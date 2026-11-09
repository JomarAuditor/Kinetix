"""All SQL for the user_settings table."""
from typing import Dict

from data.connection import connection_scope


class SettingsRepository:
    def get(self, user_id: int, key: str) -> str | None:
        with connection_scope() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE user_id = ? AND key = ?", (user_id, key)
            ).fetchone()
        return row["value"] if row is not None else None

    def get_all(self, user_id: int) -> Dict[str, str]:
        with connection_scope() as conn:
            rows = conn.execute(
                "SELECT key, value FROM user_settings WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {row["key"]: row["value"] for row in rows}

    def set_many(self, user_id: int, values: Dict[str, str]) -> None:
        with connection_scope() as conn:
            conn.executemany(
                "INSERT INTO user_settings (user_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, key) DO UPDATE SET value = excluded.value",
                [(user_id, key, str(value)) for key, value in values.items()],
            )
