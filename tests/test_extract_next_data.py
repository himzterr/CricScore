from __future__ import annotations

import json

import pytest

from cricscore.api._python_client import ScorecardFetchError, extract_next_data


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
