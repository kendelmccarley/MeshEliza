"""SettingsScreen — configure transport defaults and app preferences."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, Switch

from meshtty.config.settings import save_config
from meshtty.themes import ALL_THEMES


_TRANSPORT_OPTIONS = [
    ("Serial / USB", "serial"),
    ("TCP / WiFi", "tcp"),
    ("Bluetooth (BLE)", "ble"),
]

_THEME_OPTIONS = [
    ("Multicolor",     "mesheliza-multicolor"),
    ("Green Phosphor", "mesheliza-phosphor"),
    ("Black & White",  "mesheliza-bw"),
]


class SettingsView(Widget):
    """Settings panel rendered inside the MainScreen Settings tab."""

    DEFAULT_CSS = """
    SettingsView {
        height: 1fr;
        overflow-y: auto;
        padding: 1 2;
    }
    .section-header {
        color: $primary;
        padding: 1 0 0 0;
        text-style: bold;
    }
    .row {
        height: 4;
        layout: horizontal;
        align: left middle;
    }
    .row Label {
        width: 28;
    }
    .row Input {
        width: 1fr;
    }
    .row Select {
        width: 1fr;
    }
    #save-btn {
        margin-top: 2;
        min-height: 3;
        width: 20;
    }
    #save-status {
        padding: 1 0;
        color: $success;
    }
    #disconnect-btn {
        margin-top: 1;
        min-height: 3;
        width: 20;
    }
    """

    def compose(self) -> ComposeResult:
        cfg = self.app.config

        yield Label("Connection", classes="section-header")

        with Vertical(classes="row"):
            yield Label("Disconnected", id="conn-status-label")

        yield Button("Disconnect", id="disconnect-btn", variant="error", disabled=True)

        yield Label("Transport", classes="section-header")

        with Vertical(classes="row"):
            yield Label("Default transport")
            yield Select(
                [(label, val) for label, val in _TRANSPORT_OPTIONS],
                value=cfg.default_transport,
                id="sel-transport",
            )

        with Vertical(classes="row"):
            yield Label("Serial port")
            yield Input(value=cfg.last_serial_port, placeholder="/dev/ttyUSB0", id="inp-serial")

        with Vertical(classes="row"):
            yield Label("TCP hostname")
            yield Input(value=cfg.last_tcp_host, placeholder="192.168.1.100", id="inp-tcp-host")

        with Vertical(classes="row"):
            yield Label("TCP port")
            yield Input(value=str(cfg.last_tcp_port), placeholder="4403", id="inp-tcp-port")

        with Vertical(classes="row"):
            yield Label("BLE address")
            yield Input(value=cfg.last_ble_address, placeholder="AA:BB:CC:DD:EE:FF", id="inp-ble")

        with Vertical(classes="row"):
            yield Label("Auto-connect on launch")
            yield Switch(value=cfg.auto_connect, id="sw-autoconnect")

        yield Label("Messaging", classes="section-header")

        with Vertical(classes="row"):
            yield Label("Default channel")
            yield Input(value=str(cfg.default_channel), placeholder="0", id="inp-channel")

        yield Label("Display", classes="section-header")

        with Vertical(classes="row"):
            yield Label("Show short node names")
            yield Switch(value=cfg.node_short_name_display, id="sw-shortnames")

        with Vertical(classes="row"):
            yield Label("Theme")
            yield Select(
                [(label, val) for label, val in _THEME_OPTIONS],
                value=cfg.theme,
                id="sel-theme",
            )

        yield Button("Save", id="save-btn", variant="primary")
        yield Label("", id="save-status")

    def on_mount(self) -> None:
        self._refresh_connection_status()

    def on_show(self) -> None:
        self._refresh_connection_status()

    def _refresh_connection_status(self) -> None:
        try:
            transport = self.app.transport
            label = self.query_one("#conn-status-label", Label)
            btn = self.query_one("#disconnect-btn", Button)
            if transport and transport.is_connected:
                nodes = len(transport.get_nodes())
                my_node = transport.get_my_node()
                bat = (my_node.get("deviceMetrics", {}) or {}).get("batteryLevel") if my_node else None
                bat_str = f" | Bat: {bat}%" if bat is not None else ""
                label.update(f"Connected via {transport} | {nodes} nodes{bat_str}")
                btn.disabled = False
            else:
                label.update("Disconnected")
                btn.disabled = True
        except Exception:
            pass

    def on_connection_established(self, event) -> None:
        try:
            self._refresh_connection_status()
        except Exception:
            pass

    def on_connection_lost(self, event) -> None:
        try:
            self._refresh_connection_status()
        except Exception:
            pass

    def on_node_updated(self, event) -> None:
        try:
            self._refresh_connection_status()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "disconnect-btn":
            event.stop()
            self.app.action_disconnect()
        elif event.button.id == "save-btn":
            event.stop()
            self._save()

    def _save(self) -> None:
        cfg = self.app.config

        cfg.default_transport = self.query_one("#sel-transport", Select).value or "serial"
        cfg.last_serial_port = self.query_one("#inp-serial", Input).value.strip()
        cfg.last_tcp_host = self.query_one("#inp-tcp-host", Input).value.strip()
        try:
            cfg.last_tcp_port = int(self.query_one("#inp-tcp-port", Input).value) or 4403
        except ValueError:
            cfg.last_tcp_port = 4403
        cfg.last_ble_address = self.query_one("#inp-ble", Input).value.strip()
        cfg.auto_connect = self.query_one("#sw-autoconnect", Switch).value
        cfg.node_short_name_display = self.query_one("#sw-shortnames", Switch).value
        cfg.theme = self.query_one("#sel-theme", Select).value or "mesheliza-multicolor"
        try:
            cfg.default_channel = int(self.query_one("#inp-channel", Input).value)
        except ValueError:
            cfg.default_channel = 0

        save_config(cfg)
        self.app.theme = cfg.theme
        self.query_one("#save-status", Label).update("Settings saved.")
