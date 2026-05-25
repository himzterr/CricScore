"""One-line fall-of-wickets summary."""

from __future__ import annotations

from rich.console import Group
from rich.text import Text
from textual.widget import Widget

from cricscore.models import Innings


def _format_fow_line(innings: Innings) -> Text:
    entries: list[str] = []
    for fow in sorted(innings.fall_of_wickets, key=lambda f: f.order or f.wicket_number or 0):
        runs = fow.runs if fow.runs is not None else "?"
        wkt = fow.wicket_number if fow.wicket_number is not None else "?"
        overs = fow.overs if fow.overs is not None else None
        name = None
        if fow.dismissed_batter:
            name = (
                fow.dismissed_batter.long_name
                or fow.dismissed_batter.name
                or fow.dismissed_batter.batting_name
            )
        bits = [f"{wkt}-{runs}"]
        if name:
            bits.append(f"({name}")
            if overs is not None:
                bits[-1] += f", {overs} ov"
            bits[-1] += ")"
        elif overs is not None:
            bits.append(f"({overs} ov)")
        entries.append(" ".join(bits))
    return Text(", ".join(entries), style="#9aa6bd")


class FowStrip(Widget):
    """Single-paragraph render of the innings' fall of wickets."""

    DEFAULT_CSS = ""

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.innings = innings
        if not innings.fall_of_wickets:
            self.add_class("empty")

    def render(self) -> Group:
        if not self.innings.fall_of_wickets:
            return Group(Text(""))
        heading = Text("Fall of wickets ", style="bold #f59f3a")
        heading.append(_format_fow_line(self.innings))
        return Group(heading)
