"""CommandHandler — parse and execute slash commands received via DM."""

from __future__ import annotations

import csv
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_JOKES_FILE = _DATA_DIR / "shortjokes.csv"
_GPIO_BASE = Path("/sys/class/gpio")
_INDEX_FILE = Path.home() / ".config" / "mesheliza" / "joke_index"
_MAX_MSG_LEN = 200

_HELP_TEXT = "/HELP /INFO /JOKE /GPIO /WEATHER /NEWS /NULL"
_INFO_TEXT = "https://github.com/kendelmccarley/MeshEliza"

_KNOWN_COMMANDS = {
    "/HELP",
    "/INFO",
    "/JOKE",
    "/GPIO",
    "/WEATHER",
    "/NEWS",
    "/NULL",
}


def _truncate(text: str) -> str:
    if len(text) <= _MAX_MSG_LEN:
        return text
    return text[: _MAX_MSG_LEN - 3] + "..."


class CommandHandler:
    """Handles slash commands in direct messages.

    Call ``handle(text)`` on any incoming DM text that starts with ``/``.
    Returns a reply string for valid commands, or ``None`` for unknown ones.
    Unknown commands should be silently dropped by the caller.
    """

    def __init__(self) -> None:
        self._jokes: list[str] = []
        self._joke_index: int = 0
        self._jokes_file_missing: bool = False
        self._jokes_ready = threading.Event()
        self._lock = threading.Lock()
        threading.Thread(target=self._load_jokes, daemon=True).start()

    # ------------------------------------------------------------------
    # Background joke loader
    # ------------------------------------------------------------------

    def _load_jokes(self) -> None:
        if not _JOKES_FILE.exists():
            self._jokes_file_missing = True
            self._jokes_ready.set()
            return
        try:
            jokes: list[str] = []
            with open(_JOKES_FILE, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    joke = (row.get("Joke") or "").strip()
                    if joke:
                        jokes.append(joke)
            self._jokes = jokes
        except Exception:
            pass
        # Restore saved position, clamped to the actual list length.
        if self._jokes:
            try:
                saved = int(_INDEX_FILE.read_text().strip())
                self._joke_index = saved % len(self._jokes)
            except Exception:
                self._joke_index = 0
        self._jokes_ready.set()

    def _save_index(self) -> None:
        try:
            _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            _INDEX_FILE.write_text(str(self._joke_index))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def handle(self, text: str) -> str | None:
        """Parse *text* as a slash command.

        Returns a reply string for valid commands; ``None`` if the command is
        not recognised (caller should silently drop the message).
        """
        word = text.strip().split()[0].upper() if text.strip() else ""
        if word not in _KNOWN_COMMANDS:
            return None
        if word == "/HELP":
            return _HELP_TEXT
        if word == "/INFO":
            return _INFO_TEXT
        if word == "/JOKE":
            return _truncate(self._next_joke())
        if word == "/GPIO":
            return _truncate(self._read_gpio())
        if word == "/WEATHER":
            return "Probably sunny and warm... but this feature is not implemented"
        if word == "/NEWS":
            return "Not much. What's new with you?"
        if word == "/NULL":
            return "All is nothingness"
        return None  # unreachable but satisfies type checkers

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _next_joke(self) -> str:
        if not self._jokes_ready.wait(timeout=5.0):
            return "Still loading jokes, try again in a moment."
        with self._lock:
            if self._jokes_file_missing or not self._jokes:
                if self._jokes_file_missing:
                    return "No joke for you.  It's a dull day."
                return "No jokes available."
            joke = self._jokes[self._joke_index]
            self._joke_index = (self._joke_index + 1) % len(self._jokes)
            self._save_index()
            return joke

    def _read_gpio(self) -> str:
        if not _GPIO_BASE.exists():
            return "GPIO not available on this system."
        try:
            pins: list[str] = []
            for entry in sorted(_GPIO_BASE.iterdir()):
                name = entry.name
                if name.startswith("gpio") and name[4:].isdigit():
                    direction_path = entry / "direction"
                    value_path = entry / "value"
                    try:
                        direction = (
                            direction_path.read_text().strip()
                            if direction_path.exists()
                            else "?"
                        )
                        value = (
                            value_path.read_text().strip()
                            if value_path.exists()
                            else "?"
                        )
                        pins.append(f"GPIO{name[4:]}:{direction}/{value}")
                    except Exception:
                        pass
            if not pins:
                return "No GPIO pins currently exported."
            return " ".join(pins)
        except Exception as exc:
            return f"GPIO read error: {exc}"
