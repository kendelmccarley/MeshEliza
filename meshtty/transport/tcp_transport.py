import logging

import meshtastic.tcp_interface

from .base import TransportManager

log = logging.getLogger(__name__)


class _TCPInterface(meshtastic.tcp_interface.TCPInterface):
    """TCPInterface that sets transport._interface early (before waitForConfig)."""

    def __init__(self, hostname: str, port: int, transport=None) -> None:
        self._transport_ref = transport
        super().__init__(hostname, portNumber=port)

    def _waitConnected(self, timeout=30) -> None:
        super()._waitConnected(timeout=timeout)
        if self._transport_ref is not None:
            self._transport_ref._interface = self
            log.debug("_interface set early on TCPTransport (pre-waitForConfig)")


class TCPTransport(TransportManager):
    def __init__(self, hostname: str, port: int = 4403) -> None:
        super().__init__()
        self._hostname = hostname
        self._port = port

    def connect(self) -> None:
        log.debug("TCPInterface connecting to %s:%s", self._hostname, self._port)
        self._interface = _TCPInterface(self._hostname, self._port, transport=self)
        log.debug("TCPInterface connected")

    def disconnect(self) -> None:
        if self._interface is not None:
            self._interface.close()
            self._interface = None

    @property
    def transport_type(self) -> str:
        return "tcp"

    def __str__(self) -> str:
        return f"TCP ({self._hostname}:{self._port})"
