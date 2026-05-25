"""Loading screen that fetches the scorecard in a worker thread."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, LoadingIndicator
from textual.worker import Worker, WorkerState

from cricscore.api.client import ESPNCricinfoClient, ScorecardFetchError
from cricscore.models import Match
from cricscore.url_parser import MatchRef


class LoadingScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, match_ref: MatchRef) -> None:
        super().__init__()
        self.match_ref = match_ref

    def compose(self) -> ComposeResult:
        with Container(id="loading-card"):
            yield Label(
                f"Fetching match {self.match_ref.match_id}...",
                id="loading-status",
            )
            yield LoadingIndicator()
            yield Label("", id="loading-error")
        yield Footer()

    def on_mount(self) -> None:
        self._fetch()

    def _fetch(self) -> None:
        ref = self.match_ref

        def work() -> Match:
            client = ESPNCricinfoClient()
            raw = client.fetch_scorecard(ref)
            return Match.from_scorecard_payload(raw)

        # Threaded worker — curl_cffi is sync and pydantic is fast enough.
        self.run_worker(work, name="fetch-scorecard", thread=True, exclusive=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "fetch-scorecard":
            return
        if event.state == WorkerState.SUCCESS:
            from cricscore.tui.screens.scorecard import ScorecardScreen

            match = event.worker.result
            assert isinstance(match, Match)
            self.app.switch_screen(ScorecardScreen(match))
        elif event.state == WorkerState.ERROR:
            self._show_error(event.worker.error)

    def _show_error(self, error: BaseException | None) -> None:
        if isinstance(error, ScorecardFetchError):
            message = f"Fetch failed: {error}"
        else:
            message = f"Unexpected error: {error}"
        label = self.query_one("#loading-error", Label)
        label.update(message)
        self.add_class("errored")
