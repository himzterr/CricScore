"""Per-innings container: section labels + batting + bowling + FoW."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label

from cricscore.models import Innings
from cricscore.tui.widgets.batting_table import BattingTable
from cricscore.tui.widgets.bowling_table import BowlingTable
from cricscore.tui.widgets.fow_strip import FowStrip


class InningsPanel(VerticalScroll):
    """Scrollable column with batting, bowling, and FoW for one innings."""

    DEFAULT_CSS = ""

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.innings = innings

    def compose(self) -> ComposeResult:
        yield Label("Batting", classes="section-heading")
        yield BattingTable(self.innings)
        yield Label("Bowling", classes="section-heading")
        yield BowlingTable(self.innings)
        yield FowStrip(self.innings)

    def replay(self) -> None:
        """Re-trigger the reveal animations — used on tab activation."""
        for table in self.query(BattingTable):
            table.replay()
        for table in self.query(BowlingTable):
            table.replay()
        for strip in self.query(FowStrip):
            strip.replay()
