"""Movie models: Movie (from TMDB), YouTubeVideo (from yt-dlp), MatchedMovie (combined)."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config.constants import MEDIA_MOVIE
from models.media import MediaItem


class MatchConfidence(Enum):
    STRONG = "strong"
    POSSIBLE = "possible"
    WEAK = "weak"
    REJECTED = "rejected"


class RightsStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Movie:
    """TMDB movie metadata."""
    tmdb_id: int
    title: str
    original_title: str
    release_year: int
    poster_url: str
    backdrop_url: str
    overview: str
    genres: str
    rating: float
    runtime: int  # minutes

    def to_media_item(self) -> MediaItem:
        subtitle = " • ".join(part for part in (self.genres, str(self.release_year)) if part)
        return MediaItem(
            media_type=MEDIA_MOVIE,
            external_id=str(self.tmdb_id),
            title=self.title,
            subtitle=subtitle,
            image_url=self.poster_url,
        )


@dataclass(frozen=True)
class YouTubeVideo:
    """YouTube video metadata from yt-dlp."""
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    duration_seconds: int
    description: str
    thumbnail_url: str
    upload_date: str


@dataclass(frozen=True)
class MatchedMovie:
    """A TMDB movie matched to a YouTube video."""
    movie: Movie
    video: Optional[YouTubeVideo]
    match_confidence: MatchConfidence
    match_reason: str
    rights_status: RightsStatus
    rights_reason: str
    playable: bool

    @property
    def duration_minutes(self) -> int:
        return self.video.duration_seconds // 60 if self.video else 0

    @property
    def is_verified(self) -> bool:
        return self.rights_status == RightsStatus.VERIFIED

    @property
    def external_key(self) -> str:
        if self.movie.tmdb_id > 0:
            return str(self.movie.tmdb_id)
        if self.video is not None:
            return f"yt:{self.video.video_id}"
        return self.movie.title

    @property
    def is_playable(self) -> bool:
        return (
            self.playable
            and self.video is not None
            and self.rights_status == RightsStatus.VERIFIED
            and self.match_confidence in (MatchConfidence.STRONG, MatchConfidence.POSSIBLE)
        )

    def to_media_item(self) -> MediaItem:
        if self.movie.tmdb_id > 0:
            return self.movie.to_media_item()
        channel = self.video.channel_name if self.video else ""
        parts = [p for p in (channel, str(self.movie.release_year or "") or "") if p]
        subtitle = " • ".join(parts)
        return MediaItem(
            media_type=MEDIA_MOVIE,
            external_id=self.external_key,
            title=self.movie.title,
            subtitle=subtitle,
            image_url=self.movie.poster_url,
        )
