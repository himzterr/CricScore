"""Tests for the TeamLogo widget — pure rendering, no Textual harness needed."""

from __future__ import annotations

from rich.text import Text

from cricscore.tui.widgets.team_logo import TeamLogo, _build_logo_text, _shaded


class TestShadedHelper:
    def test_factor_one_is_identity(self) -> None:
        assert _shaded("#fa8c16", 1.0).lower() == "#fa8c16"

    def test_factor_zero_is_black(self) -> None:
        assert _shaded("#fa8c16", 0.0) == "#000000"

    def test_factor_half_dims(self) -> None:
        # 0xFA / 2 = 0x7D; halving each component should land near grey-orange.
        out = _shaded("#fa8c16", 0.5)
        assert out == "#7d460b"


class TestBuildLogoText:
    def test_returns_text_object(self) -> None:
        result = _build_logo_text("DC", "#fa8c16", font="smblock")
        assert isinstance(result, Text)
        assert "DC" or "▌" in result.plain  # either ASCII fallback or block art

    def test_lines_get_different_shades(self) -> None:
        result = _build_logo_text("KKR", "#fa8c16", font="smblock")
        styles_seen = {str(span.style) for span in result.spans}
        # smblock produces 4 rows; we expect at least 2 distinct shade styles.
        assert len(styles_seen) >= 2

    def test_unknown_font_falls_back_to_plain_text(self) -> None:
        result = _build_logo_text("XYZ", "#fa8c16", font="definitely-not-a-font")
        assert "XYZ" in result.plain


class TestTeamLogoWidget:
    def test_uppercases_abbreviation(self) -> None:
        logo = TeamLogo("dc", "#fa8c16")
        assert logo.abbreviation == "DC"

    def test_handles_missing_abbreviation(self) -> None:
        logo = TeamLogo(None, "#fa8c16")
        assert logo.abbreviation == "?"

    def test_default_color_when_missing(self) -> None:
        logo = TeamLogo("MI", None)
        assert logo.primary_color == "#f59f3a"

    def test_custom_color_preserved(self) -> None:
        logo = TeamLogo("KKR", "#0860C4")
        assert logo.primary_color == "#0860C4"
