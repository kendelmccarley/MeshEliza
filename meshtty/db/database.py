import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id  TEXT,
                    from_id    TEXT    NOT NULL,
                    to_id      TEXT    NOT NULL,
                    channel    INTEGER DEFAULT 0,
                    text       TEXT    NOT NULL,
                    rx_time    INTEGER NOT NULL,
                    is_mine    INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel);
                CREATE INDEX IF NOT EXISTS idx_messages_rx_time  ON messages(rx_time);
                CREATE INDEX IF NOT EXISTS idx_messages_from     ON messages(from_id);

                CREATE TABLE IF NOT EXISTS nodes (
                    node_id    TEXT PRIMARY KEY,
                    short_name TEXT,
                    long_name  TEXT,
                    hw_model   TEXT,
                    last_snr   REAL,
                    last_lat   REAL,
                    last_lon   REAL,
                    last_alt   INTEGER,
                    battery    INTEGER,
                    last_heard INTEGER,
                    updated_at INTEGER
                );
            """)
            try:
                self._conn.execute(
                    "ALTER TABLE messages ADD COLUMN display_prefix TEXT DEFAULT ''"
                )
                self._conn.commit()
            except Exception:
                pass  # column already exists

    def insert_message(
        self,
        from_id: str,
        to_id: str,
        channel: int,
        text: str,
        rx_time: int,
        is_mine: bool = False,
        packet_id: str | None = None,
        display_prefix: str = "",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages "
                "(packet_id, from_id, to_id, channel, text, rx_time, is_mine, display_prefix) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (packet_id, from_id, to_id, channel, text, rx_time, int(is_mine), display_prefix),
            )
            self._conn.commit()

    def get_messages(self, limit: int = 200) -> list:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM messages ORDER BY rx_time DESC LIMIT ?",
                (limit,),
            )
            return list(reversed(cur.fetchall()))

    def upsert_node(self, node_id: str, info: dict) -> None:
        now = int(datetime.now().timestamp())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO nodes
                    (node_id, short_name, long_name, hw_model,
                     last_snr, last_lat, last_lon, last_alt,
                     battery, last_heard, updated_at)
                VALUES
                    (:node_id, :short_name, :long_name, :hw_model,
                     :last_snr, :last_lat, :last_lon, :last_alt,
                     :battery, :last_heard, :updated_at)
                ON CONFLICT(node_id) DO UPDATE SET
                    short_name = excluded.short_name,
                    long_name  = excluded.long_name,
                    hw_model   = excluded.hw_model,
                    last_snr   = excluded.last_snr,
                    last_lat   = excluded.last_lat,
                    last_lon   = excluded.last_lon,
                    last_alt   = excluded.last_alt,
                    battery    = excluded.battery,
                    last_heard = excluded.last_heard,
                    updated_at = excluded.updated_at
                """,
                {
                    "node_id": node_id,
                    "short_name": info.get("short_name"),
                    "long_name": info.get("long_name"),
                    "hw_model": info.get("hw_model"),
                    "last_snr": info.get("last_snr"),
                    "last_lat": info.get("last_lat"),
                    "last_lon": info.get("last_lon"),
                    "last_alt": info.get("last_alt"),
                    "battery": info.get("battery"),
                    "last_heard": info.get("last_heard"),
                    "updated_at": now,
                },
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()
