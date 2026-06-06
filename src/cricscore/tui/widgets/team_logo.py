"""Team-logo widget.

Prefers the **actual** ESPNCricinfo team logo, rendered as truecolor Unicode
half-blocks (so it looks like a real raster image inside the terminal).
Falls back to a pyfiglet ``smblock`` rendering of the abbreviation tinted
with the team's primary color when:

- no image path is supplied,
- the CDN fetch fails (network down, 404),
- Pillow / pyfiglet aren't importable for some reason.
"""

from __future__ import annotations

import logging

from rich.text import Text
from textual.widgets import Static

from cricscore.effects.gradient import _hex_to_rgb, _rgb_to_hex
from cricscore.tui.widgets._logo_image import render_team_logo

_log = logging.getLogger(__name__)

_DEFAULT_COLOR = "#f59f3a"
_DEFAULT_FIGLET_FONT = "smblock"
_DEFAULT_IMAGE_WIDTH = 14  # cells; height follows the source aspect


def _shaded(color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))


def _figlet_text(text: str, primary_color: str, font: str) -> Text:
    try:
        import pyfiglet
    except ImportError:
        return Text(text, style=f"bold {primary_color}")
    try:
        art = pyfiglet.figlet_format(text, font=font).rstrip("\n")
    except Exception:
        return Text(text, style=f"bold {primary_color}")

    lines = art.splitlines() or [text]
    out = Text()
    last = max(1, len(lines) - 1)
    for i, line in enumerate(lines):
        factor = 1.0 - (0.25 * (i / last))
        out.append(line, style=f"bold {_shaded(primary_color, factor)}")
        if i < last:
            out.append("\n")
    return out


# Re-exported for the unit tests, which assert on these helpers directly.
_build_logo_text = _figlet_text


class TeamLogo(Static):
    """Logo for one team — image-based when possible, ASCII fallback otherwise."""

    DEFAULT_CSS = ""

    def __init__(
        self,
        abbreviation: str | None,
        primary_color: str | None = None,
        image_path: str | None = None,
        *,
        font: str = _DEFAULT_FIGLET_FONT,
        width_cells: int = _DEFAULT_IMAGE_WIDTH,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        label = (abbreviation or "?").upper()
        color = primary_color or _DEFAULT_COLOR
        text = self._build(label, color, image_path, font, width_cells)
        super().__init__(text, id=id, classes=classes)
        self.abbreviation = label
        self.primary_color = color
        self.image_path = image_path

    @staticmethod
    def _build(
        label: str,
        color: str,
        image_path: str | None,
        font: str,
        width_cells: int,
    ) -> Text:
        if image_path:
            try:
                return render_team_logo(image_path, width_cells=width_cells)
            except Exception as exc:  # network, decode, Pillow missing — all fall through
                _log.debug("Falling back to figlet logo for %s: %s", label, exc)
        return _figlet_text(label, color, font)
