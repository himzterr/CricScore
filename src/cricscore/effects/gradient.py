"""Per-character color gradients built on rich.text.Text."""

from __future__ import annotations

from rich.text import Text


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {value!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def gradient_text(
    text: str,
    start: str,
    end: str,
    *,
    bold: bool = False,
) -> Text:
    """Return a Rich ``Text`` whose characters interpolate from ``start`` to ``end``.

    ``start`` and ``end`` are hex colors like ``"#f59f3a"``. Whitespace is
    preserved but rendered with the interpolated style so the run reads as a
    smooth band of color even when the source contains spaces.
    """
    if not text:
        return Text("")

    sr, sg, sb = _hex_to_rgb(start)
    er, eg, eb = _hex_to_rgb(end)
    style_suffix = " bold" if bold else ""

    result = Text()
    if len(text) == 1:
        result.append(text, style=start + style_suffix)
        return result

    for i, ch in enumerate(text):
        t = i / (len(text) - 1)
        r = int(sr + (er - sr) * t)
        g = int(sg + (eg - sg) * t)
        b = int(sb + (eb - sb) * t)
        result.append(ch, style=_rgb_to_hex(r, g, b) + style_suffix)
    return result
