"""Header card for the scorecard screen — title, status, venue, both team scores."""

from __future__ import annotations

from rich.console import Group
from rich.text import Text
from textual.widget import Widget

from cricscore.models import Match


class MatchHeader(Widget):
    """Compact summary block rendered once at the top of the scorecard screen."""

    DEFAULT_CSS = ""  # styling lives in styles.tcss

    def __init__(self, match: Match, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.match = match

    def render(self) -> Group:
        m = self.match
        title = m.title or m.short_title or f"Match {m.id}"
        format_tag = f"[{m.format}]" if m.format else ""

        venue = "venue unknown"
        if m.ground:
            town = m.ground.town_name
            base = m.ground.long_name or m.ground.name or "venue unknown"
            venue = f"{base} · {town}" if town and town not in base else base

        title_line = Text()
        title_line.append(format_tag, style="bold #5b6981")
        if format_tag:
            title_line.append("  ")
        title_line.append(title, style="bold #f59f3a")

        status_line = Text(m.status_text or "status unknown", style="bold #5dd39e")

        venue_line = Text(venue, style="#9aa6bd")

        team_lines: list[Text] = []
        for ts in m.teams:
            team_name = "?"
            if ts.team:
                team_name = ts.team.long_name or ts.team.name or "?"
            score = ts.score or "—"
            info = f"  ({ts.score_info})" if ts.score_info else ""
            line = Text()
            line.append(f"  {team_name:<28} ", style="#9aa6bd")
            line.append(score, style="bold #f59f3a")
            if info:
                line.append(info, style="#5b6981")
            team_lines.append(line)

        award_line = Text()
        if m.player_awards and m.player_awards[0].player:
            potm = m.player_awards[0].player.long_name
            if potm:
                award_line.append("  Player of the Match: ", style="#5b6981")
                award_line.append(potm, style="bold #f59f3a")

        children: list[Text] = [
            title_line,
            status_line,
            venue_line,
            Text(""),
            *team_lines,
        ]
        if str(award_line):
            children.extend([Text(""), award_line])
        return Group(*children)
