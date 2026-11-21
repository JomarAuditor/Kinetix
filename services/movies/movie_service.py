"""Movie logic: official free YouTube movie channels + TMDB metadata + rights matching.

1. Official channels (FilmRise, Popcornflix, Movie Central, Cult Cinema Classics, etc.)
   provide verified, legal full-length free movies via yt-dlp.
2. TMDB provides movie identity, 2:3 posters, backdrops, genres, ratings, and overviews.
3. Results are cached in SQLite (movie_cache) so repeat visits load instantly.
"""
import hashlib
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from config import settings
from config.constants import MEDIA_MOVIE
from config.movie_channels import OFFICIAL_MOVIE_CHANNELS, get_channels_for_category
from core.exceptions import MissingApiKeyError
from data.repositories.movie_cache_repository import MovieCacheRepository
from integrations.api.tmdb_client import TmdbClient
from integrations.media.ytdlp_client import YtDlpClient, YouTubeSearchResult
from models.media import MediaItem
from models.movie import MatchConfidence, MatchedMovie, Movie, RightsStatus, YouTubeVideo
from services.movies.movie_matching_service import MovieMatchingService
from utils.logger import get_logger

logger = get_logger("movie_service")

_BROWSE_CACHE_HOURS = 2
_SEARCH_CACHE_HOURS = 1
_CHANNEL_WORKERS = 5
_TMDB_WORKERS = 4
_MAX_CHANNELS_PER_CATEGORY = 5


class MovieService:
    def __init__(self, client: Optional[TmdbClient] = None,
                 ytdlp: Optional[YtDlpClient] = None,
                 matcher: Optional[MovieMatchingService] = None,
                 cache: Optional[MovieCacheRepository] = None) -> None:
        self._client = client or TmdbClient()
        self._ytdlp = ytdlp or YtDlpClient()
        self._matcher = matcher or MovieMatchingService()
        self._cache = cache or MovieCacheRepository()
        self._inflight_guard = threading.Lock()
        self._discover_locks: Dict[str, threading.Lock] = {}
        self._search_locks: Dict[str, threading.Lock] = {}

    # ------------------------------------------------------------------
    # Discovery & Search
    # ------------------------------------------------------------------

    def discover_from_official_channels(self, category: str = "popular", limit: int = 12) -> List[MatchedMovie]:
        """Return recent full movies from official channels for *category*, enriched by TMDB."""
        self._client._get_key()  # raise MissingApiKeyError upfront if TMDB_API_KEY is missing

        cache_key = f"discover_v3:{category}:{limit}"
        with self._inflight_guard:
            key_lock = self._discover_locks.setdefault(cache_key, threading.Lock())

        with key_lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for '%s' (%d items)", cache_key, len(cached))
                return [_dict_to_matched(d) for d in cached]

            channels = get_channels_for_category(category)[:_MAX_CHANNELS_PER_CATEGORY]
            if not channels:
                return []

            logger.info("Fetching %d channels in parallel for '%s'", len(channels), category)
            yt_results = self._fetch_channels_parallel(
                channels, query="", limit=limit * 2,
                min_minutes=settings.get_movie_min_minutes(),
            )
            matched = self._results_to_matched_parallel(yt_results)
            # Prefer movies with TMDB metadata/backdrops first so the featured banner looks crisp
            matched.sort(key=lambda m: (0 if m.movie.tmdb_id > 0 and m.movie.backdrop_url else 1,
                                        -m.movie.rating))
            matched = _dedupe_matched(matched)[:limit]

            if matched:
                try:
                    self._cache.save(cache_key, [_matched_to_dict(m) for m in matched],
                                     expiration_hours=_BROWSE_CACHE_HOURS)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Cache write failed: %s", exc)

            return matched

    def search_official_channels(self, query: str, limit: int = 12) -> List[MatchedMovie]:
        """Search official movie channels and TMDB for *query*."""
        self._client._get_key()  # raise MissingApiKeyError upfront if TMDB_API_KEY is missing

        q_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]
        cache_key = f"search_v2:{q_hash}:{limit}"
        with self._inflight_guard:
            key_lock = self._search_locks.setdefault(cache_key, threading.Lock())

        with key_lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Search cache hit for '%s'", query)
                return [_dict_to_matched(d) for d in cached]

            # Run official-channel scrape and TMDB search concurrently
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_yt = pool.submit(
                    self._fetch_channels_parallel,
                    OFFICIAL_MOVIE_CHANNELS[:12], query, limit, settings.get_movie_min_minutes(),
                )
                f_tmdb = pool.submit(self._client.search_movies, query)
                yt_results = f_yt.result()
                try:
                    tmdb_hits = f_tmdb.result()[:6]
                except MissingApiKeyError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.debug("TMDB search failed: %s", exc)
                    tmdb_hits = []

            matched = self._results_to_matched_parallel(yt_results)
            seen_tmdb = {m.movie.tmdb_id for m in matched if m.movie.tmdb_id > 0}

            remaining_slots = max(0, limit - len(matched))
            candidates = [m for m in tmdb_hits if m.tmdb_id not in seen_tmdb][:remaining_slots]
            if candidates:
                with ThreadPoolExecutor(max_workers=min(3, len(candidates))) as pool:
                    futures = [pool.submit(self._match_tmdb_movie, m, True) for m in candidates]
                    for future in as_completed(futures):
                        try:
                            extra = future.result()
                        except Exception:  # noqa: BLE001
                            extra = None
                        if extra is not None and extra.movie.tmdb_id not in seen_tmdb:
                            matched.append(extra)
                            seen_tmdb.add(extra.movie.tmdb_id)

            if matched:
                try:
                    self._cache.save(cache_key, [_matched_to_dict(m) for m in matched],
                                     expiration_hours=_SEARCH_CACHE_HOURS)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Search cache write failed: %s", exc)

            return matched[:limit]

    def resolve_media_item(self, item: MediaItem) -> Optional[MatchedMovie]:
        """Resolve a MediaItem (from Dashboard, Favorites, or History) to a MatchedMovie."""
        if item.external_id.startswith("yt:"):
            video_id = item.external_id[3:]
            yt = self._ytdlp.get_video_info(video_id)
            if yt is None:
                return None
            return self._youtube_result_to_matched(yt)

        try:
            tmdb_id = int(item.external_id)
        except ValueError:
            return None

        movie = self._client.get_movie_details(tmdb_id)
        if movie is None:
            return None

        # 1. Check official channels for a verified free upload
        matched = self._match_tmdb_movie(movie, allow_unverified=False)
        if matched is not None:
            return matched

        # 2. Return full TMDB details with unverified/unavailable video state (allows Play from URL)
        return MatchedMovie(
            movie=movie,
            video=None,
            match_confidence=MatchConfidence.REJECTED,
            match_reason="No verified free full-length upload found.",
            rights_status=RightsStatus.UNVERIFIED,
            rights_reason="TMDB metadata only — paste an authorized URL or try another title.",
            playable=False,
        )

    def featured(self, limit: int = 5) -> List[MediaItem]:
        """Return verified playable movies from official channels for the dashboard featured strip."""
        matched = self.discover_from_official_channels("popular", limit=max(limit, 8))
        return [m.to_media_item() for m in matched[:limit]]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_tmdb_movie(self, movie: Movie, allow_unverified: bool) -> Optional[MatchedMovie]:
        """Search YouTube/official channels for a full-length match to a TMDB Movie."""
        min_minutes = settings.get_movie_min_minutes()
        candidates = self._ytdlp.search_youtube_movies(movie.title, movie.release_year, min_minutes)
        best: Optional[MatchedMovie] = None

        for yt in candidates:
            video = _yt_to_video(yt)
            confidence, reason = self._matcher.match_movie(movie, video)
            if confidence not in (MatchConfidence.STRONG, MatchConfidence.POSSIBLE):
                continue
            rights, rights_reason = self._matcher.check_rights(movie, video)
            if rights == RightsStatus.BLOCKED:
                continue
            if rights == RightsStatus.VERIFIED:
                return MatchedMovie(
                    movie=movie, video=video,
                    match_confidence=confidence, match_reason=reason,
                    rights_status=rights, rights_reason=rights_reason,
                    playable=True,
                )
            if allow_unverified and best is None:
                best = MatchedMovie(
                    movie=movie, video=video,
                    match_confidence=confidence, match_reason=reason,
                    rights_status=RightsStatus.UNVERIFIED,
                    rights_reason="Unverified uploader — direct VLC playback disabled.",
                    playable=False,
                )
        return best

    def _fetch_channels_parallel(self, channels: list, query: str,
                                  limit: int, min_minutes: int) -> List[YouTubeSearchResult]:
        per_channel = max(3, (limit + len(channels) - 1) // max(len(channels), 1))
        seen_ids: set = set()
        results: List[YouTubeSearchResult] = []
        workers = min(_CHANNEL_WORKERS, max(1, len(channels)))

        def _fetch_one(ch: dict) -> List[YouTubeSearchResult]:
            try:
                return self._ytdlp.search_official_channels(
                    channel_ids=[ch["channel_id"]],
                    query=query,
                    count=per_channel,
                    min_duration_minutes=min_minutes,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Channel %s failed: %s", ch["name"], exc)
                return []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_fetch_one, ch) for ch in channels]
            for future in as_completed(futures):
                for item in future.result():
                    if item.video_id not in seen_ids:
                        seen_ids.add(item.video_id)
                        results.append(item)
                if len(results) >= limit:
                    break

        return results[:limit]

    def _results_to_matched_parallel(self, yt_results: List[YouTubeSearchResult]) -> List[MatchedMovie]:
        if not yt_results:
            return []
        matched: List[Optional[MatchedMovie]] = [None] * len(yt_results)
        with ThreadPoolExecutor(max_workers=_TMDB_WORKERS) as pool:
            future_map = {
                pool.submit(self._youtube_result_to_matched, yt): idx
                for idx, yt in enumerate(yt_results)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    matched[idx] = future.result()
                except MissingApiKeyError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Enrichment failed: %s", exc)
        return [m for m in matched if m is not None]

    def _youtube_result_to_matched(self, yt: YouTubeSearchResult) -> MatchedMovie:
        video = _yt_to_video(yt)
        movie = self._identify_movie_from_title(yt.title, yt.duration_seconds)
        if movie is None:
            movie = _movie_from_yt(yt)
        rights, rights_reason = self._matcher.check_rights(movie, video)
        if rights == RightsStatus.UNVERIFIED:
            rights = RightsStatus.VERIFIED
            rights_reason = "Official YouTube movie channel"

        return MatchedMovie(
            movie=movie,
            video=video,
            match_confidence=MatchConfidence.STRONG,
            match_reason="From verified official movie channel",
            rights_status=rights,
            rights_reason=rights_reason,
            playable=rights == RightsStatus.VERIFIED,
        )

    def _identify_movie_from_title(self, yt_title: str, duration_seconds: int) -> Optional[Movie]:
        """Look up TMDB metadata for a YouTube title and verify similarity."""
        clean = _clean_youtube_title(yt_title)
        if len(clean) < 2:
            return None
        try:
            results = self._client.search_movies(clean)
        except MissingApiKeyError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.debug("TMDB lookup failed for '%s': %s", clean, exc)
            return None

        if not results:
            return None

        video_minutes = duration_seconds // 60
        best_movie: Optional[Movie] = None
        best_score = 0.0
        for candidate in results[:5]:
            score = self._matcher._title_similarity(candidate.title, clean)
            if score >= 0.55 and score > best_score:
                if candidate.runtime > 0 and video_minutes > 0:
                    diff = abs(video_minutes - candidate.runtime) / candidate.runtime
                    if diff > 0.35:
                        continue
                best_score = score
                best_movie = candidate
        return best_movie


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _dedupe_matched(items: List[MatchedMovie]) -> List[MatchedMovie]:
    """Remove duplicate uploads of the same movie (by TMDB id or normalized title)."""
    seen_tmdb: set = set()
    seen_titles: set = set()
    unique: List[MatchedMovie] = []
    for m in items:
        if m.movie.tmdb_id > 0:
            if m.movie.tmdb_id in seen_tmdb:
                continue
            seen_tmdb.add(m.movie.tmdb_id)
        norm = re.sub(r"[^a-z0-9]+", "", m.movie.title.lower())
        if norm:
            if norm in seen_titles:
                continue
            seen_titles.add(norm)
        unique.append(m)
    return unique


def _clean_youtube_title(yt_title: str) -> str:
    clean = re.sub(
        r"(?i)\b(full\s+movie|full\s+film|complete\s+movie|hd|4k|720p|1080p|free|"
        r"english\s+subtitles?|subtitled|dubbed|official|original|remastered)\b",
        "", yt_title,
    )
    clean = re.sub(r"[\(\[]\d{4}[\)\]]", "", clean)
    clean = re.sub(r"[-|]\s*.*$", "", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _yt_to_video(yt: YouTubeSearchResult) -> YouTubeVideo:
    return YouTubeVideo(
        video_id=yt.video_id,
        title=yt.title,
        channel_name=yt.channel_name,
        channel_id=yt.channel_id,
        duration_seconds=yt.duration_seconds,
        description=yt.description,
        thumbnail_url=yt.thumbnail_url,
        upload_date=yt.upload_date,
    )


def _movie_from_yt(yt: YouTubeSearchResult) -> Movie:
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", yt.title)
    year = int(year_match.group(1)) if year_match else 0
    title = _clean_youtube_title(yt.title)
    return Movie(
        tmdb_id=0,
        title=title or yt.title,
        original_title=title or yt.title,
        release_year=year,
        poster_url=yt.thumbnail_url,
        backdrop_url=yt.thumbnail_url,
        overview=yt.description[:500] if yt.description else "",
        genres="",
        rating=0.0,
        runtime=yt.duration_seconds // 60,
    )


# ------------------------------------------------------------------
# Cache serialization helpers
# ------------------------------------------------------------------

def _matched_to_dict(m: MatchedMovie) -> dict:
    v = m.video
    mv = m.movie
    return {
        "video": {
            "video_id": v.video_id, "title": v.title, "channel_name": v.channel_name,
            "channel_id": v.channel_id, "duration_seconds": v.duration_seconds,
            "description": v.description, "thumbnail_url": v.thumbnail_url,
            "upload_date": v.upload_date,
        } if v else None,
        "movie": {
            "tmdb_id": mv.tmdb_id, "title": mv.title, "original_title": mv.original_title,
            "release_year": mv.release_year, "poster_url": mv.poster_url,
            "backdrop_url": mv.backdrop_url, "overview": mv.overview,
            "genres": mv.genres, "rating": mv.rating, "runtime": mv.runtime,
        },
        "match_confidence": m.match_confidence.value,
        "match_reason": m.match_reason,
        "rights_status": m.rights_status.value,
        "rights_reason": m.rights_reason,
        "playable": m.playable,
    }


def _dict_to_matched(d: dict) -> MatchedMovie:
    mv_d = d["movie"]
    movie = Movie(
        tmdb_id=mv_d["tmdb_id"], title=mv_d["title"], original_title=mv_d["original_title"],
        release_year=mv_d["release_year"], poster_url=mv_d["poster_url"],
        backdrop_url=mv_d["backdrop_url"], overview=mv_d["overview"],
        genres=mv_d["genres"], rating=mv_d["rating"], runtime=mv_d["runtime"],
    )
    video: Optional[YouTubeVideo] = None
    if d.get("video"):
        v_d = d["video"]
        video = YouTubeVideo(
            video_id=v_d["video_id"], title=v_d["title"], channel_name=v_d["channel_name"],
            channel_id=v_d["channel_id"], duration_seconds=v_d["duration_seconds"],
            description=v_d["description"], thumbnail_url=v_d["thumbnail_url"],
            upload_date=v_d["upload_date"],
        )
    return MatchedMovie(
        movie=movie, video=video,
        match_confidence=MatchConfidence(d["match_confidence"]),
        match_reason=d["match_reason"],
        rights_status=RightsStatus(d["rights_status"]),
        rights_reason=d["rights_reason"],
        playable=d["playable"],
    )
