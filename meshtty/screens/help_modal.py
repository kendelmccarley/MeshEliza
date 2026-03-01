"""HelpModal — keyboard shortcut reference."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

_SHORTCUTS = """\
 Ctrl+T    Messages tab
 Ctrl+N    Nodes tab
 Ctrl+L    Channels tab
 Ctrl+S    Settings tab

 Ctrl+R    Refresh node list
 Ctrl+G    Send BEL (ASCII 0x07) to current destination
 Ctrl+D    Disconnect
 Ctrl+Q    Quit
 F1        This help screen

 Eliza bot:
   Auto-starts on first DM from any node
   bye/quit    End the session (restarts on next DM)

 Node detail:
   Escape  Close
   Q       Close\
"""


class HelpModal(ModalScreen):
    """Full-screen overlay listing all keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("f1", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }
    #help-container {
        width: 46;
        height: auto;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        color: $primary;
        text-style: bold;
        padding: 0 0 1 0;
    }
    #help-content {
        padding: 0 0 1 0;
    }
    #help-close-btn {
        min-height: 3;
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("Keyboard Shortcuts", id="help-title")
            yield Static(_SHORTCUTS, id="help-content", markup=False)
            yield Button("Close  [Esc]", id="help-close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close-btn":
            self.dismiss()
