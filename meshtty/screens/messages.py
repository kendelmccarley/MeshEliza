"""MessagesView — unified message history + compose bar.

Eliza chatbot sessions are managed automatically for direct messages: when a
node sends a DM that starts with "eliza" (case-insensitive) a session opens
and subsequent DMs from that node are handled by the bot until the session
ends.  Channel broadcasts are displayed normally and are not routed to Eliza.
"""

from __future__ import annotations

import time

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.widget import Widget

from meshtty.messages.app_messages import TextMessageReceived
from meshtty.widgets.compose_bar import ComposeBar
from meshtty.widgets.message_view import MessageView


class MessagesView(Widget):
    """Full messages panel: unified message history + compose."""

    BINDINGS = [
        Binding("ctrl+g", "send_bell", "Send BEL"),
    ]

    DEFAULT_CSS = """
    MessagesView {
        height: 1fr;
        layout: vertical;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._last_prefix: str = ""

    def compose(self) -> ComposeResult:
        yield MessageView(id="message-view")
        yield ComposeBar()

    def on_mount(self) -> None:
        self._load_history()
        transport = self.app.transport
        channels = transport.get_channels() if transport else []
        first_name = channels[0][1] if channels else "Primary"
        self._last_prefix = first_name
        try:
            self.query_one(ComposeBar).set_prefix(first_name)
        except Exception:
            pass

    def on_show(self) -> None:
        """Re-focus compose input whenever the Messages tab becomes active."""
        try:
            self.query_one("#compose-input").focus()
        except Exception:
            pass

    def on_key(self, event: Key) -> None:
        """Arrow keys scroll the message view regardless of focus."""
        try:
            view = self.query_one("#message-view", MessageView)
            if event.key == "up":
                view.scroll_up(animate=False)
                event.stop()
            elif event.key == "down":
                view.scroll_down(animate=False)
                event.stop()
            elif event.key == "pageup":
                view.scroll_page_up(animate=False)
                event.stop()
            elif event.key == "pagedown":
                view.scroll_page_down(animate=False)
                event.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Prefix resolution helpers
    # ------------------------------------------------------------------

    def _resolve_incoming_prefix(self, event: TextMessageReceived) -> str:
        """Determine a human-readable prefix for an incoming message."""
        transport = self.app.transport
        if event.to_id == "^all":
            if transport:
                for idx, name in transport.get_channels():
                    if idx == event.channel:
                        return name
            return f"Ch {event.channel}"
        else:
            if transport:
                nodes = transport.get_nodes()
                node = nodes.get(event.from_id, {})
                user = node.get("user", {}) if node else {}
                short = user.get("shortName", "").strip()
                if short:
                    return short
            return event.from_id

    def _resolve_send_destination(self, prefix: str) -> tuple[int | None, str]:
        """Return (channel_idx, dest_id) from a prefix string."""
        transport = self.app.transport
        if transport:
            for idx, name in transport.get_channels():
                if name.lower() == prefix.lower():
                    return (idx, "^all")
            for node_id, node in transport.get_nodes().items():
                user = node.get("user", {}) if node else {}
                short = user.get("shortName", "").strip()
                if short and short.lower() == prefix.lower():
                    return (None, node_id)
        return (0, "^all")

    def _log(self, direction: str, prefix: str, text: str) -> None:
        ml = getattr(self.app, "message_log", None)
        if ml is not None:
            ml.log(direction, prefix, text)

    # ------------------------------------------------------------------
    # Incoming message handler
    # ------------------------------------------------------------------

    def on_text_message_received(self, event: TextMessageReceived) -> None:
        try:
            event.stop()
            text = event.text or ""
            if not text:
                return

            is_dm = event.to_id != "^all"
            view = self.query_one("#message-view", MessageView)
            prefix = self._resolve_incoming_prefix(event)
            transport = self.app.transport

            # ----------------------------------------------------------------
            # Slash-command handling: only for DMs starting with "/"
            # (runs before Eliza so /commands still work when --bot is set)
            # ----------------------------------------------------------------
            if is_dm and text.strip().startswith("/"):
                handler = getattr(self.app, "command_handler", None)
                if handler is not None:
                    reply = handler.handle(text.strip())
                    if reply is None:
                        # Unknown command — silently drop
                        return
                    # Valid command: display the incoming command message
                    view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
                    self._write_message(
                        event.from_id, event.to_id, event.channel,
                        text, event.rx_time, False, event.packet_id, prefix,
                    )
                    self._log("RX", prefix, text)
                    # Send reply back to sender and display it
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(reply, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    now = int(time.time())
                    view.append_message(prefix=prefix, text=reply, rx_time=now, is_mine=True)
                    self._write_message(
                        "me", event.from_id, 0,
                        reply, now, True, None, prefix,
                    )
                    self._log("TX", prefix, reply)
                    return

            # ----------------------------------------------------------------
            # Eliza session handling (DMs only, automatic on first message)
            # ----------------------------------------------------------------
            eliza = getattr(self.app, "eliza_handler", None)
            if eliza is not None and is_dm:
                # Display the incoming message first
                view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
                self._write_message(
                    event.from_id, event.to_id, event.channel,
                    text, event.rx_time, False, event.packet_id, prefix,
                )
                self._log("RX", prefix, text)

                # Start a new session if none exists or the previous one timed out
                greeting = eliza.ensure_session(event.from_id)
                if greeting:
                    # New session: send a brief introduction first, then the
                    # normal Eliza greeting, then the response to the first message.
                    intro = (
                        "My name is Eliza, an early natural language processing "
                        "computer program first created in 1966."
                    )
                    now = int(time.time())
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(intro, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    view.append_message(prefix=prefix, text=intro, rx_time=now, is_mine=True)
                    self._write_message("me", event.from_id, 0, intro, now, True, None, prefix)
                    self._log("TX", prefix, intro)

                    now = int(time.time())
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(greeting, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    view.append_message(prefix=prefix, text=greeting, rx_time=now, is_mine=True)
                    self._write_message("me", event.from_id, 0, greeting, now, True, None, prefix)
                    self._log("TX", prefix, greeting)

                # Feed the message into the session
                reply = eliza.respond(event.from_id, text)
                if reply:
                    now = int(time.time())
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(reply, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    view.append_message(prefix=prefix, text=reply, rx_time=now, is_mine=True)
                    self._write_message("me", event.from_id, 0, reply, now, True, None, prefix)
                    self._log("TX", prefix, reply)

                try:
                    self.query_one(ComposeBar).set_prefix(prefix)
                except Exception:
                    pass
                self._last_prefix = prefix
                return

            # ----------------------------------------------------------------
            # Normal message handling (DM or channel broadcast)
            # ----------------------------------------------------------------
            prefix = self._resolve_incoming_prefix(event)
            self._last_prefix = prefix
            view.append_message(prefix=prefix, text=event.text, rx_time=event.rx_time)
            try:
                self.query_one(ComposeBar).set_prefix(prefix)
            except Exception:
                pass
            self._write_message(
                event.from_id,
                event.to_id,
                event.channel,
                event.text,
                event.rx_time,
                False,
                event.packet_id,
                prefix,
            )
            self._log("RX", prefix, event.text)
        except Exception:
            pass

    def on_compose_bar_send_requested(self, event: ComposeBar.SendRequested) -> None:
        try:
            event.stop()
            transport = self.app.transport
            if transport is None or not transport.is_connected:
                return
            channel_idx, dest_id = self._resolve_send_destination(event.prefix)
            try:
                if dest_id == "^all":
                    transport.send_text(event.text, channel=channel_idx or 0)
                else:
                    transport.send_text(event.text, destination=dest_id, channel=0)
            except Exception:
                return
            now = int(time.time())
            view = self.query_one("#message-view", MessageView)
            view.append_message(prefix=event.prefix, text=event.text, rx_time=now, is_mine=True)
            self._write_message(
                "me",
                dest_id,
                channel_idx if channel_idx is not None else 0,
                event.text,
                now,
                True,
                None,
                event.prefix,
            )
            self._log("TX", event.prefix, event.text)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_send_bell(self) -> None:
        """Send the ASCII BEL character (\\x07) to the current destination."""
        try:
            transport = self.app.transport
            if transport is None or not transport.is_connected:
                return
            if not self._last_prefix:
                return
            channel_idx, dest_id = self._resolve_send_destination(self._last_prefix)
            try:
                if dest_id == "^all":
                    transport.send_text("\x07", channel=channel_idx or 0)
                else:
                    transport.send_text("\x07", destination=dest_id, channel=0)
            except Exception:
                return
            now = int(time.time())
            view = self.query_one("#message-view", MessageView)
            view.append_message(prefix=self._last_prefix, text="[BEL]", rx_time=now, is_mine=True)
            self._write_message(
                "me",
                dest_id,
                channel_idx if channel_idx is not None else 0,
                "\x07",
                now,
                True,
                None,
                self._last_prefix,
            )
            self._log("TX", self._last_prefix, "[BEL]")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True, name="load-history", exit_on_error=False)
    def _load_history(self) -> None:
        rows = self.app.db.get_messages(limit=200)
        self.app.call_from_thread(self._apply_history, rows)

    def _apply_history(self, rows: list) -> None:
        view = self.query_one("#message-view", MessageView)
        view.load_messages(rows)

    @work(thread=True, name="write-message", exit_on_error=False)
    def _write_message(
        self,
        from_id: str,
        to_id: str,
        channel: int,
        text: str,
        rx_time: int,
        is_mine: bool,
        packet_id: str | None = None,
        display_prefix: str = "",
    ) -> None:
        self.app.db.insert_message(
            from_id, to_id, channel, text, rx_time, is_mine, packet_id, display_prefix
        )
