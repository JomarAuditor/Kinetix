"""Movie matching: compare TMDB movies to YouTube videos, and verify source rights."""
import json
import re
from typing import Dict, List, Optional, Tuple

from config import settings
from config.movie_channels import get_all_channel_ids
from models.movie import MatchConfidence, Movie, RightsStatus, YouTubeVideo
from utils.logger import get_logger

logger = get_logger("movie_matching")

_TITLE_MATCH_THRESHOLD = 0.75
_YEAR_TOLERANCE = 1       # ±1 year from TMDB release year
_DURATION_TOLERANCE = 0.25  # ±25% of TMDB runtime is acceptable

# These words in a YouTube title disqualify it as a full-length movie
_REJECT_WORDS = (
    "trailer", "teaser", "clip", "scene", "review", "reaction",
    "recap", "summary", "explained", "analysis", "breakdown",
    "behind the scenes", "making of", "deleted scene", "bloopers",
    "interview", "featurette", "promo", "tv spot", "music video",
    "official video", "lyric video", "short film", "short movie",
    "compilation", "best moments", "funny moments", "top scenes",
)


class MovieMatchingService:
    """Matches TMDB movies to YouTube videos and verifies source rights."""

    def __init__(self) -> None:
        self._sources = self._load_sources()

    def _load_sources(self) -> dict:
        try:
            path = settings.MOVIE_SOURCES_PATH
            if path.exists():
                with open(path, encoding="utf-8") as file:
                    return json.load(file)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load movie_sources.json: %s", exc)
        return {"verified_channels": [], "blocked_channels": [], "public_domain": []}

    def match_movie(self, movie: Movie, video: YouTubeVideo) -> Tuple[MatchConfidence, str]:
        """
        Match a TMDB movie to a YouTube video.
        Returns (confidence, reason).

        Scoring:
        - Hard reject: title reject words, or title score < 0.5
        - STRONG:   title ≥ 0.75  AND  (year match OR duration match)
        - POSSIBLE: title ≥ 0.60  AND  duration in range (year might be absent)
        - WEAK:     title ≥ 0.50
        - REJECTED: everything else
        """
        video_title_lower = video.title.lower()

        # Hard reject: trailer/clip/review words
        if any(w in video_title_lower for w in _REJECT_WORDS):
            return MatchConfidence.REJECTED, f"Rejected: title contains disqualifying word"

        # Title similarity
        title_score = self._title_similarity(movie.title, video.title)
        orig_score = self._title_similarity(movie.original_title, video.title)
        best_score = max(title_score, orig_score)

        if best_score < 0.50:
            return MatchConfidence.REJECTED, f"Title mismatch (score {best_score:.0%})"

        # Year check — from title and description
        year_in_title = self._extract_year(video.title)
        year_in_desc = self._extract_year(video.description[:300]) if video.description else 0
        year_found = year_in_title or year_in_desc
        year_match = (
            abs(year_found - movie.release_year) <= _YEAR_TOLERANCE
            if year_found else False
        )

        # Duration check
        video_minutes = video.duration_seconds // 60
        duration_match = True
        if movie.runtime > 0 and video_minutes > 0:
            diff = abs(video_minutes - movie.runtime) / movie.runtime
            duration_match = diff <= _DURATION_TOLERANCE

        # Confidence decision
        if best_score >= _TITLE_MATCH_THRESHOLD and (year_match or duration_match):
            reason = (
                f"Title {best_score:.0%}, year={movie.release_year}"
                f"{' ✓' if year_match else ''}, "
                f"duration={video_minutes}min"
                f"{' ✓' if duration_match else ''}"
            )
            return MatchConfidence.STRONG, reason

        if best_score >= 0.60 and duration_match:
            return (
                MatchConfidence.POSSIBLE,
                f"Title {best_score:.0%}, duration {video_minutes}min matches runtime"
            )

        if best_score >= 0.50:
            return MatchConfidence.WEAK, f"Weak title match {best_score:.0%}"

        return MatchConfidence.REJECTED, f"No reliable match (score {best_score:.0%})"

    def check_rights(self, movie: Movie, video: YouTubeVideo) -> Tuple[RightsStatus, str]:
        """Check source registry (blocked/verified/public domain). Default UNVERIFIED."""
        blocked = self._sources.get("blocked_channels", [])
        for block in blocked:
            if isinstance(block, dict) and block.get("channel_id") == video.channel_id:
                return RightsStatus.BLOCKED, block.get("reason", "Blocked channel")

        verified = self._sources.get("verified_channels", [])
        for channel in verified:
            if isinstance(channel, dict) and channel.get("channel_id") == video.channel_id:
                return RightsStatus.VERIFIED, channel.get("reason", "Verified distributor channel")

        if video.channel_id and video.channel_id in get_all_channel_ids():
            return RightsStatus.VERIFIED, "Official YouTube movie channel"

        public_domain = self._sources.get("public_domain", [])
        for pd in public_domain:
            if isinstance(pd, dict) and pd.get("tmdb_id") == movie.tmdb_id:
                youtube_id = pd.get("youtube_id")
                if not youtube_id or youtube_id == video.video_id:
                    return RightsStatus.VERIFIED, pd.get("reason", "Public domain")

        return RightsStatus.UNVERIFIED, "Unverified source"

    @staticmethod
    def _title_similarity(title1: str, title2: str) -> float:
        """Jaccard word similarity after normalising both titles."""
        def normalize(text: str) -> str:
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            # Remove noise words added by YouTube uploaders
            noise = (
                'the', 'a', 'an',
                'full', 'movie', 'film', 'complete', 'hd', '4k', '1080p', '720p',
                'free', 'watch', 'online', 'english', 'subtitles', 'dubbed',
                'official', 'original', 'remastered', 'extended', 'cut',
            )
            for w in noise:
                text = re.sub(rf'\b{w}\b', ' ', text)
            return re.sub(r'\s+', ' ', text).strip()

        n1 = normalize(title1)
        n2 = normalize(title2)
        if not n1 or not n2:
            return 0.0

        # Substring bonus
        if n1 in n2 or n2 in n1:
            return 0.90

        w1 = set(n1.split())
        w2 = set(n2.split())
        if not w1 or not w2:
            return 0.0

        return len(w1 & w2) / len(w1 | w2)

    @staticmethod
    def _extract_year(text: str) -> int:
        """Return the first plausible 4-digit movie year found in text."""
        matches = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', text)
        return int(matches[0]) if matches else 0
