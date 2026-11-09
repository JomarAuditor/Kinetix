"""All SQL for the history table (Recently Played)."""
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.constants import HISTORY_LIMIT
from data.connection import connection_scope
from models.media import MediaItem


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _to_item(row: sqlite3.Row) -> MediaItem:
    return MediaItem(
        id=row["id"],
        media_type=row["media_type"],
        external_id=row["external_id"],
        title=row["title"],
        subtitle=row["subtitle"],
        image_url=row["image_url"],
        timestamp=row["last_accessed"],
    )


class HistoryRepository:
    def record(self, user_id: int, item: MediaItem) -> None:
        """Insert the item, or only refresh last_accessed if it already exists."""
        with connection_scope() as conn:
            conn.execute(
                "INSERT INTO history "
                "(user_id, media_type, external_id, title, subtitle, image_url, last_accessed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, media_type, external_id) DO UPDATE SET "
                "last_accessed = excluded.last_accessed, title = excluded.title, "
                "subtitle = excluded.subtitle, image_url = excluded.image_url",
                (user_id, item.media_type, item.external_id, item.title,
                 item.subtitle, item.image_url, _utc_now_text()),
            )
            # Keep only the newest HISTORY_LIMIT rows for this user.
            conn.execute(
                "DELETE FROM history WHERE user_id = ? AND id NOT IN ("
                "SELECT id FROM history WHERE user_id = ? "
                "ORDER BY last_accessed DESC, id DESC LIMIT ?)",
                (user_id, user_id, HISTORY_LIMIT),
            )

    def list_for_user(
        self, user_id: int, media_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[MediaItem]:
        query = "SELECT * FROM history WHERE user_id = ?"
        params: list = [user_id]
        if media_type:
            query += " AND media_type = ?"
            params.append(media_type)
        query += " ORDER BY last_accessed DESC, id DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with connection_scope() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_to_item(row) for row in rows]

    def count_by_type(self, user_id: int) -> Dict[str, int]:
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT media_type, COUNT(*) AS total FROM history "
                "WHERE user_id = ? GROUP BY media_type",
                (user_id,),
            ).fetchall()
        return {row["media_type"]: row["total"] for row in rows}

    def clear(self, user_id: int) -> None:
        with connection_scope() as conn:
            conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
