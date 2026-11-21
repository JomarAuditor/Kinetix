"""YouTube Data API v3 client for discovering full-length movie uploads.

This client uses the official YouTube Data API to search for and retrieve video information.
It does NOT extract video streams - that's handled by yt-dlp when authorized.

API Documentation: https://developers.google.com/youtube/v3/docs
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from config import settings
from core.exceptions import ApiError, MissingApiKeyError
from integrations.api.base_client import BaseClient
from utils.logger import get_logger

logger = get_logger("youtube_api")

# Minimum duration in seconds to be considered a full movie (60 minutes)
MIN_MOVIE_DURATION = 3600

# Keywords that indicate trailers or non-movie content
EXCLUDE_KEYWORDS = (
    "trailer", "teaser", "clip", "scene", "review", "reaction", "recap",
    "behind the scenes", "interview", "explained", "ending", "shorts",
    "preview", "promo", "ad", "commercial", "highlight"
)


@dataclass(frozen=True)
class YouTubeVideo:
    """YouTube video metadata from the Data API."""
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    duration_seconds: int
    thumbnail_url: str
    upload_date: str  # ISO 8601 format
    description: str
    view_count: Optional[int]
    video_url: str
    is_embeddable: bool


class YouTubeClient(BaseClient):
    """YouTube Data API v3 client."""
    
    def __init__(self) -> None:
        super().__init__("https://www.googleapis.com/youtube/v3")
        self._key: Optional[str] = None

    def _get_key(self) -> str:
        """Get YouTube API key from settings."""
        if self._key is None:
            self._key = settings.get_youtube_api_key()
            if not self._key:
                raise MissingApiKeyError("YOUTUBE_API_KEY is not set in .env.")
        return self._key

    def search_movies(self, movie_title: str, year: str = "", max_results: int = 10) -> List[YouTubeVideo]:
        """Search for full-length movie uploads on YouTube.
        
        Args:
            movie_title: The movie title to search for
            year: Optional release year to narrow results
            max_results: Maximum number of results to return (1-50)
            
        Returns:
            List of YouTubeVideo objects matching the search
            
        Raises:
            MissingApiKeyError: If YOUTUBE_API_KEY is not configured
            ApiError: If the API request fails
        """
        key = self._get_key()
        
        # Build search query
        search_terms = [movie_title, "full movie"]
        if year:
            search_terms.append(year)
        query = " ".join(search_terms)
        
        # Search parameters
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "long",  # Only long videos (> 20 minutes)
            "videoEmbeddable": "true",  # Only embeddable videos
            "videoSyndicated": "true",  # Only videos that can be played outside YouTube
            "maxResults": min(max_results, 50),
            "key": key,
            "order": "relevance"
        }
        
        try:
            data = self.get_json("search", params)
        except ApiError:
            raise
        
        if not isinstance(data, dict) or "items" not in data:
            raise ApiError("YouTube API returned an unexpected response.")
        
        items = data.get("items", [])
        if not items:
            return []
        
        # Get video IDs for detailed information
        video_ids = [item["id"]["videoId"] for item in items if isinstance(item, dict) and "id" in item]
        
        if not video_ids:
            return []
        
        # Get video details including duration
        videos = self._get_video_details(video_ids)
        
        # Filter results
        filtered = []
        for video in videos:
            # Check duration (at least 60 minutes for full movies)
            if video.duration_seconds < MIN_MOVIE_DURATION:
                logger.debug(f"Filtered out '{video.title}' - too short ({video.duration_seconds}s)")
                continue
            
            # Check for excluded keywords in title
            title_lower = video.title.lower()
            if any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS):
                logger.debug(f"Filtered out '{video.title}' - contains excluded keyword")
                continue
            
            filtered.append(video)
        
        return filtered

    def _get_video_details(self, video_ids: List[str]) -> List[YouTubeVideo]:
        """Get detailed information for specific video IDs.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of YouTubeVideo objects with full details
        """
        if not video_ids:
            return []
        
        key = self._get_key()
        
        params = {
            "part": "snippet,contentDetails,statistics,status",
            "id": ",".join(video_ids[:50]),  # API limit is 50 IDs per request
            "key": key
        }
        
        try:
            data = self.get_json("videos", params)
        except ApiError:
            raise
        
        if not isinstance(data, dict) or "items" not in data:
            return []
        
        videos = []
        for item in data.get("items", []):
            try:
                video = self._parse_video(item)
                if video:
                    videos.append(video)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to parse video: {exc}")
                continue
        
        return videos

    def _parse_video(self, item: dict) -> Optional[YouTubeVideo]:
        """Parse a video item from the API response."""
        try:
            video_id = item["id"]
            snippet = item["snippet"]
            content_details = item["contentDetails"]
            statistics = item.get("statistics", {})
            status = item.get("status", {})
            
            # Parse duration from ISO 8601 format (PT1H2M10S)
            duration = self._parse_duration(content_details["duration"])
            
            # Get thumbnail URL (prefer high quality)
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url") or
                thumbnails.get("medium", {}).get("url") or
                thumbnails.get("default", {}).get("url") or
                ""
            )
            
            # Parse view count
            view_count = None
            if "viewCount" in statistics:
                try:
                    view_count = int(statistics["viewCount"])
                except (ValueError, TypeError):
                    pass
            
            # Check if embeddable
            is_embeddable = status.get("embeddable", True)
            
            return YouTubeVideo(
                video_id=video_id,
                title=snippet.get("title", ""),
                channel_name=snippet.get("channelTitle", ""),
                channel_id=snippet.get("channelId", ""),
                duration_seconds=duration,
                thumbnail_url=thumbnail_url,
                upload_date=snippet.get("publishedAt", ""),
                description=snippet.get("description", ""),
                view_count=view_count,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                is_embeddable=is_embeddable
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"Failed to parse video item: {exc}")
            return None

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds.
        
        Example: PT1H2M10S -> 3730 seconds
        """
        import re
        
        # Remove PT prefix
        duration_str = duration_str.replace("PT", "")
        
        # Extract hours, minutes, seconds
        hours = 0
        minutes = 0
        seconds = 0
        
        hour_match = re.search(r"(\d+)H", duration_str)
        if hour_match:
            hours = int(hour_match.group(1))
        
        minute_match = re.search(r"(\d+)M", duration_str)
        if minute_match:
            minutes = int(minute_match.group(1))
        
        second_match = re.search(r"(\d+)S", duration_str)
        if second_match:
            seconds = int(second_match.group(1))
        
        return hours * 3600 + minutes * 60 + seconds

    def get_video_by_id(self, video_id: str) -> Optional[YouTubeVideo]:
        """Get detailed information for a single video by ID.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            YouTubeVideo object or None if not found
        """
        videos = self._get_video_details([video_id])
        return videos[0] if videos else None
