"""Fetch orchestration that keeps the live panel and commentary feed in sync.

ESPNCricinfo serves the ``live-cricket-score`` and ``ball-by-ball-commentary``
pages from independent caches, so they can be a ball or two apart at any given
moment.  Fetching the current-over chips from the live page and the commentary
from the commentary page therefore lets the two panels drift out of sync.

The commentary page already carries the **full live summary** (current
batsmen, the bowler, and ``recentBalls``) in ``content.supportInfo.liveSummary``
alongside the ``content.comments`` feed — and the two are generated together,
so they always describe the same most-recent delivery.  We exploit that by
deriving *both* :class:`LiveState` and :class:`Commentary` from a single
commentary-page fetch, guaranteeing the live panel and commentary update in
lockstep.  The dedicated live page is used only as a fallback when the
commentary fetch is unavailable.
"""

from __future__ import annotations

from cricscore.api.client import ESPNCricinfoClient
from cricscore.models import Match
from cricscore.models.match import Commentary, LiveState
from cricscore.url_parser import MatchRef


def fetch_match_state(
    client: ESPNCricinfoClient, match_ref: MatchRef
) -> tuple[Match, LiveState | None, Commentary | None]:
    """Fetch the scorecard plus, for live matches, in-sync live + commentary.

    The scorecard page is always fetched (it is the only page with the full
    innings/batting/bowling tables).  For a live match the live state and the
    commentary feed are then derived from one shared commentary-page fetch so
    the current-over chips and the commentary feed never disagree.
    """
    match = Match.from_scorecard_payload(client.fetch_scorecard(match_ref))
    if not match.is_live:
        return match, None, None
    live, commentary = _fetch_live_and_commentary(client, match_ref)
    return match, live, commentary


def _fetch_live_and_commentary(
    client: ESPNCricinfoClient, match_ref: MatchRef
) -> tuple[LiveState | None, Commentary | None]:
    """Derive a self-consistent ``(live, commentary)`` pair from one fetch."""
    try:
        raw = client.fetch_commentary(match_ref)
    except Exception:
        # Commentary page unavailable — fall back to the dedicated live page
        # so the live panel still works (no commentary this cycle).
        return _live_only(client, match_ref), None

    live: LiveState | None = None
    commentary: Commentary | None = None
    try:
        live = LiveState.from_live_payload(raw)
    except Exception:
        live = None
    try:
        commentary = Commentary.from_commentary_payload(raw)
    except Exception:
        commentary = None
    # If the commentary page somehow lacked live-summary data, fall back to
    # the dedicated live page for the live panel (commentary may still apply).
    if live is None:
        live = _live_only(client, match_ref)
    return live, commentary


def _live_only(
    client: ESPNCricinfoClient, match_ref: MatchRef
) -> LiveState | None:
    """Best-effort live state from the dedicated ``live-cricket-score`` page."""
    try:
        return LiveState.from_live_payload(client.fetch_live(match_ref))
    except Exception:
        return None
