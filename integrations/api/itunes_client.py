"""iTunes Search API (no key). Gives track info, artwork and 30-second previews."""
from typing import List, Optional

from config.constants import SEARCH_RESULT_LIMIT
from core.exceptions import ApiError
from integrations.api.base_client import BaseClient
from models.music import Track


def _upgrade_artwork(url: str) -> str:
    """iTunes sends 100x100 art; the same URL works for 300x300."""
    return url.replace("100x100", "300x300") if isinstance(url, str) else ""


def _parse_track(row) -> Optional[Track]:
    if not isinstance(row, dict) or row.get("kind") != "song":
        return None
    track_id, title, artist = row.get("trackId"), row.get("trackName"), row.get("artistName")
    if not track_id or not isinstance(title, str) or not isinstance(artist, str):
        return None
    duration = row.get("trackTimeMillis")
    return Track(
        track_id=str(track_id),
        title=title,
        artist=artist,
        album=row.get("collectionName") if isinstance(row.get("collectionName"), str) else "",
        duration_ms=duration if isinstance(duration, int) else 0,
        preview_url=row.get("previewUrl") if isinstance(row.get("previewUrl"), str) else "",
        artwork_url=_upgrade_artwork(row.get("artworkUrl100", "")),
    )


def _parse_results(data) -> List[Track]:
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        raise ApiError("The music service sent an unexpected answer.")
    tracks, seen = [], set()
    for row in results:
        track = _parse_track(row)
        if track is not None and track.track_id not in seen:
            seen.add(track.track_id)
            tracks.append(track)
    return tracks


class ItunesClient(BaseClient):
    def __init__(self) -> None:
        super().__init__("https://itunes.apple.com")

    def search_songs(self, term: str, limit: int = SEARCH_RESULT_LIMIT) -> List[Track]:
        params = {"term": term, "media": "music", "entity": "song", "limit": max(1, min(limit, 50))}
        return _parse_results(self.get_json("search", params))

    def lookup_song(self, track_id: str) -> Optional[Track]:
        tracks = _parse_results(self.get_json("lookup", {"id": track_id, "entity": "song"}))
        return tracks[0] if tracks else None
