"""Loading screen — fetches the scorecard in a worker thread.

Phase 4: status line uses a typewriter effect and cycles through phases
("Warming up Akamai...", "Fetching scorecard...", "Parsing...") to give a
better sense of progress than a static label.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, LoadingIndicator
from textual.worker import Worker, WorkerState

from cricscore.api.client import ESPNCricinfoClient, ScorecardFetchError
from cricscore.effects import TypewriterLabel
from cricscore.models import Match
from cricscore.url_parser import MatchRef

_PHASES: tuple[str, ...] = (
    "Warming up the Akamai handshake...",
    "Fetching scorecard...",
    "Parsing innings...",
    "Rendering...",
)
_PHASE_INTERVAL = 0.9


class LoadingScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, match_ref: MatchRef) -> None:
        super().__init__()
        self.match_ref = match_ref
        self._phase_index = 0
        self._phase_timer = None

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
        self._phase_timer = self.set_interval(_PHASE_INTERVAL, self._advance_phase)

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

        def work() -> Match:
            client = ESPNCricinfoClient()
            raw = client.fetch_scorecard(ref)
            return Match.from_scorecard_payload(raw)

        self.run_worker(work, name="fetch-scorecard", thread=True, exclusive=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "fetch-scorecard":
            return
        if event.state == WorkerState.SUCCESS:
            self._stop_phase_timer()
            from cricscore.tui.screens.scorecard import ScorecardScreen

            match = event.worker.result
            assert isinstance(match, Match)
            self.app.switch_screen(ScorecardScreen(match))
        elif event.state == WorkerState.ERROR:
            self._stop_phase_timer()
            self._show_error(event.worker.error)

    def _stop_phase_timer(self) -> None:
        if self._phase_timer is not None:
            self._phase_timer.stop()
            self._phase_timer = None

    def _show_error(self, error: BaseException | None) -> None:
        if isinstance(error, ScorecardFetchError):
            message = f"Fetch failed: {error}"
        else:
            message = f"Unexpected error: {error}"
        label = self.query_one("#loading-error", Label)
        label.update(message)
        self.add_class("errored")
