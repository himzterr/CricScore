"""Live match panel — replaces MatchHeader while a match is in progress.

Left column:
  • Score line   — "IND  247/3  (66.2 ov)  CRR 4.31 · RRR -"
  • Current over — "This over:  0  4  •  •  1  W"
  • Batsmen      — striker marked with ✦, run rates
  • Bowler       — figures + economy
  • Partnership / last wicket context

Right column:
  • Ordinal over number + total runs for the over
  • Per-ball chip tiles: dot(•), W, 4, 6, Wd, Nb, … coloured by type
"""

from __future__ import annotations

import contextlib

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from cricscore.effects import TypewriterLabel, gradient_text
from cricscore.models.match import LiveBatter, LiveBowler, LiveState, RecentBall

_ACCENT = "#f59f3a"
_ACCENT_BRIGHT = "#ffd16e"
_SUCCESS = "#5dd39e"
_DANGER = "#f05a5a"
_DIM = "#5b6981"
_MUTED = "#9aa6bd"


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────


def _ordinal(n: int) -> str:
    """Return English ordinal string: 1 → '1st', 2 → '2nd', 11 → '11th', …"""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ball_chip(ball: RecentBall) -> Text:
    """Return a single Rich Text chip representing one delivery (for the text strip)."""
    label = ball.display
    if ball.is_wicket:
        style = f"bold {_DANGER}"
    elif ball.is_four or ball.is_six:
        style = f"bold {_ACCENT}"
    elif label in {"Wd", "Nb"} or label.startswith(("Wd+", "Nb+", "By", "Lb")):
        style = _MUTED
    else:
        style = _SUCCESS if label != "0" else _DIM
    return Text(f" {label} ", style=style)


def _over_strip_text(balls: list[RecentBall]) -> str:
    """Build a plain string for the typewriter label (style applied separately)."""
    if not balls:
        return "This over:  (no balls yet)"
    parts = [b.display for b in balls]
    return "This over:  " + "  ".join(parts)


def _chip_label(ball: RecentBall) -> str:
    """Short label for a chip tile — dot balls shown as '•'."""
    label = ball.display
    return "•" if label == "0" else label


def _chip_classes(ball: RecentBall) -> str:
    """CSS class string for a chip tile based on delivery type."""
    if ball.is_wicket:
        return "ball-chip chip-wicket"
    if ball.is_four or ball.is_six:
        return "ball-chip chip-boundary"
    if ball.wides or ball.noballs or ball.byes or ball.legbyes:
        return "ball-chip chip-extra"
    if (ball.batsman_runs or 0) > 0:
        return "ball-chip chip-run"
    return "ball-chip chip-dot"


def _make_chip_static(ball: RecentBall) -> Static:
    """Return a bordered chip Static widget for one delivery.

    No id= assigned — chips are identified by position, not by ID,
    to avoid Textual DuplicateIds errors on rebuild.
    """
    return Static(_chip_label(ball), classes=_chip_classes(ball))


def _chip_rows(balls: list[RecentBall]) -> list[list[RecentBall]]:
    """Split deliveries into rows of 6 to handle extended overs."""
    return [balls[i : i + 6] for i in range(0, len(balls), 6)] if balls else []


def _over_header_text(balls: list[RecentBall]) -> Text:
    """Two-line header for the over chip column: ordinal over + run count."""
    if not balls:
        return Text("  —\n  —", justify="left")
    raw_over = balls[0].over_number or 0
    over_num = raw_over - 1 if raw_over else 0
    total_runs = sum(b.total_runs or 0 for b in balls)
    t = Text(justify="center")
    t.append(_ordinal(over_num) if over_num else "—", style=f"bold {_MUTED}")
    t.append(" over\n", style=_DIM)
    t.append(str(total_runs), style=f"bold {_ACCENT_BRIGHT}")
    t.append(" run" + ("s" if total_runs != 1 else ""), style=_DIM)
    return t


def _batter_line(batter: LiveBatter) -> Text:
    name = batter.player.long_name or batter.player.name or "?"
    sr = f"{batter.strike_rate:.1f}" if batter.strike_rate is not None else "-"
    line = Text()
    if batter.on_strike:
        line.append(f"  ✦ {name}", style=f"bold {_ACCENT}")
    else:
        line.append(f"    {name}", style=_MUTED)
    line.append(f"  {batter.runs or 0} ({batter.balls or 0})", style=_MUTED)
    line.append(f"  SR {sr}", style=_DIM)
    if batter.fours:
        line.append(f"  4s: {batter.fours}", style=_DIM)
    if batter.sixes:
        line.append(f"  6s: {batter.sixes}", style=_DIM)
    return line


def _bowler_line(bowler: LiveBowler) -> Text:
    name = bowler.player.long_name or bowler.player.name or "?"
    overs = f"{bowler.overs}" if bowler.overs is not None else "-"
    m = bowler.maidens or 0
    r = bowler.conceded or 0
    w = bowler.wickets or 0
    econ = f"{bowler.economy:.2f}" if bowler.economy is not None else "-"
    wkt_style = f"bold {_ACCENT}" if w >= 3 else _MUTED
    line = Text()
    line.append(f"  ⚾ {name}", style=f"bold {_SUCCESS}")
    line.append("  ", style="")
    line.append(f"{overs}-{m}-{r}-", style=_MUTED)
    line.append(str(w), style=wkt_style)
    line.append(f"  (econ {econ})", style=_DIM)
    return line


def _score_line(live: LiveState) -> Text:
    abbr = live.batting_team_abbreviation or live.batting_team_name or ""
    score = live.current_score or "-"
    # Prefer overs_actual from the most recent ball (already cricket notation e.g. 69.5).
    # Fall back to live_overs which ESPN encodes as 69.05; convert by treating
    # the fractional part as hundredths-of-ball (0.05 → 5th ball → display ".5").
    _recent = live.recent_balls[0].overs_actual if live.recent_balls else None
    if _recent is not None:
        overs = f"{_recent:.6g}"
    elif live.live_overs is not None:
        _ov = live.live_overs
        overs = f"{int(_ov)}.{round((_ov % 1) * 100)}"
    else:
        overs = "-"
    crr = f"{live.info.current_run_rate:.2f}" if live.info and live.info.current_run_rate else "-"
    rrr = (
        f"{live.info.required_run_rate:.2f}"
        if live.info and live.info.required_run_rate and live.info.required_run_rate > 0
        else None
    )

    line = Text()
    line.append(f"  {abbr} ", style=f"bold {_MUTED}")
    line.append_text(gradient_text(score, _ACCENT, _ACCENT_BRIGHT, bold=True))
    line.append(f"  ({overs} ov)", style=_DIM)
    line.append(f"    CRR {crr}", style=_MUTED)
    if rrr:
        line.append(f"  ·  RRR {rrr}", style=_MUTED)
    return line


# ──────────────────────────────────────────────────────────────────────────────
# Widget
# ──────────────────────────────────────────────────────────────────────────────


class LivePanel(Horizontal):
    """Live match status card — shown in place of MatchHeader while LIVE.

    Uses a left/right split: existing text info on the left, ball-chip
    tiles for the current over on the right.
    """

    DEFAULT_CSS = ""

    def __init__(self, live: LiveState, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._live = live

    # ---------- compose ----------

    def compose(self) -> ComposeResult:
        live = self._live
        balls = live.current_over_balls

        # ── LEFT: status / score / over strip / batsmen / bowler / context ──
        with Vertical(id="live-left"):
            if live.status_text:
                yield Static(
                    Text(live.status_text, style=f"bold {_SUCCESS}"),
                    id="live-status",
                    classes="live-status",
                )
            yield Static(_score_line(live), id="live-score", classes="live-score")
            yield TypewriterLabel(
                _over_strip_text(balls),
                style=_MUTED,
                delay=0.025,
                id="live-over",
                classes="live-over",
            )
            yield Static(Text("  Batsmen", style=f"bold {_DIM}"), classes="live-section-label")
            for batter in live.batsmen:
                yield Static(_batter_line(batter), classes="live-batter")
            bowler = live.current_bowler
            if bowler is not None:
                yield Static(
                    Text("  Bowler", style=f"bold {_DIM}"), classes="live-section-label"
                )
                yield Static(_bowler_line(bowler), id="live-bowler", classes="live-bowler")
            context_parts: list[str] = []
            if live.partnership_text:
                context_parts.append(f"Partnership: {live.partnership_text}")
            if live.last_bat_text:
                context_parts.append(f"Last: {live.last_bat_text}")
            if live.fow_text:
                context_parts.append(f"FoW: {live.fow_text}")
            if context_parts:
                ctx = Text()
                for i, part in enumerate(context_parts):
                    if i:
                        ctx.append("  ·  ", style=_DIM)
                    ctx.append(part, style=_MUTED)
                yield Static(ctx, classes="live-context")

        # ── RIGHT: over chip tile display ──
        with Vertical(id="live-right"):
            yield Static(_over_header_text(balls), id="over-info", classes="over-info")
            with Vertical(id="over-chips-wrap"):
                for row in _chip_rows(balls):
                    with Horizontal(classes="over-chips-row"):
                        for ball in row:
                            yield _make_chip_static(ball)

    # ---------- live update ----------

    def update_state(self, live: LiveState) -> None:
        """Refresh all labels with the new live snapshot and replay animations."""
        self._live = live
        balls = live.current_over_balls

        with contextlib.suppress(Exception):
            self.query_one("#live-score", Static).update(_score_line(live))

        with contextlib.suppress(Exception):
            if live.status_text:
                self.query_one("#live-status", Static).update(
                    Text(live.status_text, style=f"bold {_SUCCESS}")
                )

        with contextlib.suppress(Exception):
            over_label = self.query_one("#live-over", TypewriterLabel)
            over_label.reset_to(_over_strip_text(balls))

        batter_widgets = list(self.query(".live-batter"))
        for widget, batter in zip(batter_widgets, live.batsmen, strict=False):
            if isinstance(widget, Static):
                widget.update(_batter_line(batter))

        bowler = live.current_bowler
        if bowler is not None:
            with contextlib.suppress(Exception):
                self.query_one("#live-bowler", Static).update(_bowler_line(bowler))

        with contextlib.suppress(Exception):
            context_parts: list[str] = []
            if live.partnership_text:
                context_parts.append(f"Partnership: {live.partnership_text}")
            if live.last_bat_text:
                context_parts.append(f"Last: {live.last_bat_text}")
            if live.fow_text:
                context_parts.append(f"FoW: {live.fow_text}")
            if context_parts:
                ctx = Text()
                for i, part in enumerate(context_parts):
                    if i:
                        ctx.append("  ·  ", style=_DIM)
                    ctx.append(part, style=_MUTED)
                for w in self.query(".live-context"):
                    if isinstance(w, Static):
                        w.update(ctx)

        # Rebuild over chip tiles
        with contextlib.suppress(Exception):
            self.query_one("#over-info", Static).update(_over_header_text(balls))

        with contextlib.suppress(Exception):
            wrap = self.query_one("#over-chips-wrap")
            for child in list(wrap.children):
                child.remove()
            for row_balls in _chip_rows(balls):
                row = Horizontal(classes="over-chips-row")
                wrap.mount(row)
                row.mount(*[_make_chip_static(b) for b in row_balls])
