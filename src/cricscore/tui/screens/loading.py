"""Loading screen — fetches the scorecard in a worker thread.

Phase 4: status line uses a typewriter effect and cycles through phases
("Warming up Akamai...", "Fetching scorecard...", "Parsing...") to give a
better sense of progress than a static label.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, LoadingIndicator
from textual.worker import Worker, WorkerState

from cricscore.api.client import ESPNCricinfoClient
from cricscore.api.live_feed import fetch_match_state
from cricscore.effects import TypewriterLabel
from cricscore.models import Match
from cricscore.models.match import Commentary, LiveState
from cricscore.url_parser import MatchRef

_PHASES: tuple[str, ...] = (
    "Warming up the Akamai handshake...",
    "Fetching scorecard...",
    "Parsing innings...",
    "Rendering...",
)
_PHASE_INTERVAL = 0.9


class LoadingScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("r", "retry", "Retry", show=False),
    ]

    def __init__(self, match_ref: MatchRef) -> None:
        super().__init__()
        self.match_ref = match_ref
        self._phase_index = 0
        self._phase_timer = None  # type: ignore[var-annotated]

    def compose(self) -> ComposeResult:
        with Container(id="loading-card"):
            yield TypewriterLabel(
                f"Loading match {self.match_ref.match_id}...",
                style="#9aa6bd",
                delay=0.022,
                id="loading-status",
            )
            yield LoadingIndicator()
            yield Label("", id="loading-error")
        yield Footer()

    def on_mount(self) -> None:
        self._fetch()
        # Rotate the status line through the phases until the worker finishes.
        self._phase_timer = self.set_interval(_PHASE_INTERVAL, self._advance_phase)  # type: ignore[assignment]

    def action_retry(self) -> None:
        """Re-run the fetch (shown in footer only when errored)."""
        if not self.has_class("errored"):
            return
        self.remove_class("errored")
        self.query_one("#loading-error", Label).update("")
        self._phase_index = 0
        self._fetch()
        self._phase_timer = self.set_interval(_PHASE_INTERVAL, self._advance_phase)  # type: ignore[assignment]

    def _advance_phase(self) -> None:
        if self._phase_index >= len(_PHASES):
            return
        phrase = _PHASES[self._phase_index]
        self._phase_index += 1
        try:
            label = self.query_one("#loading-status", TypewriterLabel)
        except Exception:
            return
        label.reset_to(phrase)

    def _fetch(self) -> None:
        ref = self.match_ref

        def work() -> tuple[Match, LiveState | None, Commentary | None]:
            # Live state and commentary are derived from a single shared fetch
            # so the live panel and commentary feed never drift apart.
            return fetch_match_state(ESPNCricinfoClient(), ref)

        self.run_worker(work, name="fetch-scorecard", thread=True, exclusive=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "fetch-scorecard":
            return
        if event.state == WorkerState.SUCCESS:
            self._stop_phase_timer()
            from cricscore.tui.screens.scorecard import ScorecardScreen

            result: tuple[Match, LiveState | None, Commentary | None] = event.worker.result  # type: ignore[assignment]
            match, live, commentary = result
            assert isinstance(match, Match)
            # Store the match_ref on the app so ScorecardScreen can poll.
            self.app.match_ref = self.match_ref  # type: ignore[attr-defined]
            self.app.switch_screen(ScorecardScreen(match, live, commentary))
        elif event.state == WorkerState.ERROR:
            self._stop_phase_timer()
            self._show_error(event.worker.error)

    def _stop_phase_timer(self) -> None:
        if self._phase_timer is not None:
            self._phase_timer.stop()
            self._phase_timer = None

    def _show_error(self, error: BaseException | None) -> None:
        raw = str(error or "unknown error")
        # Truncate verbose curl messages to just the first sentence.
        short = raw.split("\n")[0].split(". See ")[0]
        if len(short) > 120:
            short = short[:117] + "…"
        label = self.query_one("#loading-error", Label)
        label.update(f"{short}  •  press r to retry")
        self.add_class("errored")
