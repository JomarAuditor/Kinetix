"""Music models: Track (from iTunes) and Lyrics (from LRCLIB)."""
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import List, Tuple

from config.constants import MEDIA_MUSIC
from models.media import MediaItem
from utils.helpers import format_duration


@dataclass(frozen=True)
class Track:
    track_id: str
    title: str
    artist: str
    album: str = ""
    duration_ms: int = 0
    preview_url: str = ""
    artwork_url: str = ""

    @property
    def duration_text(self) -> str:
        return format_duration(self.duration_ms) if self.duration_ms else ""

    def to_media_item(self) -> MediaItem:
        """Shape used by favorites, history and the shared cards."""
        return MediaItem(media_type=MEDIA_MUSIC, external_id=self.track_id, title=self.title,
                         subtitle=self.artist, image_url=self.artwork_url)


@dataclass
class Lyrics:
    """synced = [(start_ms, line)] sorted by time. plain = text without timestamps."""
    synced: List[Tuple[int, str]] = field(default_factory=list)
    plain: str = ""

    @property
    def has_synced(self) -> bool:
        return bool(self.synced)

    @property
    def has_text(self) -> bool:
        return bool(self.synced or self.plain.strip())

    def line_index_at(self, position_ms: int) -> int:
        """Index of the line being sung at position_ms, or -1 before the first line."""
        times = [start for start, _ in self.synced]
        return bisect_right(times, position_ms) - 1

    def plain_lines(self) -> List[str]:
        if self.synced:
            return [text for _, text in self.synced]
        return [line.strip() for line in self.plain.splitlines() if line.strip()]
