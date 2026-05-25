"""Paste-a-URL screen. Used when the app is launched without a URL argument."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Input, Label

from cricscore.url_parser import InvalidUrlError, parse_match_url


class URLInputScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Container(id="url-card"):
            yield Label("CricScore", id="url-title")
            yield Input(
                placeholder="Paste an espncricinfo full-scorecard URL...",
                id="url-input",
            )
            yield Label("Invalid URL", id="url-error")
            yield Label("press [enter] to load, [q] to quit", id="url-hint")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            match_ref = parse_match_url(event.value)
        except InvalidUrlError as exc:
            error_label = self.query_one("#url-error", Label)
            error_label.update(f"{exc}")
            self.add_class("errored")
            return
        # Imported here to avoid a circular import with CricScoreApp.
        from cricscore.tui.screens.loading import LoadingScreen

        self.remove_class("errored")
        self.app.switch_screen(LoadingScreen(match_ref))
