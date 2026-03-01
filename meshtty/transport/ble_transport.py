import logging

import meshtastic.ble_interface

from .base import TransportManager

log = logging.getLogger(__name__)


class _BLEInterface(meshtastic.ble_interface.BLEInterface):
    """BLEInterface that sets transport._interface early (before waitForConfig)."""

    def __init__(self, address: str, transport=None) -> None:
        self._transport_ref = transport
        super().__init__(address)

    def _waitConnected(self, timeout=30) -> None:
        super()._waitConnected(timeout=timeout)
        if self._transport_ref is not None:
            self._transport_ref._interface = self
            log.debug("_interface set early on BLETransport (pre-waitForConfig)")


class BLETransport(TransportManager):
    def __init__(self, address: str) -> None:
        super().__init__()
        self._address = address

    def connect(self) -> None:
        log.debug("BLEInterface connecting to %s", self._address)
        self._interface = _BLEInterface(self._address, transport=self)
        log.debug("BLEInterface connected")

    def disconnect(self) -> None:
        if self._interface is not None:
            self._interface.close()
            self._interface = None

    @property
    def transport_type(self) -> str:
        return "ble"

    def __str__(self) -> str:
        return f"BLE ({self._address})"
