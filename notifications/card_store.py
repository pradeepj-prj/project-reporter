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
                    created_at TEXT NOT NULL,
                    card_type TEXT NOT NULL DEFAULT 'factual'
                );
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL REFERENCES cards(id),
                    channel_id TEXT NOT NULL,
                    message_id TEXT,
                    posted_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deep_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    round INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    doc_path TEXT NOT NULL,
                    cards_generated INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_cards_project ON cards(project);
                CREATE INDEX IF NOT EXISTS idx_history_channel ON post_history(channel_id);
                CREATE INDEX IF NOT EXISTS idx_deep_analysis_project ON deep_analysis(project);
            """)
            # Migrate existing cards table if card_type column is missing
            cols = [
                row[1]
                for row in conn.execute("PRAGMA table_info(cards)").fetchall()
            ]
            if "card_type" not in cols:
                conn.execute(
                    "ALTER TABLE cards ADD COLUMN card_type TEXT NOT NULL DEFAULT 'factual'"
                )

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
        card_type: str = "factual",
    ) -> int:
        """Store a new knowledge card. Returns the card ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO cards (project, title, summary, insight, tags, source_path, source_url, created_at, card_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (project, title, summary, insight, json.dumps(tags or []), source_path, source_url, now, card_type),
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

    def has_unposted_cards_for_project(self, project: str, channel_id: str) -> bool:
        """Check if there are any unposted cards for a project in a channel."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM cards c
                   WHERE c.project = ?
                     AND c.id NOT IN (
                         SELECT card_id FROM post_history WHERE channel_id = ?
                     )""",
                (project, channel_id),
            ).fetchone()
            return (row[0] if row else 0) > 0

    def get_deep_analysis_round(self, project: str) -> int:
        """Return the current deep analysis round for a project (0 if none)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(round) FROM deep_analysis WHERE project = ?",
                (project,),
            ).fetchone()
            return row[0] if row and row[0] is not None else 0

    def record_deep_analysis(
        self, project: str, round_num: int, doc_path: str, cards_generated: int
    ) -> int:
        """Record a completed deep analysis round. Returns the record ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO deep_analysis (project, round, generated_at, doc_path, cards_generated)
                   VALUES (?, ?, ?, ?, ?)""",
                (project, round_num, now, doc_path, cards_generated),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_deep_analysis_docs(self, project: str) -> list[dict[str, Any]]:
        """Get all deep analysis records for a project, ordered by round."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM deep_analysis WHERE project = ? ORDER BY round",
                (project,),
            ).fetchall()
            return [dict(row) for row in rows]
