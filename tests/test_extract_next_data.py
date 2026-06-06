from __future__ import annotations

import json

import pytest

from cricscore.api._python_client import (
    ScorecardFetchError,
    extract_live_data,
    extract_next_data,
)


def _wrap_html(next_data_dict: dict) -> str:
    body = json.dumps(next_data_dict)
    return (
        "<html><head></head><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{body}</script>'
        "</body></html>"
    )


def test_extracts_data_block() -> None:
    payload = {
        "props": {
            "appPageProps": {
                "data": {"match": {"id": 42}, "content": {"innings": []}}
            }
        }
    }
    result = extract_next_data(_wrap_html(payload))
    assert result == {"match": {"id": 42}, "content": {"innings": []}}


def test_missing_next_data_script_raises() -> None:
    with pytest.raises(ScorecardFetchError, match="__NEXT_DATA__"):
        extract_next_data("<html><body>nothing here</body></html>")


def test_invalid_json_raises() -> None:
    html = (
        '<script id="__NEXT_DATA__" type="application/json">not json</script>'
    )
    with pytest.raises(ScorecardFetchError, match="valid JSON"):
        extract_next_data(html)


def test_missing_data_path_raises() -> None:
    bad = {"props": {"appPageProps": {}}}
    with pytest.raises(ScorecardFetchError, match="props.appPageProps.data"):
        extract_next_data(_wrap_html(bad))


def test_missing_match_key_raises() -> None:
    bad = {"props": {"appPageProps": {"data": {"content": {}}}}}
    with pytest.raises(ScorecardFetchError, match="'match' key"):
        extract_next_data(_wrap_html(bad))


# ---------- extract_live_data ----------

def test_extract_live_data_nested_shape() -> None:
    """Live page wraps data one level deeper than scorecard page."""
    payload = {
        "props": {
            "appPageProps": {
                "data": {
                    "sponsoredFeatures": [],
                    "data": {
                        "match": {"id": 99, "state": "LIVE"},
                        "content": {"supportInfo": {}},
                    },
                }
            }
        }
    }
    result = extract_live_data(_wrap_html(payload))
    assert result["match"]["id"] == 99
    assert result["match"]["state"] == "LIVE"


def test_extract_live_data_flat_shape() -> None:
    """If data already has 'match' at the outer level (scorecard shape), accept it."""
    payload = {
        "props": {
            "appPageProps": {
                "data": {"match": {"id": 77}, "content": {}}
            }
        }
    }
    result = extract_live_data(_wrap_html(payload))
    assert result["match"]["id"] == 77


def test_extract_live_data_missing_match_raises() -> None:
    bad = {
        "props": {
            "appPageProps": {
                "data": {"data": {"content": {}}}
            }
        }
    }
    with pytest.raises(ScorecardFetchError, match="'match' key"):
        extract_live_data(_wrap_html(bad))
