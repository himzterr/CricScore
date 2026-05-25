"""Bowling card for one innings."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from cricscore.models import Innings


def _fmt(value: int | float | None, precision: int | None = None) -> str:
    if value is None:
        return "-"
    if precision is not None and isinstance(value, float):
        return f"{value:.{precision}f}"
    return str(value)


class BowlingTable(DataTable):
    """DataTable populated from one innings' bowling lineup."""

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id, show_cursor=True, zebra_stripes=True)
        self.innings = innings

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns(
            "Bowler",
            Text("O", justify="right"),
            Text("M", justify="right"),
            Text("R", justify="right"),
            Text("W", justify="right"),
            Text("Econ", justify="right"),
            Text("WD", justify="right"),
            Text("NB", justify="right"),
        )

        for bowler in self.innings.bowled_lineup:
            name = bowler.player.long_name or bowler.player.name or "?"
            wickets = bowler.wickets or 0
            name_style = "bold #f59f3a" if wickets >= 3 else ""
            self.add_row(
                Text(name, style=name_style),
                Text(_fmt(bowler.overs, 1), justify="right"),
                Text(_fmt(bowler.maidens), justify="right"),
                Text(_fmt(bowler.conceded), justify="right"),
                Text(_fmt(bowler.wickets), justify="right", style=name_style),
                Text(_fmt(bowler.economy, 2), justify="right"),
                Text(_fmt(bowler.wides), justify="right"),
                Text(_fmt(bowler.noballs), justify="right"),
            )
