"""ConnectionScreen — transport picker shown at startup or on demand."""

from __future__ import annotations

import logging
import sys

log = logging.getLogger(__name__)

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Switch,
    TabbedContent,
    TabPane,
)

from textual.events import Key

from meshtty.messages.app_messages import ConnectionEstablished, ConnectionLost, NodeUpdated
from meshtty.transport.ble_transport import BLETransport
from meshtty.transport.discovery import scan_ble_devices, scan_serial_ports
from meshtty.transport.serial_transport import SerialTransport
from meshtty.transport.tcp_transport import TCPTransport


class ConnectionScreen(Screen):
    """Full-screen transport picker and connector."""

    BINDINGS = [
        Binding("ctrl+q", "app.quit", "Quit"),
    ]

    DEFAULT_CSS = """
    ConnectionScreen {
        align: center middle;
    }
    #conn-container {
        width: 80;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    #status-label {
        height: 3;
        content-align: center middle;
        color: $warning;
    }
    #error-label {
        height: 3;
        content-align: center middle;
        color: $error;
    }
    #remember-row {
        height: 3;
        align: left middle;
    }
    #remember-row Label {
        padding: 0 1;
    }
    .section-label {
        padding: 1 0 0 0;
        color: $text-muted;
    }
    LoadingIndicator {
        height: 3;
    }
    Button {
        margin: 1 0;
        min-height: 3;
    }
    DataTable {
        height: 8;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._connecting = False
        self._download_dots = 0
        self._download_done = False
        self._download_timer = None
        self._already_transitioned = False
        self._autoconnect_timer = None
        self._autoconnect_remaining = 5
        self._programmatic_tab_change = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="conn-container"):
            yield Label("MeshEliza — Connect to Radio", classes="section-label")
            with TabbedContent(id="transport-tabs"):
                with TabPane("Serial / USB", id="tab-serial"):
                    yield Label("Detected devices:", classes="section-label")
                    yield DataTable(id="serial-table", show_cursor=True)
                    yield Label("Or enter port manually:", classes="section-label")
                    yield Input(
                        placeholder=(
                            "/dev/cu.usbserial-XXXX"
                            if sys.platform == "darwin"
                            else "/dev/ttyUSB0"
                        ),
                        id="serial-input",
                    )
                with TabPane("TCP / WiFi", id="tab-tcp"):
                    yield Label("Hostname or IP address:", classes="section-label")
                    yield Input(placeholder="192.168.1.100", id="tcp-host")
                    yield Label("Port:", classes="section-label")
                    yield Input(placeholder="4403", id="tcp-port", value="4403")
                with TabPane("Bluetooth (BLE)", id="tab-ble"):
                    yield Label("Detected Meshtastic devices:", classes="section-label")
                    yield DataTable(id="ble-table", show_cursor=True)
                    yield Label("Or enter address manually:", classes="section-label")
                    yield Input(
                        placeholder="AA:BB:CC:DD:EE:FF",
                        id="ble-input",
                    )
                    yield Button("Scan for BLE Devices", id="ble-scan-btn", variant="default")
            with Horizontal(id="remember-row"):
                yield Switch(value=True, id="remember-switch")
                yield Label("Remember this device")
            yield Label("", id="status-label")
            yield Label("", id="error-label")
            yield Button("Connect", id="connect-btn", variant="primary")

    def on_mount(self) -> None:
        cfg = self.app.config

        # Pre-fill from saved config
        self.query_one("#serial-input", Input).value = cfg.last_serial_port
        self.query_one("#tcp-host", Input).value = cfg.last_tcp_host
        self.query_one("#tcp-port", Input).value = str(cfg.last_tcp_port)
        self.query_one("#ble-input", Input).value = cfg.last_ble_address

        # Set active tab to configured default transport
        tab_map = {"serial": "tab-serial", "tcp": "tab-tcp", "ble": "tab-ble"}
        tab_id = tab_map.get(cfg.default_transport, "tab-serial")
        self._programmatic_tab_change = True
        self.query_one(TabbedContent).active = tab_id

        # Set up serial table
        serial_table = self.query_one("#serial-table", DataTable)
        serial_table.add_columns("Port", "Description")
        serial_table.cursor_type = "row"

        # Set up BLE table
        ble_table = self.query_one("#ble-table", DataTable)
        ble_table.add_columns("Address", "Name")
        ble_table.cursor_type = "row"

        # Auto-scan serial ports on mount
        self._scan_serial()

        # Start auto-connect countdown if a device is remembered
        if self.app._has_saved_transport():
            self._start_autoconnect_countdown()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True, exclusive=True, name="serial-scan", exit_on_error=False)
    def _scan_serial(self) -> None:
        ports = scan_serial_ports()
        self.app.call_from_thread(self._populate_serial_table, ports)

    def _populate_serial_table(self, ports: list[dict]) -> None:
        table = self.query_one("#serial-table", DataTable)
        table.clear()
        for p in ports:
            table.add_row(p["port"], p["description"], key=p["port"])
        # Auto-populate the input when exactly one device is detected
        if len(ports) == 1:
            self.query_one("#serial-input", Input).value = ports[0]["port"]
        # Don't overwrite the status label if the auto-connect countdown is running
        if self._autoconnect_timer is None:
            if ports:
                self._set_status(f"Found {len(ports)} serial device(s).")
            else:
                self._set_status("No serial devices detected. Enter port manually.")

    @work(exclusive=True, name="ble-scan")
    async def _scan_ble(self) -> None:
        self._set_status("Scanning for BLE devices (5s)…")
        self.query_one("#ble-scan-btn", Button).disabled = True
        devices = await scan_ble_devices(timeout=5.0)
        self.query_one("#ble-scan-btn", Button).disabled = False
        table = self.query_one("#ble-table", DataTable)
        table.clear()
        for d in devices:
            table.add_row(d["address"], d["name"], key=d["address"])
        if devices:
            self._set_status(f"Found {len(devices)} BLE device(s).")
        else:
            self._set_status("No Meshtastic BLE devices found.")

    @work(thread=True, exclusive=True, name="connector")
    def _connect_worker(self, transport) -> None:
        # Capture app reference NOW — ContextVar is valid at worker-thread start
        # but transport.connect() can block 5-7 min on a busy network, by which
        # point the ContextVar may be invalid (user quit/disconnected mid-connect).
        # A direct object ref avoids the NoActiveAppError that caused failures.
        app = self.app
        app._pending_transport = transport
        self._already_transitioned = False
        log.debug("Attempting connection: %s", transport)
        try:
            transport.connect()
            log.debug("Connection succeeded: %s", transport)
            # If connection.established already fired (after _waitConnected, well
            # before waitForConfig completes) _do_transition was already called.
            # _finalize_from_worker is a no-op in that case.  On a quiet network
            # both complete quickly; _finalize_from_worker handles that fallback.
            try:
                app.call_from_thread(self._finalize_from_worker)
            except Exception:
                pass
        except Exception as exc:
            log.exception("Transport connection failed: %s", transport)
            try:
                app.call_from_thread(self._on_connect_failure, str(exc))
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Auto-connect countdown
    # ------------------------------------------------------------------

    def _start_autoconnect_countdown(self) -> None:
        self._autoconnect_remaining = 5
        self._set_status(
            f"Connecting in {self._autoconnect_remaining}s\u2026 (press any key to cancel)"
        )
        self._autoconnect_timer = self.set_interval(1.0, self._autoconnect_tick)

    def _autoconnect_tick(self) -> None:
        self._autoconnect_remaining -= 1
        if self._autoconnect_remaining <= 0:
            self._autoconnect_timer.stop()
            self._autoconnect_timer = None
            self._attempt_connect()
        else:
            self._set_status(
                f"Connecting in {self._autoconnect_remaining}s\u2026 (press any key to cancel)"
            )

    def _cancel_autoconnect(self) -> None:
        if self._autoconnect_timer is not None:
            self._autoconnect_timer.stop()
            self._autoconnect_timer = None
            self._set_status("")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_key(self, event: Key) -> None:
        self._cancel_autoconnect()

    def on_node_updated(self, event: NodeUpdated) -> None:
        """Count nodes arriving during the connection handshake and show progress."""
        if not self._connecting or self._download_done:
            return
        self._download_dots += 1
        dots = "." * self._download_dots
        self._set_status(f"Connected \u2014 downloading nodes: {dots}")
        # After 3 s with no new nodes the radio has sent everything it knows
        if self._download_timer is not None:
            self._download_timer.stop()
        self._download_timer = self.set_timer(3.0, self._on_download_complete)

    def _on_download_complete(self) -> None:
        if not self._connecting:
            return
        n = self._download_dots
        label = f"{n} node{'s' if n != 1 else ''}"
        self._set_status(
            f"Download complete ({label}) \u2014 waiting for radio confirmation\u2026"
        )
        self._download_done = True

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self._programmatic_tab_change:
            self._programmatic_tab_change = False
            return
        self._cancel_autoconnect()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._cancel_autoconnect()
        if event.button.id == "ble-scan-btn":
            self._scan_ble()
        elif event.button.id == "connect-btn":
            self._attempt_connect()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "serial-table":
            self.query_one("#serial-input", Input).value = str(event.row_key.value)
        elif event.data_table.id == "ble-table":
            self.query_one("#ble-input", Input).value = str(event.row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        if event.data_table.id == "serial-table":
            self.query_one("#serial-input", Input).value = str(event.row_key.value)
        elif event.data_table.id == "ble-table":
            self.query_one("#ble-input", Input).value = str(event.row_key.value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attempt_connect(self) -> None:
        if self._connecting:
            return
        self._connecting = True
        self._already_transitioned = False
        self._download_dots = 0
        self._download_done = False
        if self._download_timer is not None:
            self._download_timer.stop()
            self._download_timer = None
        self._clear_error()
        self._set_status("Connecting…")
        self.query_one("#connect-btn", Button).disabled = True

        active_tab = self.query_one(TabbedContent).active
        log.debug("_attempt_connect: active_tab=%r", active_tab)

        if active_tab == "tab-serial":
            port = self.query_one("#serial-input", Input).value.strip()
            if not port:
                self._set_error("Enter a serial port path.")
                self._reset_connect_btn()
                return
            transport = SerialTransport(port)

        elif active_tab == "tab-tcp":
            host = self.query_one("#tcp-host", Input).value.strip()
            port_str = self.query_one("#tcp-port", Input).value.strip()
            if not host:
                self._set_error("Enter a hostname or IP address.")
                self._reset_connect_btn()
                return
            try:
                port = int(port_str) if port_str else 4403
            except ValueError:
                self._set_error("Port must be a number.")
                self._reset_connect_btn()
                return
            transport = TCPTransport(host, port)

        elif active_tab == "tab-ble":
            addr = self.query_one("#ble-input", Input).value.strip()
            if not addr:
                self._set_error("Enter a BLE address or select a device.")
                self._reset_connect_btn()
                return
            transport = BLETransport(addr)

        else:
            log.debug("_attempt_connect: unrecognised tab %r — aborting", active_tab)
            self._set_error(f"Unknown tab: {active_tab!r}")
            self._reset_connect_btn()
            return

        try:
            self.app.bridge.subscribe()
        except Exception as exc:
            log.exception("bridge.subscribe() failed")
            self._set_error(f"Event subscription failed: {exc}")
            self._reset_connect_btn()
            return

        self._connect_worker(transport)

    def on_connection_established(self, event: ConnectionEstablished) -> None:
        """Fired by the bridge when meshtastic's _waitConnected completes.

        This arrives well before transport.connect() returns on a busy network
        (waitForConfig can add 5+ more minutes).  Transitioning here ends the
        node-download loop and lets the user get to the main screen promptly.
        """
        if not self._connecting or self._already_transitioned:
            return
        try:
            self._do_transition(event.transport)
        except Exception:
            pass

    def _finalize_from_worker(self) -> None:
        """Called on the UI thread after transport.connect() finally returns.

        No-op when the bridge already triggered _do_transition.  Handles fast/
        quiet networks where waitForConfig completes before connection.established
        is processed.
        """
        if self._already_transitioned:
            return
        transport = getattr(self.app, "_pending_transport", None)
        if transport:
            self._do_transition(transport)

    def _do_transition(self, transport) -> None:
        """Transition to the main screen.  Always called on the UI thread."""
        self._already_transitioned = True
        if self._download_timer is not None:
            self._download_timer.stop()
            self._download_timer = None
        self._connecting = False
        self.app.transport = transport
        cfg = self.app.config
        try:
            remember = self.query_one("#remember-switch", Switch).value
            if remember:
                if transport.transport_type == "serial":
                    cfg.last_serial_port = transport._dev_path
                    cfg.default_transport = "serial"
                elif transport.transport_type == "tcp":
                    cfg.last_tcp_host = transport._hostname
                    cfg.last_tcp_port = transport._port
                    cfg.default_transport = "tcp"
                elif transport.transport_type == "ble":
                    cfg.last_ble_address = transport._address
                    cfg.default_transport = "ble"
                from meshtty.config.settings import save_config
                save_config(cfg)
        except Exception:
            pass
        n = self._download_dots
        node_str = f"{n} node{'s' if n != 1 else ''}" if n else "nodes"
        self._set_status(f"Connected! ({node_str} loaded)")
        self.app.post_message(ConnectionEstablished(transport))
        self.app.push_screen("main")

    def _on_connect_failure(self, reason: str) -> None:
        if self._download_timer is not None:
            self._download_timer.stop()
            self._download_timer = None
        self._download_dots = 0
        self._set_error(f"Connection failed: {reason}")
        self.app.bridge.unsubscribe()
        self._connecting = False
        self._reset_connect_btn()
        self.app.post_message(ConnectionLost(reason))

    def _reset_connect_btn(self) -> None:
        self.query_one("#connect-btn", Button).disabled = False
        self._connecting = False

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-label", Label).update(msg)

    def _set_error(self, msg: str) -> None:
        self.query_one("#error-label", Label).update(msg)

    def _clear_error(self) -> None:
        self.query_one("#error-label", Label).update("")
