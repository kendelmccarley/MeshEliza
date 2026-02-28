"""MessagesView — unified message history + compose bar.

Only direct messages are displayed; channel broadcasts are silently ignored.
Eliza chatbot sessions are managed automatically: when a node sends a DM
that starts with "eliza" (case-insensitive) a session opens and subsequent
DMs from that node are handled by the bot until the session ends.
"""

from __future__ import annotations

import time

from textual import work
from textual.app import ComposeResult
from textual.events import Key
from textual.widget import Widget

from meshtty.messages.app_messages import TextMessageReceived
from meshtty.widgets.compose_bar import ComposeBar
from meshtty.widgets.message_view import MessageView


class MessagesView(Widget):
    """Full messages panel: unified message history + compose."""

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
    # Helpers (DM-only; no channel resolution)
    # ------------------------------------------------------------------

    def _node_short_name(self, node_id: str) -> str:
        """Return the short name for *node_id*, falling back to the ID."""
        transport = self.app.transport
        if transport:
            node = transport.get_nodes().get(node_id, {})
            short = (node.get("user", {}) or {}).get("shortName", "").strip()
            if short:
                return short
        return node_id

    def _resolve_send_destination(self, prefix: str) -> str | None:
        """Return the node_id whose short name matches *prefix*, or None."""
        transport = self.app.transport
        if not transport:
            return None
        for node_id, node in transport.get_nodes().items():
            short = (node.get("user", {}) or {}).get("shortName", "").strip()
            if short and short.lower() == prefix.lower():
                return node_id
        return None

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

            # Only handle direct messages; ignore channel broadcasts
            if event.to_id == "^all":
                return

            view = self.query_one("#message-view", MessageView)
            prefix = self._node_short_name(event.from_id)
            transport = self.app.transport

            # ----------------------------------------------------------------
            # Eliza session handling (always-on)
            # ----------------------------------------------------------------
            eliza = getattr(self.app, "eliza_handler", None)
            if eliza is not None:

                if eliza.is_active(event.from_id):
                    # Feed text into the existing session
                    view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
                    self._write_message(
                        event.from_id, event.to_id, event.channel,
                        text, event.rx_time, False, event.packet_id, prefix,
                    )
                    self._log("RX", prefix, text)

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
                    return

                elif eliza.is_trigger(text):
                    # Start a new Eliza session for this node
                    view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
                    self._write_message(
                        event.from_id, event.to_id, event.channel,
                        text, event.rx_time, False, event.packet_id, prefix,
                    )
                    self._log("RX", prefix, text)

                    greeting = eliza.start(event.from_id)
                    now = int(time.time())
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(greeting, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    view.append_message(prefix=prefix, text=greeting, rx_time=now, is_mine=True)
                    self._write_message("me", event.from_id, 0, greeting, now, True, None, prefix)
                    self._log("TX", prefix, greeting)

                    # Text after "eliza" becomes the first input to the session
                    after = eliza.first_input(text)
                    if after:
                        reply = eliza.respond(event.from_id, after)
                        if reply:
                            now = int(time.time())
                            if transport and transport.is_connected:
                                try:
                                    transport.send_text(reply, destination=event.from_id, channel=0)
                                except Exception:
                                    pass
                            view.append_message(
                                prefix=prefix, text=reply, rx_time=now, is_mine=True,
                            )
                            self._write_message(
                                "me", event.from_id, 0, reply, now, True, None, prefix,
                            )
                            self._log("TX", prefix, reply)

                    try:
                        self.query_one(ComposeBar).set_prefix(prefix)
                    except Exception:
                        pass
                    self._last_prefix = prefix
                    return

            # ----------------------------------------------------------------
            # Slash-command bot handling (--bot flag)
            # ----------------------------------------------------------------
            if text.strip().startswith("/"):
                handler = getattr(self.app, "command_handler", None)
                if handler is not None:
                    reply = handler.handle(text.strip())
                    if reply is None:
                        return  # Unknown command — silently drop
                    view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
                    self._write_message(
                        event.from_id, event.to_id, event.channel,
                        text, event.rx_time, False, event.packet_id, prefix,
                    )
                    self._log("RX", prefix, text)
                    if transport and transport.is_connected:
                        try:
                            transport.send_text(reply, destination=event.from_id, channel=0)
                        except Exception:
                            pass
                    now = int(time.time())
                    view.append_message(prefix=prefix, text=reply, rx_time=now, is_mine=True)
                    self._write_message("me", event.from_id, 0, reply, now, True, None, prefix)
                    self._log("TX", prefix, reply)
                    return

            # ----------------------------------------------------------------
            # Normal DM display
            # ----------------------------------------------------------------
            self._last_prefix = prefix
            view.append_message(prefix=prefix, text=text, rx_time=event.rx_time)
            try:
                self.query_one(ComposeBar).set_prefix(prefix)
            except Exception:
                pass
            self._write_message(
                event.from_id, event.to_id, event.channel,
                text, event.rx_time, False, event.packet_id, prefix,
            )
            self._log("RX", prefix, text)
        except Exception:
            pass

    def on_compose_bar_send_requested(self, event: ComposeBar.SendRequested) -> None:
        try:
            event.stop()
            transport = self.app.transport
            if transport is None or not transport.is_connected:
                return
            dest_id = self._resolve_send_destination(event.prefix)
            if dest_id is None:
                # Prefix doesn't match any known node — don't send
                return
            try:
                transport.send_text(event.text, destination=dest_id, channel=0)
            except Exception:
                return
            now = int(time.time())
            view = self.query_one("#message-view", MessageView)
            view.append_message(prefix=event.prefix, text=event.text, rx_time=now, is_mine=True)
            self._write_message("me", dest_id, 0, event.text, now, True, None, event.prefix)
            self._log("TX", event.prefix, event.text)
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
