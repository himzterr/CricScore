"""Tests for the half-block image renderer + URL/cache helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from rich.text import Text

from cricscore.tui.widgets._logo_image import (
    cache_dir,
    cdn_url,
    fetch_logo_bytes,
    image_to_half_block_text,
)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Each test gets its own throwaway cache dir."""
    monkeypatch.setenv("CRICSCORE_CACHE_DIR", str(tmp_path))
    return tmp_path / "logos"


def _solid_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    img = Image.new("RGBA", (width, height), rgba)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestUrlAndCache:
    def test_cdn_url_prepends_base(self) -> None:
        assert cdn_url("/lsci/db/PICTURES/CMS/313400/313422.logo.png") == (
            "https://img1.hscicdn.com/image/upload"
            "/lsci/db/PICTURES/CMS/313400/313422.logo.png"
        )

    def test_cdn_url_handles_missing_leading_slash(self) -> None:
        assert cdn_url("logo.png").startswith("https://img1.hscicdn.com/image/upload/")

    def test_cache_dir_created_under_env_override(self, isolated_cache: Path) -> None:
        path = cache_dir()
        assert path == isolated_cache
        assert path.exists()


class TestImageToHalfBlocks:
    def test_returns_text_object(self) -> None:
        png = _solid_png(8, 8, (255, 0, 0, 255))
        result = image_to_half_block_text(png, width_cells=8)
        assert isinstance(result, Text)
        assert "▀" in result.plain

    def test_width_cells_controls_columns(self) -> None:
        png = _solid_png(20, 20, (0, 255, 0, 255))
        result = image_to_half_block_text(png, width_cells=12)
        first_line = result.plain.splitlines()[0]
        assert len(first_line) == 12

    def test_height_pairs_pixels(self) -> None:
        # Square source, width 10 → 10 columns × 5 char-rows (each = 2 pixels).
        png = _solid_png(20, 20, (0, 0, 255, 255))
        result = image_to_half_block_text(png, width_cells=10)
        lines = result.plain.splitlines()
        assert len(lines) == 5

    def test_solid_color_image_yields_uniform_style(self) -> None:
        png = _solid_png(6, 6, (250, 140, 22, 255))
        result = image_to_half_block_text(png, width_cells=6)
        styles = {str(span.style) for span in result.spans}
        # The accent orange should appear in at least one span's style string.
        assert any("#fa8c16" in s.lower() for s in styles)

    def test_transparency_composites_onto_background(self) -> None:
        # Fully transparent image should render entirely as the background color.
        png = _solid_png(4, 4, (0, 0, 0, 0))
        result = image_to_half_block_text(png, width_cells=4, background=(11, 22, 33))
        styles = {str(span.style) for span in result.spans}
        assert any("#0b1621" in s.lower() for s in styles)


class TestFetchLogoBytes:
    def test_reads_from_cache_without_network(self, isolated_cache: Path) -> None:
        # Pre-seed the cache file the function would otherwise download.
        from cricscore.tui.widgets._logo_image import _cache_filename

        path = "/lsci/test/abc.png"
        payload = _solid_png(2, 2, (1, 2, 3, 255))
        target = isolated_cache / _cache_filename(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

        assert fetch_logo_bytes(path) == payload
