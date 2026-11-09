"""All SQL for the favorites table."""
import sqlite3
from typing import Dict, List, Optional, Set

from data.connection import connection_scope
from models.media import MediaItem


def _to_item(row: sqlite3.Row) -> MediaItem:
    return MediaItem(
        id=row["id"],
        media_type=row["media_type"],
        external_id=row["external_id"],
        title=row["title"],
        subtitle=row["subtitle"],
        image_url=row["image_url"],
        timestamp=row["created_at"],
    )


class FavoritesRepository:
    def add(self, user_id: int, item: MediaItem) -> None:
        """Add a favorite. Adding the same item twice does nothing.

        Only duplicates are ignored; an invalid media_type still raises.
        """
        with connection_scope() as conn:
            conn.execute(
                "INSERT INTO favorites "
                "(user_id, media_type, external_id, title, subtitle, image_url) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, media_type, external_id) DO NOTHING",
                (user_id, item.media_type, item.external_id, item.title,
                 item.subtitle, item.image_url),
            )

    def remove(self, user_id: int, media_type: str, external_id: str) -> None:
        with connection_scope() as conn:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND media_type = ? AND external_id = ?",
                (user_id, media_type, external_id),
            )

    def is_favorite(self, user_id: int, media_type: str, external_id: str) -> bool:
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND media_type = ? AND external_id = ?",
                (user_id, media_type, external_id),
            ).fetchone()
        return row is not None

    def list_ids(self, user_id: int, media_type: str) -> Set[str]:
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT external_id FROM favorites WHERE user_id = ? AND media_type = ?",
                (user_id, media_type),
            ).fetchall()
        return {row["external_id"] for row in rows}

    def list_for_user(
        self, user_id: int, media_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[MediaItem]:
        query = "SELECT * FROM favorites WHERE user_id = ?"
        params: list = [user_id]
        if media_type:
            query += " AND media_type = ?"
            params.append(media_type)
        query += " ORDER BY created_at DESC, id DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with connection_scope() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_to_item(row) for row in rows]

    def count_by_type(self, user_id: int) -> Dict[str, int]:
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT media_type, COUNT(*) AS total FROM favorites "
                "WHERE user_id = ? GROUP BY media_type",
                (user_id,),
            ).fetchall()
        return {row["media_type"]: row["total"] for row in rows}
