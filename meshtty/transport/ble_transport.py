import logging

import meshtastic.ble_interface

from .base import TransportManager

log = logging.getLogger(__name__)


class BLETransport(TransportManager):
    def __init__(self, address: str) -> None:
        super().__init__()
        self._address = address

    def connect(self) -> None:
        log.debug("BLEInterface connecting to %s", self._address)
        self._interface = meshtastic.ble_interface.BLEInterface(self._address)
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
