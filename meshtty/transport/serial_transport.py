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
    """

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
        self._interface = _SerialInterface(self._dev_path)
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
