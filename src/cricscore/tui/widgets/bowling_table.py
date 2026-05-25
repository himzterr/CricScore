"""Bowling card for one innings — staggered row reveal + replay on tab switch."""

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
    """DataTable populated from one innings' bowling lineup.

    Rows reveal on a stagger timer; ``replay()`` restarts the animation
    when the parent tab is re-activated.
    """

    REVEAL_INTERVAL = 0.035

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id, show_cursor=True, zebra_stripes=True)
        self.innings = innings
        self._pending: list[tuple[Text, ...]] = []
        self._reveal_timer = None

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
        self._start_reveal()

    def _build_rows(self):
        for bowler in self.innings.bowled_lineup:
            name = bowler.player.long_name or bowler.player.name or "?"
            wickets = bowler.wickets or 0
            name_style = "bold #f59f3a" if wickets >= 3 else ""
            yield (
                Text(name, style=name_style),
                Text(_fmt(bowler.overs, 1), justify="right"),
                Text(_fmt(bowler.maidens), justify="right"),
                Text(_fmt(bowler.conceded), justify="right"),
                Text(_fmt(bowler.wickets), justify="right", style=name_style),
                Text(_fmt(bowler.economy, 2), justify="right"),
                Text(_fmt(bowler.wides), justify="right"),
                Text(_fmt(bowler.noballs), justify="right"),
            )

    def _start_reveal(self) -> None:
        self._pending = list(self._build_rows())
        if not self._pending:
            return
        self.add_row(*self._pending.pop(0))
        if self._pending:
            self._reveal_timer = self.set_interval(
                self.REVEAL_INTERVAL, self._reveal_next
            )

    def _reveal_next(self) -> None:
        if not self._pending:
            if self._reveal_timer is not None:
                self._reveal_timer.stop()
                self._reveal_timer = None
            return
        self.add_row(*self._pending.pop(0))

    def replay(self) -> None:
        """Clear and re-stream the rows — invoked on tab activation."""
        if self._reveal_timer is not None:
            self._reveal_timer.stop()
            self._reveal_timer = None
        # ``clear()`` keeps columns intact; only the row data is removed.
        self.clear()
        self._start_reveal()

    def on_unmount(self) -> None:
        if self._reveal_timer is not None:
            self._reveal_timer.stop()
            self._reveal_timer = None
