"""Scorecard screen — header + per-innings tabs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, TabbedContent, TabPane

from cricscore.models import Match
from cricscore.tui.widgets import InningsPanel, MatchHeader


class ScorecardScreen(Screen):
    # `n`/`p` are priority bindings so they fire even when the focused
    # DataTable would otherwise consume the key. Arrow keys stay free for
    # the DataTable's own cursor navigation.
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("n", "next_tab", "Next innings", priority=True),
        Binding("p", "prev_tab", "Prev innings", priority=True),
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
        self._cycle_tab(step=1)

    def action_prev_tab(self) -> None:
        self._cycle_tab(step=-1)

    def _cycle_tab(self, *, step: int) -> None:
        """Switch innings by ``step``. Also moves focus into the new tab so
        Textual doesn't snap back to the original tab to keep a focused
        descendant visible — that was the source of the navigation glitch.
        """
        tabs = self.query_one(TabbedContent)
        pane_ids = [pane.id for pane in tabs.query(TabPane) if pane.id]
        if not pane_ids:
            return
        try:
            current = pane_ids.index(tabs.active)
        except ValueError:
            current = 0
        new_id = pane_ids[(current + step) % len(pane_ids)]
        tabs.active = new_id

        # Move focus into the new pane so the active-tab assignment sticks
        # — Textual brings the parent tab of the focused descendant back to
        # the front, so leaving focus in the old pane reverts the switch.
        new_pane = tabs.query_one(f"#{new_id}", TabPane)
        focusables = [w for w in new_pane.query("DataTable") if w.can_focus]
        if focusables:
            focusables[0].focus()
        else:
            self.set_focus(None)
