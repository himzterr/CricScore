"""Typed view over the ESPNCricinfo scorecard payload.

Every model uses ``extra="ignore"`` and aggressively-optional fields because
the upstream JSON includes ~hundreds of attributes per record and ESPN
occasionally renames or drops them. We only promise the slice the TUI
actually renders.
"""

from __future__ import annotations

import html as _html_lib
import re as _re_lib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ESPNModel(BaseModel):
    """Shared config for every ESPNCricinfo-derived model."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )


class TeamRef(_ESPNModel):
    id: int | None = None
    name: str | None = None
    long_name: str | None = Field(default=None, alias="longName")
    abbreviation: str | None = None
    primary_color: str | None = Field(default=None, alias="primaryColor")
    slug: str | None = None
    # Raw image dict from ESPNCricinfo (id/url/slug/etc); the CDN path is
    # surfaced via :pyattr:`image_url_path` below.
    image: dict[str, Any] | None = None

    @property
    def image_url_path(self) -> str | None:
        """The ``/lsci/...logo.png`` path of the team logo, or None."""
        if not isinstance(self.image, dict):
            return None
        url = self.image.get("url") or self.image.get("imageUrl")
        return url if isinstance(url, str) and url.startswith("/") else None


class PlayerRef(_ESPNModel):
    id: int | None = None
    name: str | None = None
    long_name: str | None = Field(default=None, alias="longName")
    mobile_name: str | None = Field(default=None, alias="mobileName")
    batting_name: str | None = Field(default=None, alias="battingName")
    fielding_name: str | None = Field(default=None, alias="fieldingName")


class DismissalText(_ESPNModel):
    short: str | None = None
    long: str | None = None
    commentary: str | None = None
    fielder_text: str | None = Field(default=None, alias="fielderText")
    bowler_text: str | None = Field(default=None, alias="bowlerText")


class Batter(_ESPNModel):
    player: PlayerRef
    batted_type: str | None = Field(default=None, alias="battedType")
    runs: int | None = None
    balls: int | None = None
    fours: int | None = None
    sixes: int | None = None
    strike_rate: float | None = Field(default=None, alias="strikerate")
    minutes: int | None = None
    is_out: bool = Field(default=False, alias="isOut")
    dismissal_text: DismissalText | None = Field(default=None, alias="dismissalText")

    @field_validator("batted_type", mode="after")
    @classmethod
    def _lower_batted_type(cls, value: str | None) -> str | None:
        return value.lower() if isinstance(value, str) else value

    @property
    def has_batted(self) -> bool:
        return self.batted_type == "yes"

    @property
    def is_substitute(self) -> bool:
        return self.batted_type == "sub"


class Bowler(_ESPNModel):
    player: PlayerRef
    overs: float | None = None
    maidens: int | None = None
    conceded: int | None = None
    wickets: int | None = None
    economy: float | None = None
    wides: int | None = None
    noballs: int | None = None
    dots: int | None = None
    balls: int | None = None


class FallOfWicket(_ESPNModel):
    wicket_number: int | None = Field(default=None, alias="fowWicketNum")
    order: int | None = Field(default=None, alias="fowOrder")
    runs: int | None = Field(default=None, alias="fowRuns")
    overs: float | None = Field(default=None, alias="fowOvers")
    balls: int | None = Field(default=None, alias="fowBalls")
    dismissed_batter: PlayerRef | None = Field(default=None, alias="dismissalBatsman")


class Innings(_ESPNModel):
    inning_number: int = Field(alias="inningNumber")
    team: TeamRef | None = None
    runs: int | None = None
    wickets: int | None = None
    overs: float | None = None
    extras: int | None = None
    byes: int | None = None
    legbyes: int | None = None
    wides: int | None = None
    noballs: int | None = None
    penalties: int | None = None
    target: int | None = None
    lead: int | None = None
    is_current: bool = Field(default=False, alias="isCurrent")

    batters: list[Batter] = Field(default_factory=list, alias="inningBatsmen")
    bowlers: list[Bowler] = Field(default_factory=list, alias="inningBowlers")
    fall_of_wickets: list[FallOfWicket] = Field(
        default_factory=list, alias="inningFallOfWickets"
    )
    # Raw per-over records. The full per-over schema is large and noisy;
    # only the fields the sparkline cares about are exposed via properties.
    over_records: list[dict[str, Any]] = Field(
        default_factory=list, alias="inningOvers"
    )

    @property
    def runs_per_over(self) -> list[int]:
        """Runs scored in each over (in order). Missing values become 0."""
        out: list[int] = []
        for over in self.over_records:
            value = over.get("overRuns")
            out.append(int(value) if isinstance(value, (int, float)) else 0)
        return out

    @property
    def wickets_per_over(self) -> list[int]:
        """Wickets that fell in each over (in order)."""
        out: list[int] = []
        for over in self.over_records:
            value = over.get("overWickets")
            out.append(int(value) if isinstance(value, (int, float)) else 0)
        return out

    @property
    def batting_lineup(self) -> list[Batter]:
        """Batters who actually came to the crease (excludes substitutes)."""
        return [b for b in self.batters if not b.is_substitute]

    @property
    def bowled_lineup(self) -> list[Bowler]:
        """Bowlers who actually bowled (non-zero overs)."""
        return [b for b in self.bowlers if (b.overs or 0) > 0 or (b.balls or 0) > 0]


class TeamScore(_ESPNModel):
    team: TeamRef | None = None
    score: str | None = None
    score_info: str | None = Field(default=None, alias="scoreInfo")
    inning_numbers: list[int] = Field(default_factory=list, alias="inningNumbers")


class Ground(_ESPNModel):
    id: int | None = None
    name: str | None = None
    long_name: str | None = Field(default=None, alias="longName")
    town: dict[str, Any] | None = None
    country: dict[str, Any] | None = None

    @property
    def town_name(self) -> str | None:
        if not isinstance(self.town, dict):
            return None
        return self.town.get("name") or self.town.get("longName")

    @property
    def country_name(self) -> str | None:
        if not isinstance(self.country, dict):
            return None
        return self.country.get("name") or self.country.get("longName")


class PlayerAward(_ESPNModel):
    award_type: str | None = Field(default=None, alias="awardType")
    name: str | None = None
    player: PlayerRef | None = None


class LiveBatter(_ESPNModel):
    """One of the two batters currently at the crease (from the live page)."""

    player: PlayerRef
    runs: int | None = None
    balls: int | None = None
    fours: int | None = None
    sixes: int | None = None
    strike_rate: float | None = Field(default=None, alias="strikerate")
    current_type: int | None = Field(default=None, alias="currentType")

    @property
    def on_strike(self) -> bool:
        """``True`` when this batter is on strike (``currentType == 1``)."""
        return self.current_type == 1


class LiveBowler(_ESPNModel):
    """The bowler currently bowling or the previous bowler (from the live page)."""

    player: PlayerRef
    overs: float | None = None
    maidens: int | None = None
    conceded: int | None = None
    wickets: int | None = None
    economy: float | None = None
    current_type: int | None = Field(default=None, alias="currentType")

    @property
    def is_current(self) -> bool:
        """``True`` when this is the bowler currently bowling (``currentType == 1``)."""
        return self.current_type == 1


def _ball_outcome(
    total_runs: int | None,
    is_four: bool,
    is_six: bool,
    is_wicket: bool,
    wides: int | None,
    noballs: int | None,
    byes: int | None,
    legbyes: int | None,
    batsman_runs: int | None,
) -> str:
    """Return a short display token for a delivery (``W``, ``4``, ``6``, ``Wd``, …).

    Shared between :attr:`RecentBall.display` and
    :attr:`CommentaryItem.outcome` so both use identical chip logic.
    """
    if is_wicket:
        return "W"
    if is_six:
        return "6"
    if is_four:
        return "4"
    if wides:
        runs = total_runs or 0
        return f"Wd+{runs - 1}" if runs > 1 else "Wd"
    if noballs:
        runs = batsman_runs or 0
        return f"Nb+{runs}" if runs else "Nb"
    if byes:
        return f"By{byes}" if byes > 1 else "By"
    if legbyes:
        return f"Lb{legbyes}" if legbyes > 1 else "Lb"
    return str(batsman_runs or 0)


class RecentBall(_ESPNModel):
    """One delivery from the recent-balls stream on the live page."""

    over_number: int | None = Field(default=None, alias="overNumber")
    overs_actual: float | None = Field(default=None, alias="oversActual")
    total_runs: int | None = Field(default=None, alias="totalRuns")
    batsman_runs: int | None = Field(default=None, alias="batsmanRuns")
    is_four: bool = Field(default=False, alias="isFour")
    is_six: bool = Field(default=False, alias="isSix")
    is_wicket: bool = Field(default=False, alias="isWicket")
    wides: int | None = None
    noballs: int | None = None
    byes: int | None = None
    legbyes: int | None = None
    batsman_player_id: int | None = Field(default=None, alias="batsmanPlayerId")
    non_striker_player_id: int | None = Field(default=None, alias="nonStrikerPlayerId")
    bowler_player_id: int | None = Field(default=None, alias="bowlerPlayerId")

    @property
    def display(self) -> str:
        """Short display token for this delivery (``W``, ``4``, ``6``, ``wd``, …)."""
        return _ball_outcome(
            self.total_runs,
            self.is_four,
            self.is_six,
            self.is_wicket,
            self.wides,
            self.noballs,
            self.byes,
            self.legbyes,
            self.batsman_runs,
        )


class LiveInfo(_ESPNModel):
    """Run-rate and last-few-overs summary from the live page."""

    current_run_rate: float | None = Field(default=None, alias="currentRunRate")
    required_run_rate: float | None = Field(default=None, alias="requiredRunrate")
    last_few_overs_runrate: float | None = Field(
        default=None, alias="lastFewOversRunrate"
    )
    last_few_overs_runs: str | None = Field(default=None, alias="lastFewOversRuns")
    last_few_overs_wickets: str | None = Field(
        default=None, alias="lastFewOversWickets"
    )


class LiveState(_ESPNModel):
    """Aggregated live match state parsed from the ``live-cricket-score`` page.

    Build via :meth:`from_live_payload` — do not instantiate directly.
    """

    # Match-level live fields
    state: str | None = None
    status_text: str | None = Field(default=None, alias="statusText")
    live_inning: int | None = Field(default=None, alias="liveInning")
    live_overs: float | None = Field(default=None, alias="liveOvers")

    # Current batting team / score (from match.teams list)
    batting_team_name: str | None = None
    batting_team_abbreviation: str | None = None
    current_score: str | None = None    # e.g. "247/3"
    current_score_info: str | None = None

    # Live performers
    batsmen: list[LiveBatter] = Field(default_factory=list)
    bowlers: list[LiveBowler] = Field(default_factory=list)

    # Recent ball stream (newest-first as delivered by ESPN)
    recent_balls: list[RecentBall] = Field(default_factory=list)

    # Rate info
    info: LiveInfo | None = None

    # Context lines
    partnership_text: str | None = None
    last_bat_text: str | None = None
    fow_text: str | None = None

    # ---------- derived ----------

    @property
    def is_live(self) -> bool:
        return self.state == "LIVE"

    @property
    def current_over_balls(self) -> list[RecentBall]:
        """Balls from the *current* over in chronological order (oldest first).

        Derived from ``recent_balls`` (ESPN delivers newest first) by taking
        all deliveries whose ``over_number`` matches that of the most-recent
        ball, then reversing.
        """
        if not self.recent_balls:
            return []
        current_over = self.recent_balls[0].over_number
        same_over = [
            b for b in self.recent_balls if b.over_number == current_over
        ]
        return list(reversed(same_over))

    @property
    def current_bowler(self) -> LiveBowler | None:
        """The bowler currently bowling, or ``None``."""
        for bw in self.bowlers:
            if bw.is_current:
                return bw
        return self.bowlers[0] if self.bowlers else None

    @property
    def striker(self) -> LiveBatter | None:
        """The batter currently on strike, or ``None``."""
        for b in self.batsmen:
            if b.on_strike:
                return b
        return self.batsmen[0] if self.batsmen else None

    @property
    def non_striker(self) -> LiveBatter | None:
        """The batter at the non-striker's end, or ``None``."""
        for b in self.batsmen:
            if not b.on_strike:
                return b
        return self.batsmen[1] if len(self.batsmen) > 1 else None

    # ---------- constructor ----------

    @classmethod
    def from_live_payload(cls, payload: dict[str, Any]) -> LiveState:
        """Build a :class:`LiveState` from the raw live fetcher payload.

        ``payload`` is the value returned by
        :meth:`cricscore.api.client.ESPNCricinfoClient.fetch_live` — the inner
        ``data`` dict containing ``match`` and ``content``.
        """
        try:
            match_block: dict[str, Any] = payload["match"]
            content_block: dict[str, Any] = payload.get("content") or {}
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "Live payload missing required 'match' key"
            ) from exc

        support = content_block.get("supportInfo") or {}
        live_summary = support.get("liveSummary") or {}
        live_info_raw = support.get("liveInfo") or {}

        # Derive the batting team name and current score from match.teams
        # (the team whose inning numbers include the live inning number).
        teams: list[dict[str, Any]] = match_block.get("teams", []) or []
        live_inning = match_block.get("liveInning")
        batting_team_name: str | None = None
        batting_team_abbr: str | None = None
        current_score: str | None = None
        current_score_info: str | None = None
        for ts in teams:
            inning_numbers = ts.get("inningNumbers", []) or []
            if live_inning is not None and live_inning in inning_numbers:
                team_ref = ts.get("team") or {}
                batting_team_name = (
                    team_ref.get("longName") or team_ref.get("name")
                )
                batting_team_abbr = team_ref.get("abbreviation")
                current_score = ts.get("score")
                current_score_info = ts.get("scoreInfo")
                break

        batsmen = [
            LiveBatter.model_validate(b)
            for b in (live_summary.get("batsmen") or [])
        ]
        bowlers = [
            LiveBowler.model_validate(bw)
            for bw in (live_summary.get("bowlers") or [])
        ]
        recent_balls = [
            RecentBall.model_validate(rb)
            for rb in (live_summary.get("recentBalls") or [])
        ]

        return cls.model_validate(
            {
                **{
                    k: match_block.get(k)
                    for k in (
                        "state", "statusText", "liveInning", "liveOvers"
                    )
                },
                "batting_team_name": batting_team_name,
                "batting_team_abbreviation": batting_team_abbr,
                "current_score": current_score,
                "current_score_info": current_score_info,
                "batsmen": [b.model_dump() for b in batsmen],
                "bowlers": [bw.model_dump() for bw in bowlers],
                "recent_balls": [rb.model_dump() for rb in recent_balls],
                "info": live_info_raw or None,
                "partnership_text": live_summary.get("partnershipText"),
                "last_bat_text": live_summary.get("lastBatText"),
                "fow_text": live_summary.get("fowText"),
            }
        )


class CommentaryItem(_ESPNModel):
    """One delivery entry from the ball-by-ball commentary feed.

    All text fields are optional because ESPN may omit them for older balls
    or between-over entries.
    """

    # ESPN sends both ``_uid`` and ``id`` with the same value; ``id`` is
    # the stable key we use for new-delivery detection.
    comment_id: int | None = Field(default=None, alias="id")
    inning_number: int | None = Field(default=None, alias="inningNumber")
    over_number: int | None = Field(default=None, alias="overNumber")
    ball_number: int | None = Field(default=None, alias="ballNumber")
    overs_actual: float | None = Field(default=None, alias="oversActual")

    # Scoring fields — same names/aliases as RecentBall
    total_runs: int | None = Field(default=None, alias="totalRuns")
    batsman_runs: int | None = Field(default=None, alias="batsmanRuns")
    is_four: bool = Field(default=False, alias="isFour")
    is_six: bool = Field(default=False, alias="isSix")
    is_wicket: bool = Field(default=False, alias="isWicket")
    wides: int | None = None
    noballs: int | None = None
    byes: int | None = None
    legbyes: int | None = None

    # Narrative fields
    title: str | None = None  # e.g. "Kharote to Gill"
    dismissal_text: str | None = Field(default=None, alias="dismissalText")
    comment_text_items: list[dict[str, Any]] = Field(
        default_factory=list, alias="commentTextItems"
    )

    @property
    def over_label(self) -> str:
        """Over label in ``"74.6"`` format (or ``"<over>.<ball>"`` fallback)."""
        if self.overs_actual is not None:
            # Use shortest-decimal repr via :.6g to avoid 74.60000000001 noise.
            return f"{self.overs_actual:.6g}"
        if self.over_number is not None and self.ball_number is not None:
            return f"{self.over_number - 1}.{self.ball_number}"
        return "?"

    @property
    def text(self) -> str:
        """Plain-text commentary (HTML tags stripped, entities unescaped)."""
        parts: list[str] = []
        for item in self.comment_text_items or []:
            if isinstance(item, dict):
                raw = item.get("html") or ""
                stripped = _re_lib.sub(r"<[^>]+>", "", raw)
                parts.append(_html_lib.unescape(stripped).strip())
        return " ".join(p for p in parts if p)

    @property
    def outcome(self) -> str:
        """Short outcome chip — same tokens as :attr:`RecentBall.display`."""
        return _ball_outcome(
            self.total_runs,
            self.is_four,
            self.is_six,
            self.is_wicket,
            self.wides,
            self.noballs,
            self.byes,
            self.legbyes,
            self.batsman_runs,
        )


class Commentary(_ESPNModel):
    """Ball-by-ball commentary feed from the ``ball-by-ball-commentary`` page.

    Build via :meth:`from_commentary_payload` — do not instantiate directly.
    ``items`` is kept newest-first, exactly as ESPN delivers it.
    """

    items: list[CommentaryItem] = Field(default_factory=list)
    current_inning_number: int | None = Field(
        default=None, alias="currentInningNumber"
    )

    @classmethod
    def from_commentary_payload(cls, payload: dict[str, Any]) -> Commentary:
        """Build a :class:`Commentary` from the raw commentary fetcher payload.

        ``payload`` is the value returned by
        :meth:`cricscore.api.client.ESPNCricinfoClient.fetch_commentary` — the
        inner ``data`` dict containing ``match`` and ``content``.
        """
        try:
            content_block: dict[str, Any] = payload.get("content") or {}
        except (AttributeError, TypeError) as exc:
            raise ValueError(
                "Commentary payload missing 'content' key"
            ) from exc

        raw_comments: list[dict[str, Any]] = content_block.get("comments") or []
        items = [CommentaryItem.model_validate(c) for c in raw_comments]
        return cls.model_validate(
            {
                "items": [it.model_dump() for it in items],
                "currentInningNumber": content_block.get("currentInningNumber"),
            }
        )


class Match(_ESPNModel):
    id: int
    format: str | None = None
    title: str | None = None
    short_title: str | None = Field(default=None, alias="shortTitle")
    description: str | None = None
    status_text: str | None = Field(default=None, alias="statusText")
    stage: str | None = None
    state: str | None = None
    teams: list[TeamScore] = Field(default_factory=list)
    ground: Ground | None = None
    innings: list[Innings] = Field(default_factory=list)
    player_awards: list[PlayerAward] = Field(default_factory=list)

    @property
    def is_live(self) -> bool:
        """``True`` when this match is currently in progress."""
        return self.state == "LIVE"

    @classmethod
    def from_scorecard_payload(cls, payload: dict[str, Any]) -> Match:
        """Build a :class:`Match` from the raw fetcher payload.

        ``payload`` is the value returned by
        :meth:`cricscore.api.client.ESPNCricinfoClient.fetch_scorecard` — i.e.
        the ``props.appPageProps.data`` slice of ``__NEXT_DATA__``.
        """
        try:
            match_block = payload["match"]
            content_block = payload.get("content") or {}
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "Scorecard payload missing required 'match' key"
            ) from exc

        return cls.model_validate(
            {
                **match_block,
                "innings": content_block.get("innings", []),
                "player_awards": content_block.get("matchPlayerAwards") or [],
            }
        )
