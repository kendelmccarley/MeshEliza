from abc import ABC, abstractmethod


class TransportManager(ABC):
    def __init__(self) -> None:
        self._interface = None

    @abstractmethod
    def connect(self) -> None:
        """Blocking connect. Call from a worker thread, not the event loop."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the radio connection and release resources."""

    @property
    def is_connected(self) -> bool:
        return self._interface is not None

    def send_text(
        self,
        text: str,
        destination: str = "^all",
        channel: int = 0,
    ) -> None:
        if self._interface is None:
            raise RuntimeError("Not connected")
        self._interface.sendText(text, destinationId=destination, channelIndex=channel)

    def get_nodes(self) -> dict:
        if self._interface is None:
            return {}
        return self._interface.nodes or {}

    def get_my_node(self) -> dict:
        if self._interface is None:
            return {}
        return self._interface.getMyNodeInfo() or {}

    def get_channels(self) -> list[tuple[int, str]]:
        """Return list of (index, name) for configured (non-disabled) channels.

        Falls back to [(0, 'Primary')] if channel config is unavailable.
        """
        if self._interface is None:
            return [(0, "Primary")]
        try:
            chans = self._interface.localNode.channels
            result = []
            for i, ch in enumerate(chans):
                # role 0 == DISABLED in Meshtastic protobuf
                if getattr(ch, "role", 0) != 0:
                    try:
                        name = ch.settings.name.strip()
                    except Exception:
                        name = ""
                    display = name if name else ("Primary" if i == 0 else f"Ch {i}")
                    result.append((i, display))
            return result if result else [(0, "Primary")]
        except Exception:
            return [(0, "Primary")]

    @property
    def transport_type(self) -> str:
        """Return a human-readable transport type name."""
        return self.__class__.__name__.replace("Transport", "").lower()
