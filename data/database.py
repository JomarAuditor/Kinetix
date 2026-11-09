"""Creates the database tables on first run."""
from data.connection import connection_scope
from utils.logger import get_logger

logger = get_logger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    iterations    INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_type  TEXT NOT NULL CHECK (media_type IN ('music', 'movie', 'game')),
    external_id TEXT NOT NULL,
    title       TEXT NOT NULL,
    subtitle    TEXT NOT NULL DEFAULT '',
    image_url   TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, media_type, external_id)
);

CREATE TABLE IF NOT EXISTS history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    media_type    TEXT NOT NULL CHECK (media_type IN ('music', 'movie', 'game')),
    external_id   TEXT NOT NULL,
    title         TEXT NOT NULL,
    subtitle      TEXT NOT NULL DEFAULT '',
    image_url     TEXT NOT NULL DEFAULT '',
    last_accessed TEXT NOT NULL,
    UNIQUE (user_id, media_type, external_id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key     TEXT NOT NULL,
    value   TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS youtube_movies (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id         TEXT NOT NULL UNIQUE,
    tmdb_movie_id    TEXT,
    title            TEXT NOT NULL,
    channel_name     TEXT NOT NULL,
    channel_id       TEXT,
    duration_seconds INTEGER NOT NULL,
    thumbnail_url    TEXT,
    upload_date      TEXT,
    description      TEXT,
    view_count       INTEGER,
    video_url        TEXT NOT NULL,
    is_embeddable    INTEGER DEFAULT 1,
    playback_method  TEXT CHECK (playback_method IN ('vlc', 'youtube_player', 'unverified')) DEFAULT 'unverified',
    rights_verified  INTEGER DEFAULT 0,
    last_checked     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movie_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key   TEXT NOT NULL UNIQUE,
    cache_data  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_history_user ON history (user_id, last_accessed);
CREATE INDEX IF NOT EXISTS idx_youtube_movies_video ON youtube_movies (video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_movies_tmdb ON youtube_movies (tmdb_movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_cache_key ON movie_cache (cache_key, expires_at);
"""


def initialize_database() -> None:
    with connection_scope() as connection:
        connection.executescript(SCHEMA)
        # Remove legacy numeric RAWG entries now that Games uses playable APIs
        connection.execute(
            "DELETE FROM favorites WHERE media_type = 'game' AND external_id NOT LIKE '%:%'"
        )
        connection.execute(
            "DELETE FROM history WHERE media_type = 'game' AND external_id NOT LIKE '%:%'"
        )
    logger.info("Database ready")
