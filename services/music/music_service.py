"""Music logic: search, featured tracks, lookup and lyrics. No GUI code here."""
from collections import OrderedDict
import threading
import time
from typing import Dict, List, Optional, Tuple

from config.constants import DEFAULT_MUSIC_QUERY, FEATURED_CACHE_SECONDS, FEATURED_TRACK_LIMIT, SEARCH_RESULT_LIMIT
from integrations.api.itunes_client import ItunesClient
from integrations.api.lyrics_client import LyricsClient
from models.media import MediaItem
from models.music import Lyrics, Track

_SEARCH_CACHE_SECONDS = 300
_CACHE_MAX_ENTRIES = 64


class MusicService:
    def __init__(self, itunes: Optional[ItunesClient] = None, lyrics: Optional[LyricsClient] = None) -> None:
        self._itunes = itunes or ItunesClient()
        self._lyrics = lyrics or LyricsClient()
        self._lock = threading.Lock()
        self._featured_cache: Optional[Tuple[float, List[Track]]] = None
        self._search_cache: "OrderedDict[Tuple[str, int], Tuple[float, List[Track]]]" = OrderedDict()
        self._lookup_cache: "OrderedDict[str, Tuple[float, Optional[Track]]]" = OrderedDict()
        self._lyrics_cache: "OrderedDict[str, Tuple[float, Lyrics]]" = OrderedDict()

    @staticmethod
    def _remember(cache: OrderedDict, key, value) -> None:
        cache[key] = (time.monotonic(), value)
        cache.move_to_end(key)
        while len(cache) > _CACHE_MAX_ENTRIES:
            cache.popitem(last=False)

    def search(self, query: str, limit: int = SEARCH_RESULT_LIMIT) -> List[Track]:
        query = query.strip()
        if not query:
            return []
        key = (query.lower(), limit)
        with self._lock:
            cached = self._search_cache.get(key)
            if cached and time.monotonic() - cached[0] < _SEARCH_CACHE_SECONDS:
                self._search_cache.move_to_end(key)
                return list(cached[1])
        tracks = self._itunes.search_songs(query, limit)
        if tracks:
            with self._lock:
                self._remember(self._search_cache, key, list(tracks))
        return tracks

    def featured(self, limit: int = FEATURED_TRACK_LIMIT) -> List[Track]:
        """Tracks for the default query. Cached for a few minutes so pages open fast."""
        with self._lock:
            cached = self._featured_cache
            if cached and time.monotonic() - cached[0] < FEATURED_CACHE_SECONDS and len(cached[1]) >= limit:
                return list(cached[1][:limit])
        tracks = self._itunes.search_songs(DEFAULT_MUSIC_QUERY, max(limit, FEATURED_TRACK_LIMIT))
        if tracks:
            with self._lock:
                self._featured_cache = (time.monotonic(), list(tracks))
        return tracks[:limit]

    def featured_items(self, limit: int) -> List[MediaItem]:
        return [track.to_media_item() for track in self.featured(limit)]

    def lookup(self, track_id: str) -> Optional[Track]:
        with self._lock:
            cached = self._lookup_cache.get(track_id)
            if cached and time.monotonic() - cached[0] < _SEARCH_CACHE_SECONDS:
                self._lookup_cache.move_to_end(track_id)
                return cached[1]
        track = self._itunes.lookup_song(track_id)
        if track is not None:
            with self._lock:
                self._remember(self._lookup_cache, track_id, track)
        return track

    def lyrics(self, track: Track) -> Lyrics:
        """Synced lyrics if LRCLIB has them, else plain lyrics, else an empty Lyrics object."""
        key = track.track_id or f"{track.artist}:{track.title}".lower()
        with self._lock:
            cached = self._lyrics_cache.get(key)
            if cached and time.monotonic() - cached[0] < FEATURED_CACHE_SECONDS:
                self._lyrics_cache.move_to_end(key)
                return cached[1]
        result = self._lyrics.find(track.title, track.artist, track.album, track.duration_ms // 1000)
        with self._lock:
            self._remember(self._lyrics_cache, key, result)
        return result
