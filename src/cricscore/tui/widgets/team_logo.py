"""Text-art team logo built with pyfiglet.

We render the team abbreviation in the ``smblock`` figlet font — 4 rows of
Unicode block characters — and tint it with the team's ESPNCricinfo
``primaryColor``. A subtle vertical gradient (full color at top, fading
about 20 % toward black at the bottom) gives the block art a bit of depth
without obscuring the team color.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from cricscore.effects.gradient import _hex_to_rgb, _rgb_to_hex

_DEFAULT_COLOR = "#f59f3a"
_DEFAULT_FONT = "smblock"


def _shaded(color: str, factor: float) -> str:
    """Return ``color`` scaled toward black by ``factor`` in [0, 1]."""
    r, g, b = _hex_to_rgb(color)
    return _rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))


def _render_ascii(text: str, font: str) -> str:
    try:
        import pyfiglet  # local import — keeps the widget cheap to import
    except ImportError:
        return text
    try:
        return pyfiglet.figlet_format(text, font=font).rstrip("\n")
    except Exception:
        return text


def _build_logo_text(abbreviation: str, primary_color: str, font: str) -> Text:
    art = _render_ascii(abbreviation, font)
    lines = art.splitlines() or [abbreviation]
    out = Text()
    last = max(1, len(lines) - 1)
    for i, line in enumerate(lines):
        # Linear shade from 1.0 (top) to 0.75 (bottom).
        factor = 1.0 - (0.25 * (i / last))
        out.append(line, style=f"bold {_shaded(primary_color, factor)}")
        if i < last:
            out.append("\n")
    return out


class TeamLogo(Static):
    """Static widget that displays a team's abbreviation as block-letter art."""

    DEFAULT_CSS = ""

    def __init__(
        self,
        abbreviation: str | None,
        primary_color: str | None = None,
        *,
        font: str = _DEFAULT_FONT,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        label = (abbreviation or "?").upper()
        color = primary_color or _DEFAULT_COLOR
        text = _build_logo_text(label, color, font)
        super().__init__(text, id=id, classes=classes)
        self.abbreviation = label
        self.primary_color = color
