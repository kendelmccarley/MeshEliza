"""MessageView — scrollable message history container."""

from __future__ import annotations

import textwrap
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label

_WRAP_WIDTH = 80


def _format_message(prefix: str, text: str, rx_time: int, is_mine: bool = False) -> str:
    try:
        dt = datetime.fromtimestamp(rx_time).strftime("%H:%M")
    except (OSError, ValueError, OverflowError):
        dt = "--:--"
    indent = "  " if is_mine else ""
    header = f"{indent}{dt} {prefix}: "
    continuation = " " * len(header)
    full = header + text
    return textwrap.fill(
        full,
        width=_WRAP_WIDTH,
        subsequent_indent=continuation,
        break_long_words=True,
        break_on_hyphens=False,
    )


class MessageView(Widget):
    """Scrollable list of chat messages."""

    DEFAULT_CSS = """
    MessageView {
        height: 1fr;
        overflow-y: auto;
        padding: 0;
        background: $surface;
    }
    MessageView Label {
        height: auto;
        padding: 0;
    }
    MessageView .mine {
        color: $accent;
    }
    MessageView .theirs {
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        return
        yield  # make it a generator

    def append_message(
        self,
        prefix: str,
        text: str,
        rx_time: int,
        is_mine: bool = False,
    ) -> Label:
        """Append a message and return the Label so callers can update it later."""
        formatted = _format_message(prefix, text, rx_time, is_mine)
        css_class = "mine" if is_mine else "theirs"
        label = Label(formatted, classes=css_class, markup=False)
        self.mount(label)
        self.scroll_end(animate=False)
        return label

    def update_ack_status(self, label: Label, status: str) -> None:
        """Append an ACK status marker to an existing message label."""
        label.update(str(label.renderable) + " " + status)

    def load_messages(self, rows: list) -> None:
        """Bulk-load historical messages (called from worker result)."""
        for row in rows:
            display_prefix = (row["display_prefix"] or "") if "display_prefix" in row.keys() else ""
            prefix = display_prefix if display_prefix else row["from_id"]
            self.append_message(
                prefix=prefix,
                text=row["text"],
                rx_time=row["rx_time"],
                is_mine=bool(row["is_mine"]),
            )
