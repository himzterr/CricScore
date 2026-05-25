"""Pure-Python implementation of the scorecard fetcher.

ESPNCricinfo's hidden JSON API (``hs-consumer-api.espncricinfo.com``) is
gated by Akamai with checks beyond TLS fingerprinting — it returns 403 even
from a real-browser-shaped curl_cffi session. The HTML page, however,
returns 200 and embeds the full scorecard in a ``__NEXT_DATA__`` script tag.
That is what we scrape here.

The endpoint URL only needs the numeric ids: ESPNCricinfo redirects
placeholder slugs (e.g. ``/series/x-<series_id>/y-<match_id>/full-scorecard``)
to the canonical URL automatically.
"""

from __future__ import annotations

import json
import re
from typing import Any

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(?P<json>.*?)</script>',
    re.DOTALL,
)

# Headers that, combined with curl_cffi's Chrome TLS fingerprint, look
# indistinguishable from a real browser navigation.
_BROWSER_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

_HOMEPAGE_URL = "https://www.espncricinfo.com/"


class ScorecardFetchError(RuntimeError):
    """Raised when the ESPNCricinfo scorecard page cannot be fetched or parsed."""


def _scorecard_page_url(series_id: int, match_id: int) -> str:
    """Build a scorecard page URL. Slugs are placeholders — ESPN redirects."""
    return (
        f"https://www.espncricinfo.com/series/x-{series_id}/y-{match_id}/full-scorecard"
    )


def python_fetch_raw_scorecard(
    series_id: int, match_id: int, timeout: float = 15.0
) -> dict[str, Any]:
    """Fetch + parse the scorecard payload from the HTML page.

    Returns the slice of ``__NEXT_DATA__`` rooted at
    ``props.appPageProps.data`` — the dict containing ``match`` and
    ``content.innings`` — which is what the pydantic models in
    :mod:`cricscore.models.match` consume.
    """
    # Imported lazily so the native shim's fallback doesn't drag curl_cffi
    # into processes that don't need it.
    from curl_cffi import requests  # type: ignore[import-not-found]

    session = requests.Session(impersonate="chrome131")
    try:
        # Akamai issues clearance cookies on the first homepage hit. Without
        # this warm-up the scorecard page also returns 403.
        session.get(_HOMEPAGE_URL, headers=_BROWSER_HEADERS, timeout=timeout)
        page_url = _scorecard_page_url(series_id, match_id)
        response = session.get(page_url, headers=_BROWSER_HEADERS, timeout=timeout)
    except Exception as exc:
        raise ScorecardFetchError(f"Network error fetching scorecard: {exc}") from exc

    if response.status_code != 200:
        raise ScorecardFetchError(
            f"Scorecard page returned HTTP {response.status_code} "
            f"for series_id={series_id} match_id={match_id}"
        )

    return extract_next_data(response.text)


def extract_next_data(html: str) -> dict[str, Any]:
    """Pull ``props.appPageProps.data`` out of a scorecard HTML page.

    Public for tests: lets us validate parsing against a saved HTML fixture
    without making a live network call.
    """
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise ScorecardFetchError(
            "Could not locate __NEXT_DATA__ in the scorecard page HTML"
        )
    try:
        payload = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise ScorecardFetchError(f"__NEXT_DATA__ was not valid JSON: {exc}") from exc

    try:
        data: dict[str, Any] = payload["props"]["appPageProps"]["data"]
    except (KeyError, TypeError) as exc:
        raise ScorecardFetchError(
            f"__NEXT_DATA__ structure missing expected path "
            f"props.appPageProps.data: {exc}"
        ) from exc

    if not isinstance(data, dict) or "match" not in data:
        raise ScorecardFetchError(
            "__NEXT_DATA__ payload did not contain a 'match' key"
        )
    return data
