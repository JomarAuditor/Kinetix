"""All SQL for the users table (parameterized queries only)."""
import sqlite3
from typing import Optional

from core.exceptions import DuplicateRecordError
from data.connection import connection_scope
from models.user import StoredUser, User

_USER_COLUMNS = "id, full_name, username, email, created_at"
_STORED_COLUMNS = _USER_COLUMNS + ", password_hash, salt, iterations"


def _to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        full_name=row["full_name"],
        username=row["username"],
        email=row["email"],
        created_at=row["created_at"],
    )


def _to_stored(row: sqlite3.Row) -> StoredUser:
    return StoredUser(
        user=_to_user(row),
        password_hash=row["password_hash"],
        salt=row["salt"],
        iterations=row["iterations"],
    )


def _duplicate_field(error: sqlite3.IntegrityError) -> str:
    return "email" if "users.email" in str(error) else "username"


class UserRepository:
    def create_user(
        self, full_name: str, username: str, email: str,
        password_hash: str, salt: str, iterations: int,
    ) -> User:
        try:
            with connection_scope() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (full_name, username, email, password_hash, salt, iterations) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (full_name, username, email, password_hash, salt, iterations),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(_duplicate_field(exc)) from exc
        return self.get_by_id(user_id)

    def get_by_id(self, user_id: int) -> Optional[User]:
        with connection_scope() as conn:
            row = conn.execute(
                f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return _to_user(row) if row else None

    def get_stored_by_id(self, user_id: int) -> Optional[StoredUser]:
        with connection_scope() as conn:
            row = conn.execute(
                f"SELECT {_STORED_COLUMNS} FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return _to_stored(row) if row else None

    def get_stored_by_login(self, identifier: str) -> Optional[StoredUser]:
        """Find a user by username or email (case-insensitive)."""
        with connection_scope() as conn:
            row = conn.execute(
                f"SELECT {_STORED_COLUMNS} FROM users WHERE username = ? OR email = ?",
                (identifier, identifier),
            ).fetchone()
        return _to_stored(row) if row else None

    def username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        return self._exists("username", username, exclude_user_id)

    def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        return self._exists("email", email, exclude_user_id)

    def _exists(self, column: str, value: str, exclude_user_id: Optional[int]) -> bool:
        # `column` is one of two fixed names chosen in this file, never user input.
        with connection_scope() as conn:
            row = conn.execute(
                f"SELECT 1 FROM users WHERE {column} = ? AND id != ?",
                (value, exclude_user_id if exclude_user_id is not None else -1),
            ).fetchone()
        return row is not None

    def update_profile(self, user_id: int, full_name: str, username: str, email: str) -> User:
        try:
            with connection_scope() as conn:
                conn.execute(
                    "UPDATE users SET full_name = ?, username = ?, email = ? WHERE id = ?",
                    (full_name, username, email, user_id),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(_duplicate_field(exc)) from exc
        return self.get_by_id(user_id)

    def update_password(self, user_id: int, password_hash: str, salt: str, iterations: int) -> None:
        with connection_scope() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ?, iterations = ? WHERE id = ?",
                (password_hash, salt, iterations, user_id),
            )

    def delete_user(self, user_id: int) -> None:
        with connection_scope() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
