"""PyPubSub → Textual thread-safe event bridge.

meshtastic-python fires PyPubSub callbacks on its own internal thread.
Textual's event loop runs on the main asyncio thread.

post_message() is already thread-safe in Textual 8: when called from a
non-asyncio thread it uses call_soon_threadsafe() internally, which is
non-blocking and returns False gracefully if the app is closing.

Never use call_from_thread() here — it blocks the meshtastic thread until
the main loop processes the coroutine, causing a deadlock if the event loop
is shutting down.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pubsub import pub

from meshtty.messages.app_messages import (
    ConnectionEstablished,
    ConnectionLost,
    NodeUpdated,
    TextMessageReceived,
)

if TYPE_CHECKING:
    from textual.app import App

log = logging.getLogger(__name__)


def _extract_node_info(node: dict) -> dict:
    """Flatten a meshtastic node dict into our canonical node_info shape."""
    user = node.get("user", {})
    pos = node.get("position", {})
    metrics = node.get("deviceMetrics", {})
    return {
        "short_name": user.get("shortName", ""),
        "long_name": user.get("longName", ""),
        "hw_model": user.get("hwModel", ""),
        "last_snr": node.get("snr"),
        "last_lat": pos.get("latitude"),
        "last_lon": pos.get("longitude"),
        "last_alt": pos.get("altitude"),
        "battery": metrics.get("batteryLevel"),
        "last_heard": node.get("lastHeard"),
    }


class EventBridge:
    """Subscribes to meshtastic PyPubSub topics and bridges into Textual."""

    def __init__(self, app: "App") -> None:
        self._app = app
        self._subscribed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self) -> None:
        if self._subscribed:
            return
        pub.subscribe(self._on_text, "meshtastic.receive.text")
        pub.subscribe(self._on_position, "meshtastic.receive.position")
        pub.subscribe(self._on_telemetry, "meshtastic.receive.telemetry")
        pub.subscribe(self._on_node_updated, "meshtastic.node.updated")
        pub.subscribe(self._on_connected, "meshtastic.connection.established")
        pub.subscribe(self._on_lost, "meshtastic.connection.lost")
        self._subscribed = True
        log.debug("EventBridge subscribed")

    def unsubscribe(self) -> None:
        if not self._subscribed:
            return
        pairs = [
            ("meshtastic.receive.text", self._on_text),
            ("meshtastic.receive.position", self._on_position),
            ("meshtastic.receive.telemetry", self._on_telemetry),
            ("meshtastic.node.updated", self._on_node_updated),
            ("meshtastic.connection.established", self._on_connected),
            ("meshtastic.connection.lost", self._on_lost),
        ]
        for topic, handler in pairs:
            try:
                pub.unsubscribe(handler, topic)
            except Exception:
                pass
        self._subscribed = False
        log.debug("EventBridge unsubscribed")

    # ------------------------------------------------------------------
    # PyPubSub callbacks (run on meshtastic's internal thread)
    #
    # Use post_message() directly — it is thread-safe in Textual 8 and
    # non-blocking.  Never use call_from_thread() here.
    # ------------------------------------------------------------------

    def _on_text(self, packet: dict, interface) -> None:  # noqa: ANN001
        try:
            self._app.post_message(TextMessageReceived(packet))
        except Exception as exc:
            log.error("_on_text bridge error: %s", exc)

    def _on_position(self, packet: dict, interface) -> None:  # noqa: ANN001
        try:
            node_id = packet.get("fromId", "")
            if node_id and interface and interface.nodes:
                node = interface.nodes.get(node_id, {})
                info = _extract_node_info(node)
                self._app.post_message(NodeUpdated(node_id, info))
        except Exception as exc:
            log.error("_on_position bridge error: %s", exc)

    def _on_telemetry(self, packet: dict, interface) -> None:  # noqa: ANN001
        try:
            node_id = packet.get("fromId", "")
            if node_id and interface and interface.nodes:
                node = interface.nodes.get(node_id, {})
                info = _extract_node_info(node)
                self._app.post_message(NodeUpdated(node_id, info))
        except Exception as exc:
            log.error("_on_telemetry bridge error: %s", exc)

    def _on_node_updated(self, node: dict, interface) -> None:  # noqa: ANN001
        try:
            node_id = node.get("id") or node.get("num", "")
            if node_id:
                info = _extract_node_info(node)
                self._app.post_message(NodeUpdated(str(node_id), info))
        except Exception as exc:
            log.error("_on_node_updated bridge error: %s", exc)

    def _on_connected(self, interface, topic=pub.AUTO_TOPIC) -> None:  # noqa: ANN001
        # _pending_transport is stored on the app by _connect_worker before the
        # blocking transport.connect() call.  Posting ConnectionEstablished here
        # (when _waitConnected completes) lets the connection screen transition
        # immediately without waiting for waitForConfig, which can take 5+ min
        # on a busy 100-node network.
        try:
            log.debug("meshtastic.connection.established received")
            pending = getattr(self._app, "_pending_transport", None)
            if pending is not None:
                self._app.post_message(ConnectionEstablished(pending))
        except Exception as exc:
            log.error("_on_connected bridge error: %s", exc)

    def _on_lost(self, interface, topic=pub.AUTO_TOPIC) -> None:  # noqa: ANN001
        try:
            self._app.post_message(ConnectionLost("Connection lost"))
        except Exception as exc:
            log.error("_on_lost bridge error: %s", exc)
