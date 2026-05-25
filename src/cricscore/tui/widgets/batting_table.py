"""Batting card for one innings.

Phase 4: rows are revealed on a stagger timer instead of all at once, and
the total row gets a gradient finish.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from cricscore.effects import gradient_text
from cricscore.models import Batter, Innings


def _fmt_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _fmt_sr(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _dismissal_short(batter: Batter) -> Text:
    if not batter.is_out and batter.batted_type == "yes":
        return Text("not out", style="#5dd39e")
    if batter.dismissal_text and batter.dismissal_text.long:
        return Text(batter.dismissal_text.long, style="#9aa6bd")
    if batter.dismissal_text and batter.dismissal_text.short:
        return Text(batter.dismissal_text.short, style="#9aa6bd")
    if (batter.batted_type or "").lower() == "dnb":
        return Text("did not bat", style="#5b6981 italic")
    return Text("", style="#5b6981")


def _batter_row(batter: Batter) -> tuple[Text, ...]:
    name = batter.player.long_name or batter.player.name or "?"
    name_style = "bold #f59f3a" if (batter.runs or 0) >= 50 else ""
    return (
        Text(name, style=name_style),
        _dismissal_short(batter),
        Text(_fmt_int(batter.runs), justify="right"),
        Text(_fmt_int(batter.balls), justify="right"),
        Text(_fmt_int(batter.fours), justify="right"),
        Text(_fmt_int(batter.sixes), justify="right"),
        Text(_fmt_sr(batter.strike_rate), justify="right"),
    )


class BattingTable(DataTable):
    """DataTable populated from one innings' batting lineup.

    Rows fade in on a short interval so the table feels alive when the
    scorecard mounts. Tests that need the complete table should wait one
    or two display frames after mount.
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
            "Batter",
            "How out",
            Text("R", justify="right"),
            Text("B", justify="right"),
            Text("4s", justify="right"),
            Text("6s", justify="right"),
            Text("SR", justify="right"),
        )
        self._start_reveal()

    def _start_reveal(self) -> None:
        self._pending = list(self._build_rows())
        if not self._pending:
            return
        # Pop the first row synchronously so the table never appears empty.
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
        self.clear()
        self._start_reveal()

    def _build_rows(self):
        for batter in self.innings.batting_lineup:
            if batter.batted_type != "yes":
                continue
            yield _batter_row(batter)

        extras_total = self.innings.extras
        if extras_total is not None:
            parts: list[str] = []
            for label, value in [
                ("b", self.innings.byes),
                ("lb", self.innings.legbyes),
                ("w", self.innings.wides),
                ("nb", self.innings.noballs),
                ("p", self.innings.penalties),
            ]:
                if value:
                    parts.append(f"{value}{label}")
            breakdown = f"({', '.join(parts)})" if parts else ""
            yield (
                Text("Extras", style="italic #9aa6bd"),
                Text(breakdown, style="#5b6981"),
                Text(_fmt_int(extras_total), justify="right", style="italic"),
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
            )

        if self.innings.runs is not None:
            wkts = self.innings.wickets if self.innings.wickets is not None else "-"
            overs = self.innings.overs if self.innings.overs is not None else "-"
            total_text = gradient_text(
                str(self.innings.runs), "#f59f3a", "#ffd16e", bold=True
            )
            total_text.justify = "right"
            yield (
                gradient_text("Total", "#f59f3a", "#ffd16e", bold=True),
                Text(f"({wkts} wkts, {overs} overs)", style="#5b6981"),
                total_text,
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
            )

        dnb = [
            b.player.long_name or b.player.name or "?"
            for b in self.innings.batting_lineup
            if (b.batted_type or "").lower() == "dnb"
        ]
        if dnb:
            yield (
                Text("DNB", style="italic #5b6981"),
                Text(", ".join(dnb), style="italic #5b6981"),
                Text(""),
                Text(""),
                Text(""),
                Text(""),
                Text(""),
            )

    def on_unmount(self) -> None:
        if self._reveal_timer is not None:
            self._reveal_timer.stop()
            self._reveal_timer = None
