"""Helpers for fetching ESPNCricinfo team logos and rendering them in-terminal.

A Unicode upper-half-block (``▀``) lets one terminal cell carry two pixels of
vertical resolution — foreground = top pixel, background = bottom pixel. That
gives recognizable raster art in any truecolor terminal without a separate
sixel/iTerm/Kitty image protocol.
"""

from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path

from rich.text import Text

_CDN_BASE = "https://img1.hscicdn.com/image/upload"
_REFERER = "https://www.espncricinfo.com/"
_USER_AGENT_PROFILE = "chrome131"


def cache_dir() -> Path:
    """Disk cache for downloaded logos. Created on first call."""
    base = Path(os.environ.get("CRICSCORE_CACHE_DIR", Path.home() / ".cache" / "cricscore"))
    logo_dir = base / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    return logo_dir


def cdn_url(image_path: str) -> str:
    """Build the full CDN URL for an ESPNCricinfo image path."""
    if not image_path.startswith("/"):
        image_path = "/" + image_path
    return f"{_CDN_BASE}{image_path}"


def _cache_filename(image_path: str) -> str:
    base = os.path.basename(image_path) or "logo"
    digest = hashlib.sha1(image_path.encode("utf-8")).hexdigest()[:10]
    safe = "".join(c for c in base if c.isalnum() or c in "._-")
    return f"{digest}-{safe}"


def fetch_logo_bytes(image_path: str, *, timeout: float = 10.0) -> bytes:
    """Download the logo (with disk cache). Raises on network/HTTP errors."""
    cache_path = cache_dir() / _cache_filename(image_path)
    if cache_path.exists():
        return cache_path.read_bytes()

    # Imported lazily — pure rendering paths don't need curl_cffi loaded.
    from curl_cffi import requests  # type: ignore[import-not-found]

    response = requests.get(
        cdn_url(image_path),
        impersonate=_USER_AGENT_PROFILE,
        headers={"Referer": _REFERER},
        timeout=timeout,
    )
    response.raise_for_status()
    payload: bytes = response.content
    cache_path.write_bytes(payload)
    return payload


def image_to_half_block_text(
    image_bytes: bytes,
    *,
    width_cells: int = 14,
    background: tuple[int, int, int] = (15, 22, 34),
) -> Text:
    """Render image bytes as a Rich ``Text`` using Unicode half-blocks.

    ``width_cells`` is the rendered width in terminal columns. The height is
    derived from the source image's aspect ratio (every cell carries two
    vertical pixels via the half-block trick). Transparent pixels are
    composited onto ``background`` so transparent logos blend cleanly with
    the TUI surface.
    """
    from PIL import Image  # local import keeps the module light

    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    if img.width == 0 or img.height == 0:
        return Text("")

    aspect = img.height / img.width
    width = max(2, int(width_cells))
    pixel_height = max(2, int(round(width * aspect)))
    if pixel_height % 2:  # we consume pixel rows in pairs
        pixel_height += 1
    img = img.resize((width, pixel_height), Image.LANCZOS)

    canvas = Image.new("RGBA", img.size, background + (255,))
    img = Image.alpha_composite(canvas, img).convert("RGB")

    out = Text()
    pixels = img.load()
    for y in range(0, pixel_height, 2):
        for x in range(width):
            tr, tg, tb = pixels[x, y]
            br, bgc, bb = pixels[x, y + 1]
            out.append(
                "▀",
                style=f"#{tr:02x}{tg:02x}{tb:02x} on #{br:02x}{bgc:02x}{bb:02x}",
            )
        if y + 2 < pixel_height:
            out.append("\n")
    return out


def render_team_logo(
    image_path: str,
    *,
    width_cells: int = 14,
    background: tuple[int, int, int] = (15, 22, 34),
    timeout: float = 8.0,
) -> Text:
    """Fetch and render the team logo. Raises on download or decode failure."""
    payload = fetch_logo_bytes(image_path, timeout=timeout)
    return image_to_half_block_text(
        payload, width_cells=width_cells, background=background
    )
