"""Track generated knowledge cards and posting history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "card_store.db"


class CardStore:
    """SQLite-backed store for knowledge cards and posting history."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    insight TEXT,
                    tags TEXT,  -- JSON array
                    source_path TEXT,
                    source_url TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL REFERENCES cards(id),
                    channel_id TEXT NOT NULL,
                    message_id TEXT,
                    posted_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cards_project ON cards(project);
                CREATE INDEX IF NOT EXISTS idx_history_channel ON post_history(channel_id);
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def add_card(
        self,
        project: str,
        title: str,
        summary: str,
        insight: str = "",
        tags: list[str] | None = None,
        source_path: str = "",
        source_url: str = "",
    ) -> int:
        """Store a new knowledge card. Returns the card ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO cards (project, title, summary, insight, tags, source_path, source_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (project, title, summary, insight, json.dumps(tags or []), source_path, source_url, now),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def record_post(self, card_id: int, channel_id: str, message_id: str = "") -> None:
        """Record that a card was posted to a channel."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO post_history (card_id, channel_id, message_id, posted_at) VALUES (?, ?, ?, ?)",
                (card_id, channel_id, message_id, now),
            )

    def get_unposted_cards(self, project: str, channel_id: str, limit: int = 1) -> list[dict[str, Any]]:
        """Get cards for a project that haven't been posted to a channel yet."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT c.* FROM cards c
                   WHERE c.project = ?
                     AND c.id NOT IN (
                         SELECT card_id FROM post_history WHERE channel_id = ?
                     )
                   ORDER BY c.id
                   LIMIT ?""",
                (project, channel_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_card(self, card_id: int) -> dict[str, Any] | None:
        """Get a single card by ID."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            return dict(row) if row else None
