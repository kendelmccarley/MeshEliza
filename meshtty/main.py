"""MeshEliza — Meshtastic TUI client with Eliza chatbot.

Entry point: python -m meshtty.main
"""

from __future__ import annotations

import argparse
import logging
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label

from meshtty.bridge.event_bridge import EventBridge
from meshtty.commands.command_handler import CommandHandler
from meshtty.config.settings import AppConfig, load_config, CONFIG_DIR
from meshtty.eliza.handler import ElizaHandler
from meshtty.message_log import MESSAGE_LOG_FILE, MessageLog
from meshtty.themes import ALL_THEMES
from meshtty.db.database import Database
from meshtty.messages.app_messages import (
    ConnectionEstablished,
    ConnectionLost,
    NodeUpdated,
    TextMessageReceived,
)
from meshtty.screens.connection import ConnectionScreen
from meshtty.screens.main_screen import MainScreen
from meshtty.transport.base import TransportManager


LOG_FILE = "/tmp/mesheliza.log"


def _setup_logging(level: str, debug: bool = False) -> None:
    effective_level = logging.DEBUG if debug else getattr(logging, level.upper(), logging.WARNING)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))

    # Apply the effective level only to our own loggers.  Setting the ROOT
    # logger to DEBUG causes the meshtastic library (and every other library)
    # to emit thousands of debug entries per second, flooding the log file and
    # consuming significant CPU for string formatting.
    app_log = logging.getLogger("meshtty")
    app_log.setLevel(effective_level)
    app_log.addHandler(handler)
    app_log.propagate = False  # don't double-log via root

    # Capture meshtastic library warnings/errors but suppress its debug spam.
    mesh_log = logging.getLogger("meshtastic")
    mesh_log.setLevel(logging.WARNING)
    if not mesh_log.handlers:
        mesh_log.addHandler(handler)
    mesh_log.propagate = False


class MeshElizaApp(App):
    """The root Textual application."""

    CSS_PATH = "../assets/mesheliza.tcss"

    TITLE = "MeshEliza"
    SUB_TITLE = "Meshtastic DM client with Eliza chatbot"

    BINDINGS = [
        Binding("f1", "show_help", "Help"),
    ]

    SCREENS = {
        "connection": ConnectionScreen,
        "main": MainScreen,
    }

    # App-level state — accessible from all screens via self.app.*
    _debug: bool = False  # set by main() before run()
    _bot: bool = False    # set by main() before run()
    _log: bool = False    # set by main() before run()
    transport: TransportManager | None = None
    config: AppConfig = None  # type: ignore[assignment]
    db: Database = None       # type: ignore[assignment]
    bridge: EventBridge = None  # type: ignore[assignment]
    command_handler: CommandHandler | None = None
    eliza_handler: ElizaHandler | None = None
    message_log: MessageLog | None = None

    def on_mount(self) -> None:
        self.config = load_config()
        _setup_logging(self.config.log_level, debug=self._debug)
        if self._debug:
            logging.getLogger(__name__).debug("Debug logging active → %s", LOG_FILE)
        self.db = Database(self.config.db_path)
        self.bridge = EventBridge(self)
        if self._bot:
            self.command_handler = CommandHandler()
        self.eliza_handler = ElizaHandler()
        if self._log:
            self.message_log = MessageLog()

        for t in ALL_THEMES:
            self.register_theme(t)
        valid = {t.name for t in ALL_THEMES}
        if self.config.theme not in valid:
            self.config.theme = "mesheliza-multicolor"
        self.theme = self.config.theme

        if self.config.auto_connect and self._has_saved_transport():
            # Try to auto-connect using saved settings, then go straight to main
            self.push_screen("connection")
        else:
            self.push_screen("connection")

    def _has_saved_transport(self) -> bool:
        cfg = self.config
        return bool(
            (cfg.default_transport == "serial" and cfg.last_serial_port)
            or (cfg.default_transport == "tcp" and cfg.last_tcp_host)
            or (cfg.default_transport == "ble" and cfg.last_ble_address)
        )

    # ------------------------------------------------------------------
    # App-level message handlers — bubble up from any screen/widget
    # ------------------------------------------------------------------

    def on_connection_established(self, event: ConnectionEstablished) -> None:
        try:
            logging.getLogger(__name__).info(
                "Connection established via %s", self.transport
            )
            # Forward to the current screen so ConnectionScreen can transition
            # early (before transport.connect() returns) and MainScreen can
            # refresh its connection-status widgets.
            if self.screen:
                self.screen.post_message(event)
        except Exception:
            pass

    def on_connection_lost(self, event: ConnectionLost) -> None:
        try:
            logging.getLogger(__name__).warning("Connection lost: %s", event.reason)
            if self.transport:
                try:
                    self.transport.disconnect()
                except Exception:
                    pass
                self.transport = None
        except Exception:
            pass

    def on_text_message_received(self, event: TextMessageReceived) -> None:
        try:
            if self.screen:
                self.screen.post_message(event)
        except Exception:
            pass

    def on_node_updated(self, event: NodeUpdated) -> None:
        try:
            if self.screen:
                self.screen.post_message(event)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_show_help(self) -> None:
        from meshtty.screens.help_modal import HelpModal
        self.push_screen(HelpModal())

    def action_disconnect(self) -> None:
        self.bridge.unsubscribe()
        if self.transport:
            try:
                self.transport.disconnect()
            except Exception:
                pass
            self.transport = None
        self.post_message(ConnectionLost("Disconnected by user"))
        # Return to connection screen
        self.switch_screen("connection")

    def on_unmount(self) -> None:
        if self.bridge:
            self.bridge.unsubscribe()
        if self.transport:
            try:
                self.transport.disconnect()
            except Exception:
                pass
        # Disconnect in-progress transport if Ctrl+Q arrived while connecting.
        # Without this the serial port stays open, blocking asyncio cleanup.
        pending = getattr(self, "_pending_transport", None)
        if pending is not None and pending is not self.transport:
            try:
                pending.disconnect()
            except Exception:
                pass
        if self.db:
            self.db.close()


def main() -> None:
    if not sys.stdin.isatty():
        print(
            "Error: MeshEliza requires an interactive terminal.\n"
            "Run in a terminal emulator or on a console TTY, not piped or redirected.",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(description="MeshEliza — Meshtastic TUI client with Eliza chatbot")
    parser.add_argument(
        "--debug",
        action="store_true",
        help=f"Enable DEBUG logging (all loggers including meshtastic) → {LOG_FILE}",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Enable DM slash-command bot (responds to /HELP, /JOKE, /INFO, etc.)",
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help=f"Log all inbound and outbound messages to {MESSAGE_LOG_FILE}",
    )
    parser.add_argument(
        "--noargs",
        action="store_true",
        help="Clear saved startup flags and launch with no flags active.",
    )
    args = parser.parse_args()

    # --noargs overrides everything: clear the saved flags file and launch clean.
    if args.noargs:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            (CONFIG_DIR / "last_flags").write_text("")
        except OSError:
            pass
        print("Saved startup flags cleared.", file=sys.stderr)
        app = MeshElizaApp()
        app.run()
        return

    # Persist flags so mesheliza.sh can replay them on the next auto-launch.
    flags = []
    if args.debug:
        flags.append("--debug")
    if args.bot:
        flags.append("--bot")
    if args.log:
        flags.append("--log")
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (CONFIG_DIR / "last_flags").write_text(" ".join(flags))
    except OSError:
        pass

    if args.debug:
        print(f"Debug logging enabled → {LOG_FILE}", file=sys.stderr)
    if args.bot:
        print("Bot mode enabled — responding to DM slash commands", file=sys.stderr)
    if args.log:
        print(f"Message logging enabled → {MESSAGE_LOG_FILE}", file=sys.stderr)

    app = MeshElizaApp()
    app._debug = args.debug
    app._bot = args.bot
    app._log = args.log
    app.run()


if __name__ == "__main__":
    main()
