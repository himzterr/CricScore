"""Extract series and match identifiers from an ESPNCricinfo scorecard URL."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


class InvalidUrlError(ValueError):
    """Raised when a URL is not a recognized ESPNCricinfo scorecard URL."""


@dataclass(frozen=True, slots=True)
class MatchRef:
    series_id: int
    match_id: int


_HOST_PATTERN = re.compile(r"^(www\.)?espncricinfo\.com$", re.IGNORECASE)
_SERIES_SEGMENT = re.compile(r"^(?P<slug>.+)-(?P<id>\d+)$")
_MATCH_SEGMENT = re.compile(r"^(?P<slug>.+)-(?P<id>\d+)$")


def parse_match_url(url: str) -> MatchRef:
    """Parse an ESPNCricinfo full-scorecard URL into a MatchRef.

    Accepts URLs shaped like:
        https://www.espncricinfo.com/series/<series-slug>-<series_id>/
            <match-slug>-<match_id>/full-scorecard

    Trailing segments after ``full-scorecard`` (query strings, fragments) are
    ignored. Raises :class:`InvalidUrlError` for anything else.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidUrlError("URL must be a non-empty string")

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise InvalidUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if not parsed.netloc or not _HOST_PATTERN.match(parsed.netloc):
        raise InvalidUrlError(f"Not an espncricinfo.com URL: {parsed.netloc!r}")

    segments = [seg for seg in parsed.path.split("/") if seg]
    # Expected shape: ['series', '<slug>-<id>', '<slug>-<id>', 'full-scorecard', ...]
    if len(segments) < 4 or segments[0] != "series" or "full-scorecard" not in segments[3:4]:
        raise InvalidUrlError(
            "URL does not match the espncricinfo full-scorecard pattern: "
            "/series/<slug>-<id>/<slug>-<id>/full-scorecard"
        )

    series_match = _SERIES_SEGMENT.match(segments[1])
    match_match = _MATCH_SEGMENT.match(segments[2])
    if not series_match or not match_match:
        raise InvalidUrlError(
            "Could not extract series or match id from URL path segments"
        )

    return MatchRef(
        series_id=int(series_match.group("id")),
        match_id=int(match_match.group("id")),
    )
