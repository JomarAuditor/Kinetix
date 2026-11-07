"""Paths and environment configuration (API keys come from .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
LOGOS_DIR = ASSETS_DIR / "logos"
PLACEHOLDERS_DIR = ASSETS_DIR / "placeholders"

STORAGE_DIR = BASE_DIR / "storage"
CACHE_DIR = STORAGE_DIR / "cache"
LOG_DIR = STORAGE_DIR / "logs"
LOG_FILE = LOG_DIR / "kinetix.log"
DATABASE_PATH = STORAGE_DIR / "kinetix.db"
LOCAL_SETTINGS_PATH = STORAGE_DIR / "local_settings.json"
# Explicit authorization records for movie sources (verified channels, public domain). See BACKEND.md.
MOVIE_SOURCES_PATH = BASE_DIR / "config" / "movie_sources.json"

load_dotenv(BASE_DIR / ".env")


def ensure_storage_dirs() -> None:
    """Create the storage folders if they do not exist yet."""
    for folder in (STORAGE_DIR, CACHE_DIR, LOG_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def get_tmdb_api_key() -> str:
    return os.environ.get("TMDB_API_KEY", "").strip()


def get_youtube_api_key() -> str:
    return os.environ.get("YOUTUBE_API_KEY", "").strip()


def get_rawg_api_key() -> str:
    return os.environ.get("RAWG_API_KEY", "").strip()


def get_movie_min_minutes() -> int:
    """Shortest upload (in minutes) that can count as a full-length movie. Default 60, set MOVIE_MIN_DURATION_MINUTES in .env."""
    try:
        value = int(os.environ.get("MOVIE_MIN_DURATION_MINUTES", "60").strip())
    except ValueError:
        value = 60
    return max(20, min(240, value))
