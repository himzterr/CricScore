"""Fall-of-wickets strip — types itself out under the bowling table."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from cricscore.effects import TypewriterLabel
from cricscore.models import Innings


def _format_fow_text(innings: Innings) -> str:
    entries: list[str] = []
    for fow in sorted(
        innings.fall_of_wickets, key=lambda f: f.order or f.wicket_number or 0
    ):
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
            if overs is not None:
                bits.append(f"({name}, {overs} ov)")
            else:
                bits.append(f"({name})")
        elif overs is not None:
            bits.append(f"({overs} ov)")
        entries.append(" ".join(bits))
    return ", ".join(entries)


class FowStrip(Horizontal):
    """Heading + typewriter line of fall of wickets."""

    DEFAULT_CSS = ""

    def __init__(self, innings: Innings, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.innings = innings
        if not innings.fall_of_wickets:
            self.add_class("empty")

    def compose(self) -> ComposeResult:
        yield Static(Text("Fall of wickets ", style="bold #f59f3a"), classes="fow-heading")
        yield TypewriterLabel(
            _format_fow_text(self.innings),
            style="#9aa6bd",
            delay=0.012,
            classes="fow-line",
        )

    def replay(self) -> None:
        """Restart the typewriter — used on tab activation."""
        if not self.innings.fall_of_wickets:
            return
        for label in self.query(TypewriterLabel):
            label.reset_to(_format_fow_text(self.innings))
