from __future__ import annotations

import json
from pathlib import Path

import pytest

from cricscore.models import Match

FIXTURE = Path(__file__).parent / "fixtures" / "scorecard_1529313.json"


@pytest.fixture(scope="session")
def raw_payload() -> dict:
    with FIXTURE.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def match(raw_payload: dict) -> Match:
    return Match.from_scorecard_payload(raw_payload)


def test_match_metadata(match: Match) -> None:
    assert match.id > 0
    assert match.format == "T20"
    assert match.status_text == "DC won by 40 runs"
    assert match.ground is not None
    assert match.ground.long_name == "Eden Gardens, Kolkata"
    assert match.ground.town_name == "Kolkata"


def test_teams(match: Match) -> None:
    assert len(match.teams) == 2
    by_abbr = {ts.team.abbreviation: ts for ts in match.teams if ts.team}
    assert set(by_abbr) == {"DC", "KKR"}
    assert by_abbr["DC"].score == "203/5"
    assert by_abbr["KKR"].score == "163"
    assert by_abbr["KKR"].score_info is not None
    assert "T:204" in by_abbr["KKR"].score_info


def test_innings_counts(match: Match) -> None:
    assert [inn.inning_number for inn in match.innings] == [1, 2]
    inn1, inn2 = match.innings
    assert inn1.team and inn1.team.abbreviation == "DC"
    assert inn1.runs == 203 and inn1.wickets == 5
    assert inn2.team and inn2.team.abbreviation == "KKR"
    assert inn2.runs == 163 and inn2.wickets == 10


def test_batting_lineup_filters_substitutes(match: Match) -> None:
    inn1 = match.innings[0]
    assert len(inn1.batters) > len(inn1.batting_lineup), "fixture should include a sub"
    assert all(b.batted_type != "sub" for b in inn1.batting_lineup)
    # Every batter who batted should have a player and a runs value
    for b in inn1.batting_lineup:
        if b.batted_type == "yes":
            assert b.player.long_name is not None
            assert b.runs is not None
            assert b.balls is not None


def test_top_scorer_kl_rahul(match: Match) -> None:
    inn1 = match.innings[0]
    top = max(
        (b for b in inn1.batting_lineup if b.batted_type == "yes"),
        key=lambda b: b.runs or 0,
    )
    assert top.player.long_name == "KL Rahul"
    assert top.runs == 60
    assert top.balls == 30


def test_best_bowler_lungi_ngidi(match: Match) -> None:
    inn2 = match.innings[1]
    best = max(
        inn2.bowled_lineup,
        key=lambda b: (b.wickets or 0, -(b.conceded or 0)),
    )
    assert best.player.long_name == "Lungi Ngidi"
    assert best.wickets == 3
    assert best.conceded == 27


def test_player_of_the_match(match: Match) -> None:
    assert len(match.player_awards) == 1
    award = match.player_awards[0]
    assert award.player is not None
    assert award.player.long_name == "Kuldeep Yadav"


def test_dismissal_text_structured(match: Match) -> None:
    inn1 = match.innings[0]
    dismissed = [b for b in inn1.batting_lineup if b.is_out and b.dismissal_text]
    assert dismissed, "innings should have at least one dismissed batter with text"
    sample = dismissed[0].dismissal_text
    assert sample is not None
    assert sample.short
    assert sample.long


def test_round_trip_through_json(match: Match) -> None:
    """A dumped Match should re-validate cleanly (used by --json mode)."""
    dumped = match.model_dump(mode="json")
    rebuilt = Match.model_validate(dumped)
    assert rebuilt.id == match.id
    assert rebuilt.status_text == match.status_text
    assert len(rebuilt.innings) == len(match.innings)


def test_payload_missing_match_key_raises() -> None:
    with pytest.raises(ValueError, match="missing required 'match'"):
        Match.from_scorecard_payload({"content": {}})


def test_team_image_url_path_extracted(match: Match) -> None:
    by_abbr = {ts.team.abbreviation: ts for ts in match.teams if ts.team}
    dc_path = by_abbr["DC"].team.image_url_path
    kkr_path = by_abbr["KKR"].team.image_url_path
    assert dc_path is not None and dc_path.endswith(".logo.png")
    assert kkr_path is not None and kkr_path.endswith(".logo.png")
