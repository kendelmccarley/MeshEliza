import logging

import meshtastic.serial_interface

from .base import TransportManager

log = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 120.0  # seconds; default 30s is too short for large node DBs


class _SerialInterface(meshtastic.serial_interface.SerialInterface):
    """SerialInterface that recovers when configCompleteId is lost in a noisy stream.

    Some radios (e.g. Heltec V3) mix UART debug text into the serial stream,
    which corrupts protobuf framing and can cause configCompleteId to be lost.
    If _waitConnected times out but the interface already has node data, we
    force the connected state ourselves so the app can proceed normally.

    Also sets transport._interface early (right after _waitConnected, before
    waitForConfig) so that is_connected returns True immediately when
    ConnectionEstablished is processed by the asyncio loop.
    """

    def __init__(self, dev_path: str, transport=None) -> None:
        self._transport_ref = transport
        super().__init__(dev_path)

    def _waitConnected(self, timeout: float = _CONNECT_TIMEOUT) -> None:
        try:
            super()._waitConnected(timeout=timeout)
        except Exception as exc:
            if "Timed out" in str(exc) and self.nodes:
                log.warning(
                    "_waitConnected timed out but %d nodes present — "
                    "forcing connected state (configCompleteId likely lost in noisy stream)",
                    len(self.nodes),
                )
                self._connected()  # sets isConnected, starts heartbeat, fires pubsub event
            else:
                raise
        # Set transport._interface NOW — before waitForConfig runs — so that
        # is_connected returns True by the time ConnectionEstablished is
        # processed by the asyncio loop (post_message is non-blocking, so
        # the event loop won't process the event until after this returns).
        if self._transport_ref is not None:
            self._transport_ref._interface = self
            log.debug("_interface set early on transport (pre-waitForConfig)")

    def waitForConfig(self) -> None:
        try:
            super().waitForConfig()
        except Exception as exc:
            if "Timed out" in str(exc):
                has_myinfo = getattr(self, "myInfo", None)
                has_nodes = getattr(self, "nodes", None)
                if has_myinfo and has_nodes:
                    log.warning(
                        "waitForConfig timed out but myInfo and %d nodes present — "
                        "proceeding without full config (channels/localConfig incomplete)",
                        len(self.nodes),
                    )
                    return
            raise


class SerialTransport(TransportManager):
    def __init__(self, dev_path: str) -> None:
        super().__init__()
        self._dev_path = dev_path

    def connect(self) -> None:
        log.debug("SerialInterface opening %s (timeout=%ss)", self._dev_path, int(_CONNECT_TIMEOUT))
        self._interface = _SerialInterface(self._dev_path, transport=self)
        log.debug("SerialInterface opened successfully")

    def disconnect(self) -> None:
        if self._interface is not None:
            self._interface.close()
            self._interface = None

    @property
    def transport_type(self) -> str:
        return "serial"

    def __str__(self) -> str:
        return f"Serial ({self._dev_path})"
