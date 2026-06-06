"""CricScoreApp — top-level Textual app.

Routing rules (Phase 3):

- Construct with ``match_ref=<MatchRef>`` to jump straight into a fetch + render.
- Construct with ``match=<Match>`` to skip the fetch (used by tests).
- Construct with neither to open the URL input screen.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from cricscore.models import Match
from cricscore.models.match import Commentary, LiveState
from cricscore.tui.screens import LoadingScreen, ScorecardScreen, URLInputScreen
from cricscore.url_parser import MatchRef


class CricScoreApp(App):
    CSS_PATH = Path(__file__).parent / "styles.tcss"
    TITLE = "CricScore"
    SUB_TITLE = "ESPNCricinfo scorecards in your terminal"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        match_ref: MatchRef | None = None,
        match: Match | None = None,
        live: LiveState | None = None,
        commentary: Commentary | None = None,
    ) -> None:
        super().__init__()
        self._initial_match_ref = match_ref
        self._initial_match = match
        self._initial_live = live
        self._initial_commentary = commentary
        # Populated by LoadingScreen after a successful fetch so ScorecardScreen
        # can poll for live refreshes.
        self.match_ref: MatchRef | None = match_ref

    def on_mount(self) -> None:
        if self._initial_match is not None:
            self.push_screen(
                ScorecardScreen(
                    self._initial_match,
                    self._initial_live,
                    self._initial_commentary,
                )
            )
        elif self._initial_match_ref is not None:
            self.push_screen(LoadingScreen(self._initial_match_ref))
        else:
            self.push_screen(URLInputScreen())
