"""ConnectionStatusBar — docked at the top of MainScreen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label


class ConnectionStatusBar(Widget):
    """Shows connection state, channel, node count, and local battery."""

    DEFAULT_CSS = """
    ConnectionStatusBar {
        dock: top;
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
    }
    ConnectionStatusBar Horizontal {
        height: 3;
        align: left middle;
    }
    #conn-state {
        width: auto;
        padding: 0 2;
        min-width: 24;
    }
    #channel-label {
        width: auto;
        padding: 0 2;
        color: $text-muted;
    }
    #node-count {
        width: auto;
        padding: 0 2;
        color: $text-muted;
    }
    #battery-label {
        width: auto;
        padding: 0 2;
        color: $text-muted;
    }
    #disconnect-btn {
        dock: right;
        margin: 0 1;
        min-height: 3;
        min-width: 14;
    }
    """

    connection_state: reactive[str] = reactive("disconnected")
    channel_name: reactive[str] = reactive("—")
    node_count: reactive[int] = reactive(0)
    battery_level: reactive[int | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("● Disconnected", id="conn-state")
            yield Label("Ch: —", id="channel-label")
            yield Label("Nodes: 0", id="node-count")
            yield Label("", id="battery-label")
            yield Button("Disconnect", id="disconnect-btn", variant="error")

    # ------------------------------------------------------------------
    # Watchers — called automatically when reactives change
    # ------------------------------------------------------------------

    def watch_connection_state(self, state: str) -> None:
        label = self.query_one("#conn-state", Label)
        btn = self.query_one("#disconnect-btn", Button)
        if state == "connected":
            transport = getattr(self.app, "transport", None)
            transport_str = f" via {transport}" if transport else ""
            label.update(f"● Connected{transport_str}")
            label.add_class("connected")
            label.remove_class("disconnected")
            btn.disabled = False
        else:
            label.update("● Disconnected")
            label.remove_class("connected")
            label.add_class("disconnected")
            btn.disabled = True

    def watch_channel_name(self, name: str) -> None:
        self.query_one("#channel-label", Label).update(f"Ch: {name}")

    def watch_node_count(self, count: int) -> None:
        self.query_one("#node-count", Label).update(f"Nodes: {count}")

    def watch_battery_level(self, level: int | None) -> None:
        label = self.query_one("#battery-label", Label)
        if level is None:
            label.update("")
        else:
            label.update(f"Bat: {level}%")

    # ------------------------------------------------------------------
    # Button handler bubbles up to MainScreen
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "disconnect-btn":
            event.stop()
            self.app.action_disconnect()
