"""MessageLog — optional append-only log of all sent and received messages."""

from __future__ import annotations

import threading
import time
from pathlib import Path

MESSAGE_LOG_FILE = Path("/tmp/mesheliza-messages.log")


class MessageLog:
    """Appends one timestamped line per message to a plain-text file.

    The file is opened fresh on every write so it is automatically re-created
    if it has been deleted while the app is running.
    """

    def __init__(self, path: Path = MESSAGE_LOG_FILE) -> None:
        self._path = path
        self._lock = threading.Lock()

    def log(self, direction: str, prefix: str, text: str) -> None:
        """Append one line: ``YYYY-MM-DD HH:MM:SS [RX|TX] prefix: text``.

        ``direction`` should be ``"RX"`` for received messages and ``"TX"``
        for sent messages (including bot replies).
        Silently ignores any I/O error so a missing or unwritable file never
        affects app operation.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} [{direction}] {prefix}: {text}\n"
        with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
            except Exception:
                pass
