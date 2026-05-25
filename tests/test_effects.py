"""Unit tests for the visual effects helpers (no Textual involved)."""

from __future__ import annotations

import pytest
from rich.text import Text

from cricscore.effects import gradient_text, sparkline


class TestGradient:
    def test_empty_input_returns_empty(self) -> None:
        assert gradient_text("", "#000000", "#ffffff").plain == ""

    def test_single_character_uses_start_color(self) -> None:
        result = gradient_text("X", "#ff0000", "#00ff00")
        assert result.plain == "X"
        # Span style includes the start color
        assert any("#ff0000" in str(span.style) for span in result.spans)

    def test_endpoints_match_start_and_end(self) -> None:
        result = gradient_text("AZ", "#000000", "#ffffff")
        # First and last characters should carry the endpoint colors.
        styles = [str(span.style) for span in result.spans]
        assert any("#000000" in s for s in styles)
        assert any("#ffffff" in s for s in styles)

    def test_per_character_styling(self) -> None:
        result = gradient_text("hello", "#100020", "#a0c0e0")
        # One span per character → five spans
        assert len(result.spans) == 5
        # Each span covers exactly one character.
        for span in result.spans:
            assert span.end - span.start == 1

    def test_bold_flag_added(self) -> None:
        result = gradient_text("hi", "#000000", "#ffffff", bold=True)
        assert all("bold" in str(span.style) for span in result.spans)

    def test_short_hex_accepted(self) -> None:
        result = gradient_text("AB", "#f0a", "#0af")
        assert isinstance(result, Text)
        assert result.plain == "AB"

    def test_invalid_hex_raises(self) -> None:
        with pytest.raises(ValueError):
            gradient_text("X", "#zzzz", "#000000")


class TestSparkline:
    def test_empty_input_returns_empty(self) -> None:
        assert sparkline([]) == ""

    def test_all_zero_returns_empty(self) -> None:
        assert sparkline([0, 0, 0]) == ""

    def test_monotonic_climb(self) -> None:
        # Values 0..7 should produce 8 distinct block levels, ending at full block.
        out = sparkline([0, 1, 2, 3, 4, 5, 6, 7])
        assert out[-1] == "█"
        # Length always matches input length
        assert len(out) == 8

    def test_none_values_treated_as_zero(self) -> None:
        out = sparkline([None, 5, None])
        assert len(out) == 3
        # First and last should be the lowest tier (space)
        assert out[0] == " "
        assert out[-1] == " "

    def test_negative_values_clamped_to_zero(self) -> None:
        out = sparkline([-3, 5])
        assert out[0] == " "
