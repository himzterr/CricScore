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


# espncricinfo.com and its cricinfo.com alias, each with an optional "www.".
_HOST_PATTERN = re.compile(r"^(www\.)?(espn)?cricinfo\.com$", re.IGNORECASE)
_ESPN_HOST_PATTERN = re.compile(r"^(www\.)?espn\.com$", re.IGNORECASE)
_ESPN_PATH_PATTERN = re.compile(
    r"^/cricket/series/(?P<series>[0-9]+)/game/(?P<match>[0-9]+)(?:/[^/]*)?/?$"
)
_SERIES_SEGMENT = re.compile(r"^(?P<slug>.+)-(?P<id>\d+)$")
_MATCH_SEGMENT = re.compile(r"^(?P<slug>.+)-(?P<id>\d+)$")


def parse_match_url(url: str) -> MatchRef:
    """Parse an ESPNCricinfo match URL into a MatchRef.

    Accepts any match sub-page URL shaped like::

        https://www.espncricinfo.com/series/<series-slug>-<series_id>/
            <match-slug>-<match_id>/<sub-page>

    where ``<sub-page>`` is any suffix (``full-scorecard``,
    ``live-cricket-score``, ``ball-by-ball-commentary``, etc.).  The
    ``cricinfo.com`` alias is accepted for the host, with or without a ``www.``
    prefix. ESPN's ``/cricket/series/<id>/game/<id>/<slug>`` format is also
    accepted: Cricinfo resolves its legacy series id to the canonical series.
    Only the ids matter downstream, since fetches are always issued
    against ``www.espncricinfo.com``.  Query strings and fragments are ignored.
    Raises :class:`InvalidUrlError` for anything that doesn't contain both a
    valid series id and a valid match id.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidUrlError("URL must be a non-empty string")

    # Pasted links may be wrapped across lines with indentation.
    parsed = urlparse("".join(url.split()))
    if parsed.scheme not in {"http", "https"}:
        raise InvalidUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if _ESPN_HOST_PATTERN.fullmatch(parsed.netloc):
        match = _ESPN_PATH_PATTERN.fullmatch(parsed.path)
        if not match:
            raise InvalidUrlError(
                "Expected an ESPN match URL: /cricket/series/<id>/game/<id>/<slug>"
            )
        return MatchRef(series_id=int(match["series"]), match_id=int(match["match"]))
    if not parsed.netloc or not _HOST_PATTERN.fullmatch(parsed.netloc):
        raise InvalidUrlError(
            f"Not an espncricinfo.com, cricinfo.com or espn.com URL: {parsed.netloc!r}"
        )

    segments = [seg for seg in parsed.path.split("/") if seg]
    # Expected shape: ['series', '<slug>-<id>', '<slug>-<id>', '<sub-page>', ...]
    if len(segments) < 3 or segments[0] != "series":
        raise InvalidUrlError(
            "URL does not look like an ESPNCricinfo match URL: "
            "expected /series/<series-slug>-<id>/<match-slug>-<id>/<sub-page>"
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
