"""LRCLIB lyrics (no key). Synced LRC first, then plain text, else empty. Nothing is hard-coded."""
import re
from typing import List, Optional, Tuple

from core.exceptions import ApiError
from integrations.api.base_client import BaseClient
from models.music import Lyrics

_TIMESTAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
_DURATION_TOLERANCE_SECONDS = 8


def parse_lrc(text: str) -> List[Tuple[int, str]]:
    """Turn LRC text into [(milliseconds, line)] sorted by time. Lines may have several timestamps."""
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        stamps = list(_TIMESTAMP.finditer(raw))
        if not stamps:
            continue
        content = raw[stamps[-1].end():].strip()
        if not content:
            continue
        for stamp in stamps:
            minutes, seconds, fraction = int(stamp.group(1)), int(stamp.group(2)), stamp.group(3) or "0"
            millis = int(fraction.ljust(3, "0")[:3])
            lines.append(((minutes * 60 + seconds) * 1000 + millis, content))
    lines.sort(key=lambda entry: entry[0])
    return lines


def _lyrics_from(entry) -> Optional[Lyrics]:
    if not isinstance(entry, dict) or entry.get("instrumental"):
        return None
    synced_text = entry.get("syncedLyrics")
    plain_text = entry.get("plainLyrics")
    synced = parse_lrc(synced_text) if isinstance(synced_text, str) else []
    plain = plain_text if isinstance(plain_text, str) else ""
    if not synced and not plain.strip():
        return None
    return Lyrics(synced=synced, plain=plain)


class LyricsClient(BaseClient):
    def __init__(self) -> None:
        super().__init__("https://lrclib.net/api", timeout=(5, 10))

    def find(self, title: str, artist: str, album: str = "", duration_seconds: int = 0) -> Lyrics:
        """Never raises for 'no lyrics'; raises ApiError only if the service itself fails."""
        exact = self._get_exact(title, artist, album, duration_seconds)
        if exact is not None and exact.has_synced:
            return exact
        searched = self._search(title, artist, duration_seconds)
        best = searched if searched is not None and (exact is None or searched.has_synced) else exact
        return best or Lyrics()

    def _get_exact(self, title: str, artist: str, album: str, duration_seconds: int) -> Optional[Lyrics]:
        params = {"track_name": title, "artist_name": artist}
        if album:
            params["album_name"] = album
        if duration_seconds:
            params["duration"] = duration_seconds
        try:
            return _lyrics_from(self.get_json("get", params))
        except ApiError as exc:
            if str(exc) == "Not found.":
                return None
            raise

    def _search(self, title: str, artist: str, duration_seconds: int) -> Optional[Lyrics]:
        data = self.get_json("search", {"track_name": title, "artist_name": artist})
        if not isinstance(data, list):
            return None
        candidates = [entry for entry in data if isinstance(entry, dict)]
        if duration_seconds:
            close = [e for e in candidates if isinstance(e.get("duration"), (int, float))
                     and abs(e["duration"] - duration_seconds) <= _DURATION_TOLERANCE_SECONDS]
            candidates = close or candidates
        parsed = [lyrics for lyrics in (_lyrics_from(entry) for entry in candidates) if lyrics]
        synced = [lyrics for lyrics in parsed if lyrics.has_synced]
        return (synced or parsed or [None])[0]
