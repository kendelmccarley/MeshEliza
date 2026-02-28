"""ComposeBar — message input + send button."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input


class ComposeBar(Widget):
    """Text input area with a Send button."""

    class SendRequested(Message):
        """Posted when the user submits a message."""

        def __init__(self, prefix: str, text: str) -> None:
            self.prefix = prefix
            self.text = text
            super().__init__()

    DEFAULT_CSS = """
    ComposeBar {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: solid $primary;
    }
    ComposeBar Horizontal {
        height: 3;
        align: left middle;
    }
    ComposeBar Input {
        width: 1fr;
        height: 3;
    }
    ComposeBar Button {
        width: 10;
        min-height: 3;
        margin: 0 0 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_prefix: str = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="Type a message… (Enter to send)", id="compose-input")
            yield Button("Send", id="send-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#compose-input", Input).focus()

    def set_prefix(self, prefix: str) -> None:
        """Update the compose prefix if the user hasn't started typing."""
        inp = self.query_one("#compose-input", Input)
        old_text = f"{self._current_prefix}: " if self._current_prefix else ""
        if inp.value in ("", old_text):
            self._current_prefix = prefix
            inp.value = f"{prefix}: "

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_send()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            event.stop()
            self._do_send()

    def _do_send(self) -> None:
        inp = self.query_one("#compose-input", Input)
        full = inp.value.strip()
        if not full:
            inp.focus()
            return
        if ": " in full:
            prefix, text = full.split(": ", 1)
            text = text.strip()
        else:
            prefix = self._current_prefix
            text = full
        if text:
            self.post_message(self.SendRequested(prefix=prefix, text=text))
            inp.value = f"{self._current_prefix}: "
        inp.focus()
