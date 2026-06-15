"""Tests for :func:`cricscore.api.live_feed.fetch_match_state`.

The key guarantee under test: for a live match the live panel's current-over
data and the commentary feed are derived from a *single* commentary-page
fetch, so they always describe the same most-recent delivery.  No network
calls are made — a fake client serves captured fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cricscore.api.live_feed import fetch_match_state
from cricscore.url_parser import MatchRef

FIXTURES = Path(__file__).parent / "fixtures"
COMMENTARY_FIXTURE = FIXTURES / "commentary_1527150.json"

REF = MatchRef(series_id=1, match_id=1527150)


@pytest.fixture(scope="session")
def commentary_payload() -> dict:
    with COMMENTARY_FIXTURE.open() as f:
        return json.load(f)


class FakeClient:
    """Records which endpoints were hit and serves canned payloads."""

    def __init__(
        self,
        *,
        scorecard: dict,
        commentary: dict | None = None,
        commentary_error: Exception | None = None,
        live: dict | None = None,
    ) -> None:
        self._scorecard = scorecard
        self._commentary = commentary
        self._commentary_error = commentary_error
        self._live = live
        self.calls: list[str] = []

    def fetch_scorecard(self, match_ref: MatchRef) -> dict:
        self.calls.append("scorecard")
        return self._scorecard

    def fetch_commentary(self, match_ref: MatchRef) -> dict:
        self.calls.append("commentary")
        if self._commentary_error is not None:
            raise self._commentary_error
        assert self._commentary is not None
        return self._commentary

    def fetch_live(self, match_ref: MatchRef) -> dict:
        self.calls.append("live")
        assert self._live is not None
        return self._live


def _live_scorecard() -> dict:
    return {"match": {"id": 1527150, "state": "LIVE"}, "content": {"innings": []}}


def _finished_scorecard() -> dict:
    return {"match": {"id": 1527150, "state": "POST"}, "content": {"innings": []}}


# ---------- happy path: single fetch, in sync ----------

def test_live_and_commentary_from_single_fetch(commentary_payload: dict) -> None:
    client = FakeClient(scorecard=_live_scorecard(), commentary=commentary_payload)
    match, live, commentary = fetch_match_state(client, REF)  # type: ignore[arg-type]

    assert match.is_live
    assert live is not None and commentary is not None
    # The dedicated live page must NOT be hit — that's the whole point.
    assert client.calls == ["scorecard", "commentary"]


def test_live_and_commentary_are_in_sync(commentary_payload: dict) -> None:
    """Current-over chips and the feed describe the same most-recent ball."""
    client = FakeClient(scorecard=_live_scorecard(), commentary=commentary_payload)
    _, live, commentary = fetch_match_state(client, REF)  # type: ignore[arg-type]

    assert live is not None and live.recent_balls
    assert commentary is not None and commentary.items
    assert live.recent_balls[0].overs_actual == commentary.items[0].overs_actual


# ---------- non-live match: no live/commentary fetches ----------

def test_finished_match_skips_live_and_commentary() -> None:
    client = FakeClient(scorecard=_finished_scorecard())
    match, live, commentary = fetch_match_state(client, REF)  # type: ignore[arg-type]

    assert not match.is_live
    assert live is None and commentary is None
    assert client.calls == ["scorecard"]


# ---------- fallback: commentary unavailable ----------

def test_commentary_failure_falls_back_to_live_page() -> None:
    """If the commentary page fails, the live panel still works via live page."""
    live_payload = {
        "match": {
            "id": 1527150, "state": "LIVE", "liveInning": 1, "teams": [],
        },
        "content": {
            "supportInfo": {
                "liveSummary": {
                    "batsmen": [], "bowlers": [],
                    "recentBalls": [{"overNumber": 5, "oversActual": 4.3}],
                }
            }
        },
    }
    client = FakeClient(
        scorecard=_live_scorecard(),
        commentary_error=RuntimeError("commentary page 503"),
        live=live_payload,
    )
    match, live, commentary = fetch_match_state(client, REF)  # type: ignore[arg-type]

    assert match.is_live
    assert commentary is None  # commentary unavailable this cycle
    assert live is not None and live.recent_balls  # live still populated
    assert client.calls == ["scorecard", "commentary", "live"]
