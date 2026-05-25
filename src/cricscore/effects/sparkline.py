"""Unicode block-character sparklines."""

from __future__ import annotations

from collections.abc import Iterable

# Eight tiers of vertical block fill plus space for zero.
_BLOCKS = " ▁▂▃▄▅▆▇█"


def sparkline(values: Iterable[float | int | None]) -> str:
    """Render an inline bar chart from a sequence of numeric values.

    ``None`` and negative values are treated as zero. If every value is zero
    (or the input is empty) the result is the empty string so the caller
    can choose whether to render it at all.
    """
    clean = [max(0.0, float(v)) if v is not None else 0.0 for v in values]
    if not clean:
        return ""
    peak = max(clean)
    if peak == 0:
        return ""
    last_index = len(_BLOCKS) - 1
    return "".join(_BLOCKS[min(last_index, round(v / peak * last_index))] for v in clean)
