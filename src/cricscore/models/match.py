"""Typed view over the ESPNCricinfo scorecard payload.

Every model uses ``extra="ignore"`` and aggressively-optional fields because
the upstream JSON includes ~hundreds of attributes per record and ESPN
occasionally renames or drops them. We only promise the slice the TUI
actually renders.
"""

from __future__ import annotations

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

    @classmethod
    def from_scorecard_payload(cls, payload: dict[str, Any]) -> "Match":
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
