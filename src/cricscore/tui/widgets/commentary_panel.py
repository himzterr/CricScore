"""Ball-by-ball commentary panel — scrollable feed below the scoreboard.

Shows the most recent ~18 deliveries from the ``ball-by-ball-commentary``
page. Updated on every live-refresh tick (same 20s cycle as the scoreboard
and live panel). When a new delivery arrives the newest row briefly
flashes amber so the update is visible without disrupting reading.
"""

from __future__ import annotations

import contextlib

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label, Static

from cricscore.models.match import Commentary, CommentaryItem

# Reuse the same palette constants as live_panel.py
_ACCENT = "#f59f3a"
_SUCCESS = "#5dd39e"
_DANGER = "#f05a5a"
_DIM = "#5b6981"
_MUTED = "#9aa6bd"


def _render_item(item: CommentaryItem) -> Text:
    """Build a two-line Rich Text block for one delivery."""
    line = Text()

    # ── Over label ──
    line.append(f"  {item.over_label}", style=_DIM)
    line.append("  ", style="")

    # ── Outcome chip ──
    outcome = item.outcome
    if outcome == "W":
        chip_style = f"bold {_DANGER}"
    elif outcome in ("4", "6"):
        chip_style = f"bold {_ACCENT}"
    elif any(outcome.startswith(pfx) for pfx in ("Wd", "Nb", "By", "Lb")):
        chip_style = _MUTED
    else:
        chip_style = _SUCCESS if outcome != "0" else _DIM
    line.append(f"[{outcome}]", style=chip_style)
    line.append("  ", style="")

    # ── Title (bowler → batsman) ──
    if item.title:
        line.append(item.title, style=f"bold {_MUTED}")

    # ── Commentary text (second line) ──
    text = item.text
    if text:
        line.append(f"\n        {text}", style=_DIM)

    # ── Dismissal detail in red (third line, wickets only) ──
    if item.is_wicket and item.dismissal_text:
        detail = item.dismissal_text.long or item.dismissal_text.short
        if detail:
            line.append(f"\n        {detail}", style=f"bold {_DANGER}")

    return line


class CommentaryPanel(VerticalScroll):
    """Scrollable delivery-by-delivery commentary feed for a live match.

    ``items`` comes from the ``ball-by-ball-commentary`` page
    (newest-first). Updated every ~20s via :meth:`update_commentary`.
    """

    DEFAULT_CSS = ""

    def __init__(self, commentary: Commentary, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._commentary = commentary
        self._last_top_uid: int | None = None

    # ---------- compose ----------

    def compose(self) -> ComposeResult:
        yield Label("Commentary", classes="section-heading commentary-heading")
        for item in self._commentary.items:
            yield self._make_item_static(item, flash=False)

    # ---------- helpers ----------

    def _make_item_static(self, item: CommentaryItem, *, flash: bool) -> Static:
        """Return a styled Static for one delivery.

        No ``id`` is assigned — item Statics are identified by their position
        in the ``".commentary-item"`` query rather than by ID, which avoids
        Textual ``DuplicateIds`` errors when remove() and mount() are called
        in the same synchronous turn (remove is deferred; mount is immediate).
        """
        classes = "commentary-item"
        if flash:
            classes += " newly-arrived"
        return Static(_render_item(item), classes=classes)

    # ---------- live update ----------

    def update_commentary(self, commentary: Commentary) -> None:
        """Replace the delivery rows with fresh data.

        Performs an in-place DOM rebuild (no animations). If the newest
        delivery uid differs from the last seen, applies a transient amber
        highlight to the new top row and removes it after 0.8 s.
        """
        self._commentary = commentary

        new_top_uid = commentary.items[0].comment_id if commentary.items else None
        is_new = new_top_uid is not None and new_top_uid != self._last_top_uid

        # Remove existing delivery rows (keep the heading label).
        for widget in list(self.query(".commentary-item")):
            widget.remove()

        # Mount fresh rows.
        new_widgets = [
            self._make_item_static(item, flash=(i == 0 and is_new))
            for i, item in enumerate(commentary.items)
        ]
        if new_widgets:
            self.mount(*new_widgets)

        if is_new and new_widgets:
            self._last_top_uid = new_top_uid
            # Capture the top widget by reference to remove the flash class.
            # (IDs are not used on item Statics to avoid DuplicateIds errors
            # when remove() and mount() race in the same synchronous turn.)
            top_widget: Static = new_widgets[0]

            def _remove_flash() -> None:
                with contextlib.suppress(Exception):
                    top_widget.remove_class("newly-arrived")

            self.set_timer(0.8, _remove_flash)
