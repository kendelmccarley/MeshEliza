"""Custom Textual Message subclasses for inter-component communication.

All messages originate in the EventBridge and are dispatched by Textual to
registered handlers.

CRITICAL — bubble=False MUST be set as a class-declaration keyword argument,
NOT as a plain class-body attribute.  Textual's Message.__init_subclass__
accepts 'bubble' as a keyword and ALWAYS sets cls.bubble from it, using
True as the default.  A class-body "bubble = False" is created first, then
__init_subclass__ overwrites it back to True.  Only the keyword syntax:

    class Foo(Message, bubble=False):

correctly passes bubble=False into __init_subclass__ so it stays False.

Without this, every NodeUpdated posted to the App bounces App → Screen →
App → Screen → … in an infinite loop, pegging the CPU to 100% and filling
the asyncio queue with millions of messages (7+ GB of RAM in minutes).
"""

from textual.message import Message


class TextMessageReceived(Message, bubble=False):
    """A text message arrived from the mesh network."""

    def __init__(self, packet: dict) -> None:
        self.packet = packet
        decoded = packet.get("decoded", {})
        self.from_id: str = packet.get("fromId", "!unknown")
        self.to_id: str = packet.get("toId", "^all")
        self.channel: int = packet.get("channel", 0)
        self.text: str = decoded.get("text", "")
        self.rx_time: int = packet.get("rxTime", 0)
        self.packet_id: str | None = str(packet.get("id")) if packet.get("id") else None
        super().__init__()


class NodeUpdated(Message, bubble=False):
    """A node's information has changed (position, telemetry, first seen, etc.)."""

    def __init__(self, node_id: str, node_info: dict) -> None:
        self.node_id = node_id
        self.node_info = node_info
        super().__init__()


class ConnectionEstablished(Message, bubble=False):
    """Radio connection was successfully established."""

    def __init__(self, transport) -> None:
        self.transport = transport
        super().__init__()


class ConnectionLost(Message, bubble=False):
    """Radio connection was lost or failed to connect."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__()


class AckReceived(Message, bubble=False):
    """ACK or NAK received for a previously sent packet.

    status values:
      "*A"  — acknowledged directly by the destination node
      "*O"  — acknowledged by a different node (overheard / relayed)
      "*-"  — no response before timeout
    """

    def __init__(self, packet_id: int, status: str) -> None:
        self.packet_id = packet_id
        self.status = status
        super().__init__()


class TransportChanged(Message, bubble=False):
    """User switched to a different transport type."""

    def __init__(self, transport_type: str) -> None:
        self.transport_type = transport_type
        super().__init__()
