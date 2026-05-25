"""Scorecard screen — header + per-innings tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, TabbedContent, TabPane

from cricscore.models import Match
from cricscore.tui.widgets import InningsPanel, MatchHeader


class ScorecardScreen(Screen):
    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("n", "next_tab", "Next innings"),
        ("p", "prev_tab", "Prev innings"),
    ]

    def __init__(self, match: Match) -> None:
        super().__init__()
        self.match = match

    def compose(self) -> ComposeResult:
        yield MatchHeader(self.match)
        with TabbedContent(id="innings-tabs"):
            for innings in self.match.innings:
                team = innings.team
                team_label = (team.name if team else None) or f"Inn {innings.inning_number}"
                runs = innings.runs if innings.runs is not None else "-"
                wkts = innings.wickets if innings.wickets is not None else "-"
                tab_label = f"{team_label} {runs}/{wkts}"
                with TabPane(tab_label, id=f"innings-{innings.inning_number}"):
                    yield InningsPanel(innings)
        yield Footer()

    def action_next_tab(self) -> None:
        tabs = self.query_one(TabbedContent)
        ids = [tab.id for tab in tabs.query("TabPane") if tab.id]
        if not ids:
            return
        try:
            i = ids.index(tabs.active)
        except ValueError:
            i = -1
        tabs.active = ids[(i + 1) % len(ids)]

    def action_prev_tab(self) -> None:
        tabs = self.query_one(TabbedContent)
        ids = [tab.id for tab in tabs.query("TabPane") if tab.id]
        if not ids:
            return
        try:
            i = ids.index(tabs.active)
        except ValueError:
            i = 0
        tabs.active = ids[(i - 1) % len(ids)]
