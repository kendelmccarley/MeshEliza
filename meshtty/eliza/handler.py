"""ElizaHandler — manages per-node Eliza sessions over Meshtastic DMs.

A session is created automatically when a node sends a direct message
whose text begins with "eliza" (case-insensitive).  Subsequent DMs from
that node are fed into the session until the user sends a quit word
(bye / goodbye / quit), which closes the session and sends the final
message.

Usage::

    handler = ElizaHandler()

    # Incoming DM from node "!abc123"
    if handler.is_active(node_id):
        reply = handler.respond(node_id, text)   # None → session ended
    elif handler.is_trigger(text):
        greeting = handler.start(node_id)
        after    = handler.first_input(text)      # text after "eliza"
        reply    = handler.respond(node_id, after) if after else None
"""

from __future__ import annotations

import logging
from pathlib import Path

from meshtty.eliza.engine import Eliza

log = logging.getLogger(__name__)

_DOCTOR = Path(__file__).parent / "doctor.txt"

# Maximum safe single-packet text length for Meshtastic
MAX_REPLY_LEN = 200


def _truncate(text: str) -> str:
    if len(text) <= MAX_REPLY_LEN:
        return text
    return text[:MAX_REPLY_LEN - 3] + "..."


class ElizaHandler:
    """Manages per-node Eliza sessions."""

    def __init__(self, script_path: Path = _DOCTOR) -> None:
        self._script = str(script_path)
        self._sessions: dict[str, Eliza] = {}

    # ------------------------------------------------------------------
    # Session queries
    # ------------------------------------------------------------------

    def is_active(self, node_id: str) -> bool:
        """Return True if an Eliza session is open for *node_id*."""
        return node_id in self._sessions

    @staticmethod
    def is_trigger(text: str) -> bool:
        """Return True if *text* should open a new session."""
        return text.strip().lower().startswith("eliza")

    @staticmethod
    def first_input(text: str) -> str:
        """Extract the text after the "eliza" trigger word, if any."""
        return text.strip()[5:].strip()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self, node_id: str) -> str:
        """Open a session for *node_id* and return the initial greeting."""
        bot = Eliza()
        bot.load(self._script)
        self._sessions[node_id] = bot
        log.info("Eliza session started for %s", node_id)
        return _truncate(bot.initial())

    def respond(self, node_id: str, text: str) -> str | None:
        """Feed *text* into the active session.

        Returns the bot's reply, or ``None`` if the session has ended
        (user sent a quit word — the final message has already been
        consumed internally; the caller should fetch it via
        ``end_session()`` *before* calling this, or handle None here).

        Actually: returns the *final* goodbye string when a quit word
        is detected, then removes the session — so the caller can
        send it and the session is gone.  Returns ``None`` only when
        ``node_id`` has no active session.
        """
        bot = self._sessions.get(node_id)
        if bot is None:
            return None
        reply = bot.respond(text)
        if reply is None:
            # Quit word — send the farewell and close the session
            final = bot.final()
            del self._sessions[node_id]
            log.info("Eliza session ended (quit) for %s", node_id)
            return _truncate(final)
        return _truncate(reply)

    def close(self, node_id: str) -> str | None:
        """Force-close a session, returning the final message or None."""
        bot = self._sessions.pop(node_id, None)
        if bot is None:
            return None
        log.info("Eliza session force-closed for %s", node_id)
        return _truncate(bot.final())
