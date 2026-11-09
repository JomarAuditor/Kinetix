"""Favorites, history and playback settings in one place. Wraps the repositories for the GUI."""
from dataclasses import dataclass
from typing import List, Optional, Set

from config.constants import (DEFAULT_USER_SETTINGS, MOVIE_POSITION_KEY_PREFIX, SETTING_AUTOPLAY,
                              SETTING_MOVIE_VOLUME, SETTING_REMEMBER_POSITION, SETTING_SHOW_LYRICS,
                              SETTING_VOLUME)
from data.repositories.favorites_repository import FavoritesRepository
from data.repositories.history_repository import HistoryRepository
from data.repositories.settings_repository import SettingsRepository
from models.media import MediaItem


@dataclass
class PlaybackSettings:
    volume: int = 70
    autoplay_next: bool = True
    show_lyrics: bool = True


@dataclass
class MovieSettings:
    volume: int = 70
    remember_position: bool = False


def _as_bool(value: str, default: bool) -> bool:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return default


def _as_volume(value: str, default: int) -> int:
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return default


class LibraryService:
    def __init__(self, favorites: Optional[FavoritesRepository] = None,
                 history: Optional[HistoryRepository] = None,
                 settings: Optional[SettingsRepository] = None) -> None:
        self._favorites = favorites or FavoritesRepository()
        self._history = history or HistoryRepository()
        self._settings = settings or SettingsRepository()

    # ---- favorites ----
    def toggle_favorite(self, user_id: int, item: MediaItem) -> bool:
        """Add or remove the favorite. Returns the new state (True = now a favorite)."""
        if self._favorites.is_favorite(user_id, item.media_type, item.external_id):
            self._favorites.remove(user_id, item.media_type, item.external_id)
            return False
        self._favorites.add(user_id, item)
        return True

    def is_favorite(self, user_id: int, media_type: str, external_id: str) -> bool:
        return self._favorites.is_favorite(user_id, media_type, external_id)

    def favorite_ids(self, user_id: int, media_type: str) -> Set[str]:
        return self._favorites.list_ids(user_id, media_type)

    def latest_favorites(self, user_id: int, limit: int) -> List[MediaItem]:
        return self._favorites.list_for_user(user_id, limit=limit)

    # ---- history ----
    def record_play(self, user_id: int, item: MediaItem) -> None:
        self._history.record(user_id, item)

    def latest_history(self, user_id: int, limit: int) -> List[MediaItem]:
        return self._history.list_for_user(user_id, limit=limit)

    # ---- settings (defaults when nothing is saved) ----
    def playback_settings(self, user_id: int) -> PlaybackSettings:
        saved = {**DEFAULT_USER_SETTINGS, **self._settings.get_all(user_id)}
        defaults = PlaybackSettings()
        return PlaybackSettings(
            volume=_as_volume(saved.get(SETTING_VOLUME), defaults.volume),
            autoplay_next=_as_bool(saved.get(SETTING_AUTOPLAY), defaults.autoplay_next),
            show_lyrics=_as_bool(saved.get(SETTING_SHOW_LYRICS), defaults.show_lyrics),
        )

    def movie_settings(self, user_id: int) -> MovieSettings:
        saved = {**DEFAULT_USER_SETTINGS, **self._settings.get_all(user_id)}
        defaults = MovieSettings()
        vol_raw = saved.get(SETTING_MOVIE_VOLUME) or saved.get(SETTING_VOLUME)
        return MovieSettings(
            volume=_as_volume(vol_raw, defaults.volume),
            remember_position=_as_bool(saved.get(SETTING_REMEMBER_POSITION), defaults.remember_position),
        )

    def get_movie_position(self, user_id: int, movie_key: str) -> int:
        raw = self._settings.get(user_id, f"{MOVIE_POSITION_KEY_PREFIX}{movie_key}")
        try:
            return max(0, int(raw)) if raw is not None else 0
        except (TypeError, ValueError):
            return 0

    def save_movie_position(self, user_id: int, movie_key: str, position_ms: int) -> None:
        self._settings.set_many(user_id, {
            f"{MOVIE_POSITION_KEY_PREFIX}{movie_key}": str(max(0, int(position_ms)))
        })

    # ---- game high scores ----
    def get_game_high_score(self, user_id: int, game_id: str) -> int:
        raw = self._settings.get(user_id, f"game_best:{game_id}")
        try:
            return max(0, int(raw)) if raw is not None else 0
        except (TypeError, ValueError):
            return 0

    def save_game_high_score(self, user_id: int, game_id: str, score: int) -> int:
        best = max(self.get_game_high_score(user_id, game_id), max(0, int(score)))
        self._settings.set_many(user_id, {f"game_best:{game_id}": str(best)})
        return best
