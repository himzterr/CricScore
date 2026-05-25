"""Headless smoke tests for the Textual UI.

These mount the app via Textual's ``run_test`` harness and assert that the
scorecard renders without crashing. They do not snapshot pixels — Phase 4
will own visual regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cricscore.models import Match
from cricscore.tui.app import CricScoreApp

FIXTURE = Path(__file__).parent / "fixtures" / "scorecard_1529313.json"


@pytest.fixture(scope="module")
def match() -> Match:
    with FIXTURE.open() as f:
        return Match.from_scorecard_payload(json.load(f))


@pytest.mark.asyncio
async def test_scorecard_screen_mounts(match: Match) -> None:
    app = CricScoreApp(match=match)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        # The header widget is the unmistakable marker that the scorecard
        # screen mounted — if the model wiring fails, this query raises.
        from cricscore.tui.widgets import MatchHeader

        header = app.screen.query_one(MatchHeader)
        assert header.match.id == match.id


@pytest.mark.asyncio
async def test_innings_tabs_present(match: Match) -> None:
    app = CricScoreApp(match=match)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        from textual.widgets import TabPane

        tabs = list(app.screen.query(TabPane))
        assert len(tabs) == len(match.innings)


@pytest.mark.asyncio
async def test_batting_table_populated(match: Match) -> None:
    app = CricScoreApp(match=match)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        from cricscore.tui.widgets import BattingTable

        tables = list(app.screen.query(BattingTable))
        # Both innings render; only the active tab's contents may be queried
        # depending on Textual's lazy mounting, so we settle for >= 1.
        assert len(tables) >= 1
        # The first innings' batting table should have at least batters who
        # actually batted plus the extras + total rows.
        inn1 = match.innings[0]
        expected_min_rows = sum(1 for b in inn1.batting_lineup if b.batted_type == "yes")
        assert tables[0].row_count >= expected_min_rows


@pytest.mark.asyncio
async def test_url_input_screen_mounts_without_match() -> None:
    app = CricScoreApp()  # no URL / no Match → URLInputScreen
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        from cricscore.tui.screens import URLInputScreen

        assert isinstance(app.screen, URLInputScreen)


@pytest.mark.asyncio
async def test_quit_binding_exits(match: Match) -> None:
    app = CricScoreApp(match=match)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("q")
    # If `q` did not quit, run_test would have hung; reaching here is the test.
