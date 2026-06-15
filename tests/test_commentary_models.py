"""Tests for the Commentary and CommentaryItem models.

All tests run against the captured fixture
``tests/fixtures/commentary_1527150.json``
(India vs Afghanistan Only Test, ball-by-ball-commentary page).
No network calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cricscore.models.match import Commentary, CommentaryItem, RecentBall

FIXTURE = Path(__file__).parent / "fixtures" / "commentary_1527150.json"


@pytest.fixture(scope="session")
def raw_payload() -> dict:
    with FIXTURE.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def commentary(raw_payload: dict) -> Commentary:
    return Commentary.from_commentary_payload(raw_payload)


# ---------- Commentary ----------

def test_commentary_has_items(commentary: Commentary) -> None:
    assert len(commentary.items) > 0


def test_commentary_current_inning(commentary: Commentary) -> None:
    assert commentary.current_inning_number == 1


def test_commentary_items_are_newest_first(commentary: Commentary) -> None:
    """Items are delivered newest-first by ESPN; we preserve that order."""
    if len(commentary.items) < 2:
        pytest.skip("need at least 2 items")
    # The first item has a higher or equal oversActual than the second.
    first = commentary.items[0].overs_actual
    second = commentary.items[1].overs_actual
    if first is not None and second is not None:
        assert first >= second, "items should be newest-first"


# ---------- CommentaryItem ----------

def test_item_comment_id(commentary: Commentary) -> None:
    """Each item should have a non-None comment_id."""
    for item in commentary.items:
        assert item.comment_id is not None


def test_item_over_label(commentary: Commentary) -> None:
    """over_label formats overs_actual as 'NN.N' without float noise."""
    first = commentary.items[0]
    label = first.over_label
    # Should match pattern: digits . digit(s)
    assert "." in label
    # Should not contain many decimal places (float noise check)
    decimal_part = label.split(".")[1]
    assert len(decimal_part) <= 2, f"label too long: {label!r}"


def test_item_title(commentary: Commentary) -> None:
    """Title is a human-readable 'Bowler to Batsman' string."""
    first = commentary.items[0]
    assert first.title is not None
    assert " to " in (first.title or "")


def test_item_text_strips_html(commentary: Commentary) -> None:
    """text property strips HTML tags from commentTextItems."""
    first = commentary.items[0]
    text = first.text
    assert "<" not in text, f"HTML leak in text: {text!r}"
    assert ">" not in text, f"HTML leak in text: {text!r}"


def test_item_text_is_non_empty(commentary: Commentary) -> None:
    """Most items have at least some commentary text."""
    non_empty = [it for it in commentary.items if it.text]
    assert len(non_empty) > 0


# ---------- CommentaryItem.outcome ----------

@pytest.mark.parametrize("overrides,expected", [
    ({"isWicket": True, "isFour": False, "isSix": False}, "W"),
    ({"isSix": True, "isWicket": False, "isFour": False, "totalRuns": 6, "batsmanRuns": 6}, "6"),
    ({"isFour": True, "isWicket": False, "isSix": False, "totalRuns": 4, "batsmanRuns": 4}, "4"),
])
def test_outcome_special_events(overrides: dict, expected: str) -> None:
    base = {
        "id": 999,
        "overNumber": 10, "ballNumber": 3, "oversActual": 9.3,
        "totalRuns": 0, "batsmanRuns": 0,
        "isFour": False, "isSix": False, "isWicket": False,
        "title": "Bowler to Batsman",
        "commentTextItems": [],
    }
    base.update(overrides)
    item = CommentaryItem.model_validate(base)
    assert item.outcome == expected


def test_outcome_dot_ball() -> None:
    item = CommentaryItem.model_validate({
        "id": 1, "oversActual": 1.1, "totalRuns": 0, "batsmanRuns": 0,
        "isFour": False, "isSix": False, "isWicket": False,
        "commentTextItems": [],
    })
    assert item.outcome == "0"


def test_outcome_wide() -> None:
    item = CommentaryItem.model_validate({
        "id": 2, "oversActual": 1.0, "totalRuns": 1, "batsmanRuns": 0,
        "isFour": False, "isSix": False, "isWicket": False,
        "wides": 1, "commentTextItems": [],
    })
    assert item.outcome == "Wd"


# ---------- RecentBall.display still works after _ball_outcome refactor ----------

def test_recent_ball_display_unchanged() -> None:
    """Ensure the _ball_outcome refactor did not break RecentBall.display."""
    ball = RecentBall.model_validate({
        "overNumber": 5, "oversActual": 4.3,
        "totalRuns": 4, "batsmanRuns": 4,
        "isFour": True, "isSix": False, "isWicket": False,
    })
    assert ball.display == "4"


def test_recent_ball_display_wicket() -> None:
    ball = RecentBall.model_validate({
        "overNumber": 5, "oversActual": 4.4, "totalRuns": 0, "batsmanRuns": 0,
        "isFour": False, "isSix": False, "isWicket": True,
    })
    assert ball.display == "W"


# ---------- dismissalText shapes ----------

def test_dismissal_text_dict_shape() -> None:
    """ESPN sends a wicket's dismissalText as a structured object, not a string.

    Regression: a single dict-shaped dismissalText used to raise a
    ValidationError and take down the entire commentary feed.
    """
    item = CommentaryItem.model_validate({
        "id": 7, "oversActual": 10.4, "totalRuns": 0, "batsmanRuns": 0,
        "isFour": False, "isSix": False, "isWicket": True,
        "dismissalText": {
            "short": "caught", "long": "c Powell b Hosein",
            "commentary": "Kamindu Mendis c Powell b Hosein 20",
            "fielderText": "c Powell", "bowlerText": "b Hosein",
        },
        "commentTextItems": [],
    })
    assert item.dismissal_text is not None
    assert item.dismissal_text.long == "c Powell b Hosein"
    assert item.dismissal_text.short == "caught"


def test_dismissal_text_string_shape() -> None:
    """A bare-string dismissalText is coerced into the structured form."""
    item = CommentaryItem.model_validate({
        "id": 8, "oversActual": 10.5, "isWicket": True,
        "dismissalText": "c Powell b Hosein", "commentTextItems": [],
    })
    assert item.dismissal_text is not None
    assert item.dismissal_text.long == "c Powell b Hosein"


def test_commentary_payload_with_wicket_parses() -> None:
    """A feed containing a wicket delivery parses without error."""
    payload = {
        "content": {
            "currentInningNumber": 1,
            "comments": [
                {
                    "id": 1, "oversActual": 10.5, "isWicket": False,
                    "commentTextItems": [],
                },
                {
                    "id": 2, "oversActual": 10.4, "isWicket": True,
                    "dismissalText": {"long": "c Powell b Hosein"},
                    "commentTextItems": [],
                },
            ],
        }
    }
    c = Commentary.from_commentary_payload(payload)
    assert len(c.items) == 2
    assert c.items[1].dismissal_text is not None
    assert c.items[1].dismissal_text.long == "c Powell b Hosein"


# ---------- from_commentary_payload error path ----------

def test_missing_content_returns_empty() -> None:
    """Payload with no content produces an empty Commentary."""
    c = Commentary.from_commentary_payload({})
    assert c.items == []
    assert c.current_inning_number is None
