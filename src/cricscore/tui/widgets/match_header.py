"""Header card for the scorecard screen.

Phase 4: the title reveals itself with a typewriter effect, the team
scores render with a warm-to-bright gradient, and a per-over runs
sparkline is appended underneath each innings.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from cricscore.effects import TypewriterLabel, gradient_text, sparkline
from cricscore.models import Match
from cricscore.tui.widgets.team_logo import TeamLogo

_ACCENT = "#f59f3a"
_ACCENT_BRIGHT = "#ffd16e"
_SUCCESS = "#5dd39e"
_DIM = "#5b6981"
_MUTED = "#9aa6bd"


class MatchHeader(Vertical):
    DEFAULT_CSS = ""

    def __init__(self, match: Match, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.match = match

    # ---------- helpers ----------

    def _title_text(self) -> str:
        m = self.match
        title = m.title or m.short_title or f"Match {m.id}"
        if m.format:
            return f"[{m.format}]  {title}"
        return title

    def _venue_line(self) -> Text:
        m = self.match
        venue = "venue unknown"
        if m.ground:
            town = m.ground.town_name
            base = m.ground.long_name or m.ground.name or "venue unknown"
            venue = f"{base} · {town}" if town and town not in base else base
        return Text(venue, style=_MUTED)

    def _award_line(self) -> Text | None:
        if not self.match.player_awards:
            return None
        award = self.match.player_awards[0]
        if not award.player or not award.player.long_name:
            return None
        line = Text()
        line.append("Player of the Match: ", style=_DIM)
        line.append(award.player.long_name, style=f"bold {_ACCENT}")
        return line

    def _team_line(self, *, name: str, score: str, info: str | None) -> Text:
        line = Text()
        line.append(f"{name:<28} ", style=_MUTED)
        if score and score != "—":
            line.append_text(gradient_text(score, _ACCENT, _ACCENT_BRIGHT, bold=True))
        else:
            line.append("—", style=_DIM)
        if info:
            line.append(f"  ({info})", style=_DIM)
        return line

    def _sparkline_line(self, innings_label: str, runs_per_over: list[int]) -> Text | None:
        if not runs_per_over:
            return None
        spark = sparkline(runs_per_over)
        if not spark:
            return None
        line = Text()
        line.append(f"{innings_label:<8}", style=_DIM)
        line.append_text(gradient_text(spark, _ACCENT, _SUCCESS))
        peak = max(runs_per_over)
        line.append(f"  peak {peak}/over", style=_DIM)
        return line

    # ---------- compose ----------

    def compose(self) -> ComposeResult:
        m = self.match

        # Logos row — only renders when we have two teams with abbreviations.
        teams = [ts for ts in m.teams if ts.team and ts.team.abbreviation]
        if len(teams) >= 2:
            left, right = teams[0], teams[1]
            with Horizontal(classes="logos-row"):
                yield TeamLogo(
                    left.team.abbreviation if left.team else None,
                    left.team.primary_color if left.team else None,
                    classes="team-logo",
                )
                yield Static(
                    Text("vs", style=f"bold {_DIM}"),
                    classes="logos-vs",
                )
                yield TeamLogo(
                    right.team.abbreviation if right.team else None,
                    right.team.primary_color if right.team else None,
                    classes="team-logo",
                )

        yield TypewriterLabel(
            self._title_text(),
            style=f"bold {_ACCENT}",
            delay=0.022,
            classes="match-title",
        )

        if m.status_text:
            yield Static(Text(m.status_text, style=f"bold {_SUCCESS}"), classes="match-status")

        yield Static(self._venue_line(), classes="match-venue")
        yield Static("", classes="match-spacer")

        for ts in m.teams:
            team_name = "?"
            if ts.team:
                team_name = ts.team.long_name or ts.team.name or "?"
            yield Static(
                self._team_line(name=team_name, score=ts.score or "—", info=ts.score_info),
                classes="match-team",
            )

        sparkline_lines: list[Text] = []
        for inn in m.innings:
            label = inn.team.abbreviation if inn.team and inn.team.abbreviation else f"Inn{inn.inning_number}"
            line = self._sparkline_line(label, inn.runs_per_over)
            if line is not None:
                sparkline_lines.append(line)
        if sparkline_lines:
            yield Static("", classes="match-spacer")
            for line in sparkline_lines:
                yield Static(line, classes="match-sparkline")

        award = self._award_line()
        if award is not None:
            yield Static("", classes="match-spacer")
            yield Static(award, classes="match-award")
