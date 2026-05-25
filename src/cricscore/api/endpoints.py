"""URL builders for ESPNCricinfo.

The hidden JSON API at ``hs-consumer-api.espncricinfo.com`` is Akamai-gated
beyond what curl_cffi can defeat (verified 2026-05; returns 403 from all
Chrome / Safari / Edge / Firefox impersonation profiles even with warmed
cookies). The HTML pages, on the other hand, return 200 and embed the full
match payload in a ``__NEXT_DATA__`` script tag — that is what the data
layer actually fetches.

These URL builders intentionally use placeholder slugs (``x``/``y``).
ESPNCricinfo's edge layer redirects them to the canonical URL based on the
numeric ids alone.
"""

from __future__ import annotations

SITE_BASE = "https://www.espncricinfo.com"


def scorecard_page_url(series_id: int, match_id: int) -> str:
    """Full-scorecard HTML page URL."""
    return f"{SITE_BASE}/series/x-{series_id}/y-{match_id}/full-scorecard"


def match_home_page_url(series_id: int, match_id: int) -> str:
    """Match home page URL (toss, status, summary)."""
    return f"{SITE_BASE}/series/x-{series_id}/y-{match_id}/live-cricket-score"
