"""SQLite connections. Each call opens its own connection, so threads are safe."""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from config import settings
from core.exceptions import DatabaseError
from utils.logger import get_logger

logger = get_logger("database")


def open_connection() -> sqlite3.Connection:
    settings.ensure_storage_dirs()
    connection = sqlite3.connect(str(settings.DATABASE_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    """Commit on success, roll back on error, always close."""
    connection = open_connection()
    try:
        yield connection
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        raise  # repositories turn this into a clear message
    except sqlite3.Error as exc:
        connection.rollback()
        logger.error("Database error: %s", exc)
        raise DatabaseError("A database error occurred.") from exc
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
