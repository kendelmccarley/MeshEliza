"""ElizaHandler — manages per-node Eliza sessions over Meshtastic DMs.

A session is created automatically on the first direct message received from a
node.  All subsequent DMs from that node are fed into the session.  The session
closes when:

  * the remote node sends a quit word (bye / goodbye / quit), or
  * no message has been received from that node for SESSION_TIMEOUT seconds
    (checked lazily when the next message arrives).

A new session starts automatically on the next message after a close.

Usage::

    handler = ElizaHandler()

    # Incoming DM from node "!abc123"
    greeting = handler.ensure_session(node_id)   # str if new, None if already open
    reply = handler.respond(node_id, text)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from meshtty.eliza.engine import Eliza

log = logging.getLogger(__name__)

_DOCTOR = Path(__file__).parent / "doctor.txt"

# Maximum safe single-packet text length for Meshtastic
MAX_REPLY_LEN = 200

# Idle timeout before a session is silently expired
SESSION_TIMEOUT = 30 * 60  # 30 minutes


def _truncate(text: str) -> str:
    if len(text) <= MAX_REPLY_LEN:
        return text
    return text[:MAX_REPLY_LEN - 3] + "..."


class ElizaHandler:
    """Manages per-node Eliza sessions with automatic timeout."""

    def __init__(self, script_path: Path = _DOCTOR) -> None:
        self._script = str(script_path)
        self._sessions: dict[str, Eliza] = {}
        self._last_activity: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Session queries
    # ------------------------------------------------------------------

    def is_active(self, node_id: str) -> bool:
        """Return True if a live, non-expired session exists for *node_id*."""
        if node_id not in self._sessions:
            return False
        if time.monotonic() - self._last_activity.get(node_id, 0) > SESSION_TIMEOUT:
            self._expire(node_id)
            return False
        return True

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def ensure_session(self, node_id: str) -> str | None:
        """Ensure a session exists for *node_id*.

        Returns the initial greeting string if a new session was started,
        or ``None`` if a session was already active.
        """
        if self.is_active(node_id):
            return None
        return self.start(node_id)

    def start(self, node_id: str) -> str:
        """Open a session for *node_id* and return the initial greeting."""
        bot = Eliza()
        bot.load(self._script)
        self._sessions[node_id] = bot
        self._last_activity[node_id] = time.monotonic()
        log.info("Eliza session started for %s", node_id)
        return _truncate(bot.initial())

    def respond(self, node_id: str, text: str) -> str | None:
        """Feed *text* into the active session and return the bot's reply.

        Returns the farewell string when a quit word is detected (session is
        then removed).  Returns ``None`` if no session exists for *node_id*.
        """
        bot = self._sessions.get(node_id)
        if bot is None:
            return None
        self._last_activity[node_id] = time.monotonic()
        reply = bot.respond(text)
        if reply is None:
            # Quit word — send the farewell and close the session
            final = bot.final()
            self._sessions.pop(node_id, None)
            self._last_activity.pop(node_id, None)
            log.info("Eliza session ended (quit) for %s", node_id)
            return _truncate(final)
        return _truncate(reply)

    def close(self, node_id: str) -> str | None:
        """Force-close a session, returning the final message or None."""
        bot = self._sessions.pop(node_id, None)
        self._last_activity.pop(node_id, None)
        if bot is None:
            return None
        log.info("Eliza session force-closed for %s", node_id)
        return _truncate(bot.final())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _expire(self, node_id: str) -> None:
        """Silently remove an expired session."""
        self._sessions.pop(node_id, None)
        self._last_activity.pop(node_id, None)
        log.info("Eliza session expired (30-min timeout) for %s", node_id)
