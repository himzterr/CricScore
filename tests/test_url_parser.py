from __future__ import annotations

import pytest

from cricscore.url_parser import InvalidUrlError, MatchRef, parse_match_url


IPL_URL = (
    "https://www.espncricinfo.com/series/ipl-2026-1510719/"
    "kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard"
)


def test_parses_canonical_ipl_url() -> None:
    assert parse_match_url(IPL_URL) == MatchRef(series_id=1510719, match_id=1529313)


def test_parses_without_www_subdomain() -> None:
    url = IPL_URL.replace("www.espncricinfo.com", "espncricinfo.com")
    assert parse_match_url(url) == MatchRef(series_id=1510719, match_id=1529313)


def test_tolerates_query_and_fragment() -> None:
    url = IPL_URL + "?foo=bar#section"
    assert parse_match_url(url) == MatchRef(series_id=1510719, match_id=1529313)


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "not-a-url",
        "ftp://www.espncricinfo.com/series/x-1/y-2/full-scorecard",
        "https://example.com/series/x-1/y-2/full-scorecard",
        "https://www.espncricinfo.com/",
        "https://www.espncricinfo.com/series/ipl-2026-1510719/",
        "https://www.espncricinfo.com/series/ipl-2026-1510719/match-1529313/commentary",
        "https://www.espncricinfo.com/series/ipl-no-id/match-no-id/full-scorecard",
    ],
)
def test_rejects_bad_urls(bad_url: str) -> None:
    with pytest.raises(InvalidUrlError):
        parse_match_url(bad_url)
