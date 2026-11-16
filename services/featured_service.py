"""Builds the Dashboard 'Featured' list by mixing music, movies and games."""
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from config.constants import (DASHBOARD_FEATURED_COUNT, FEATURED_CACHE_SECONDS, MEDIA_GAME, MEDIA_MOVIE,
                              MEDIA_MUSIC)
from core.exceptions import MissingApiKeyError
from models.media import MediaItem
from services.games.game_service import GameService
from services.movies.movie_service import MovieService
from services.music.music_service import MusicService
from utils.logger import get_logger

logger = get_logger("featured")
_SOURCE_TIMEOUT_SECONDS = 15


@dataclass
class FeaturedResult:
    items: List[MediaItem] = field(default_factory=list)
    errors: Dict[str, Exception] = field(default_factory=dict)  # media_type -> why it is missing

    @property
    def only_missing_keys(self) -> bool:
        """True when nothing loaded and the only problem is a missing API key."""
        return not self.items and bool(self.errors) and all(
            isinstance(error, MissingApiKeyError) for error in self.errors.values())


class FeaturedService:
    def __init__(self, music: MusicService, movies: Optional[MovieService] = None,
                 games: Optional[GameService] = None) -> None:
        self._music, self._movies, self._games = music, movies or MovieService(), games or GameService()
        self._cache: Optional[Tuple[float, FeaturedResult]] = None

    def load(self, count: int = DASHBOARD_FEATURED_COUNT, force: bool = False) -> FeaturedResult:
        """Runs in a background thread. One failing source never hides the others."""
        cached = self._cache
        if not force and cached and time.monotonic() - cached[0] < FEATURED_CACHE_SECONDS:
            return cached[1]
        sources: Dict[str, Callable[[], List[MediaItem]]] = {
            MEDIA_MUSIC: lambda: self._music.featured_items(count),
            MEDIA_MOVIE: lambda: self._movies.featured(count),
            MEDIA_GAME: lambda: self._games.featured(count),
        }
        result = FeaturedResult()
        lists: Dict[str, List[MediaItem]] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {kind: pool.submit(work) for kind, work in sources.items()}
            for kind, future in futures.items():
                try:
                    lists[kind] = future.result(timeout=_SOURCE_TIMEOUT_SECONDS)
                except Exception as exc:  # noqa: BLE001 - reported per source
                    result.errors[kind] = exc
                    if not isinstance(exc, MissingApiKeyError):
                        logger.warning("Featured %s failed: %s", kind, exc)
        result.items = self._interleave([lists.get(kind, []) for kind in sources], count)
        if result.items:
            self._cache = (time.monotonic(), result)
        return result

    @staticmethod
    def _interleave(lists: List[List[MediaItem]], count: int) -> List[MediaItem]:
        mixed: List[MediaItem] = []
        position = 0
        while len(mixed) < count and any(position < len(items) for items in lists):
            for items in lists:
                if position < len(items) and len(mixed) < count:
                    mixed.append(items[position])
            position += 1
        return mixed
