"""Batting card for one innings."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

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
    if batter.batted_type == "DNB" or batter.batted_type == "dnb":
        return Text("did not bat", style="#5b6981 italic")
    return Text("", style="#5b6981")


class BattingTable(DataTable):
    """DataTable populated from one innings' batting lineup."""

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id, show_cursor=True, zebra_stripes=True)
        self.innings = innings

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

        for batter in self.innings.batting_lineup:
            if batter.batted_type != "yes":
                continue
            name = batter.player.long_name or batter.player.name or "?"
            name_text = Text(name, style="bold #f59f3a" if batter.runs and batter.runs >= 50 else "")
            self.add_row(
                name_text,
                _dismissal_short(batter),
                Text(_fmt_int(batter.runs), justify="right"),
                Text(_fmt_int(batter.balls), justify="right"),
                Text(_fmt_int(batter.fours), justify="right"),
                Text(_fmt_int(batter.sixes), justify="right"),
                Text(_fmt_sr(batter.strike_rate), justify="right"),
            )

        extras_total = self.innings.extras
        if extras_total is not None:
            parts = []
            for label, value in [
                ("b", self.innings.byes),
                ("lb", self.innings.legbyes),
                ("w", self.innings.wides),
                ("nb", self.innings.noballs),
                ("p", self.innings.penalties),
            ]:
                if value:
                    parts.append(f"{value}{label}")
            breakdown = f"  ({', '.join(parts)})" if parts else ""
            self.add_row(
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
            self.add_row(
                Text("Total", style="bold #f59f3a"),
                Text(f"({wkts} wkts, {overs} overs)", style="#5b6981"),
                Text(str(self.innings.runs), justify="right", style="bold #f59f3a"),
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
                Text("", justify="right"),
            )

        # Did-not-bat as a final compact line so the order stays readable
        dnb = [
            b.player.long_name or b.player.name or "?"
            for b in self.innings.batting_lineup
            if (b.batted_type or "").lower() == "dnb"
        ]
        if dnb:
            self.add_row(
                Text("DNB", style="italic #5b6981"),
                Text(", ".join(dnb), style="italic #5b6981"),
                Text(""),
                Text(""),
                Text(""),
                Text(""),
                Text(""),
            )
