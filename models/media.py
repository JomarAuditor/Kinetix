"""One item that can be a favorite or a history entry (music, movie or game)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaItem:
    media_type: str
    external_id: str
    title: str
    subtitle: str = ""
    image_url: str = ""
    id: Optional[int] = None
    # UTC text from SQLite: created_at for favorites, last_accessed for history.
    timestamp: str = ""
