"""Typewriter widget — reveals text one character at a time."""

from __future__ import annotations

from rich.console import RenderableType
from rich.text import Text
from textual.widgets import Static


class TypewriterLabel(Static):
    """A ``Static`` that reveals its target text character-by-character on mount.

    Once the full target has been rendered the timer cancels itself.
    The widget keeps the cursor visible only while typing — see ``cursor``.
    """

    DEFAULT_CSS = ""

    def __init__(
        self,
        text: str,
        *,
        style: str = "",
        delay: float = 0.025,
        cursor: str = "▋",
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__("", id=id, classes=classes)
        self._target = text
        self._style = style
        self._delay = max(0.005, delay)
        self._cursor = cursor
        self._index = 0
        self._timer = None

    def on_mount(self) -> None:
        if not self._target:
            self.update(Text(""))
            return
        self._render_progress()
        self._timer = self.set_interval(self._delay, self._tick)

    def _tick(self) -> None:
        if self._index >= len(self._target):
            if self._timer is not None:
                self._timer.stop()
                self._timer = None
            self.update(Text(self._target, style=self._style))
            return
        self._index += 1
        self._render_progress()

    def _render_progress(self) -> None:
        visible = self._target[: self._index]
        text = Text(visible, style=self._style)
        if self._index < len(self._target) and self._cursor:
            text.append(self._cursor, style=self._style or "dim")
        self.update(text)

    def reset_to(self, new_text: str) -> None:
        """Restart the animation with a different target."""
        if self._timer is not None:
            self._timer.stop()
        self._target = new_text
        self._index = 0
        if self.is_mounted:
            self._render_progress()
            self._timer = self.set_interval(self._delay, self._tick)

    def render(self) -> RenderableType:  # pragma: no cover - Static handles it
        return super().render()
