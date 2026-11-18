"""yt-dlp audio and video resolver: finds playable stream URLs and searches YouTube.

Only normal, public extraction is used. Nothing here bypasses DRM, paywalls,
logins or other access controls: if yt-dlp cannot get a stream, we raise MediaSourceError.

Stream URL caching
------------------
YouTube CDN URLs expire after ~6 hours.  We cache resolved video URLs in memory for
4 hours so that opening the same movie a second time (or resuming after a brief
interruption) skips the yt-dlp resolution call entirely.
"""
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import MediaSourceError
from utils.logger import get_logger

logger = get_logger("ytdlp")

_SEARCH_COUNT = 5
_MOVIE_SEARCH_COUNT = 10
_MAX_SENSIBLE_SECONDS = 900
_UNWANTED_WORDS = ("live", "cover", "remix", "karaoke", "reaction", "slowed", "sped up", "8d", "instrumental")
_TRAILER_WORDS = ("trailer", "teaser", "clip", "review", "recap", "reaction", "behind the scenes",
                  "interview", "explained", "ending explained", "deleted scene", "bloopers",
                  "soundtrack", "ost", "theme song", "commentary", "music video", "mv",
                  "scene", "scenes", "moments", "compilation", "featurette", "promo",
                  "tv spot", "analysis", "breakdown", "summary")
_BASE_OPTIONS: Dict[str, Any] = {
    "quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True,
    "socket_timeout": 15, "retries": 2, "extractor_retries": 2,
}

# In-memory stream URL cache: video_id → (ResolvedVideo, expiry_timestamp)
_STREAM_CACHE: Dict[str, Tuple["ResolvedVideo", float]] = {}
_STREAM_CACHE_LOCK = threading.Lock()
_STREAM_CACHE_TTL = 4 * 3600  # 4 hours in seconds

# In-memory audio URL cache: (artist, title) → (ResolvedAudio, expiry_timestamp)
_AUDIO_CACHE: Dict[Tuple[str, str], Tuple["ResolvedAudio", float]] = {}
_AUDIO_CACHE_LOCK = threading.Lock()

# In-flight deduplication locks per key so double-clicks don't spawn duplicate yt-dlp calls
_INFLIGHT_VIDEO_LOCKS: Dict[str, threading.Lock] = {}
_INFLIGHT_VIDEO_GUARD = threading.Lock()


@dataclass(frozen=True)
class ResolvedAudio:
    url: str
    user_agent: str = ""
    title: str = ""
    duration_seconds: int = 0


@dataclass(frozen=True)
class ResolvedVideo:
    url: str                  # video stream URL (may be video-only DASH)
    audio_url: str = ""       # separate audio stream URL when video is DASH-only
    user_agent: str = ""
    has_audio: bool = True    # True when audio_url is set OR url contains audio


@dataclass(frozen=True)
class YouTubeSearchResult:
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    duration_seconds: int
    description: str
    thumbnail_url: str
    upload_date: str


def _pick_best(entries: List[Any], title: str, duration_seconds: int) -> Optional[dict]:
    """Choose the result closest to the song length, avoiding live, cover and remix uploads."""
    usable = [e for e in entries if isinstance(e, dict) and e.get("id") and e.get("live_status") != "is_live"]
    if not usable:
        return None
    wanted = title.lower()

    def penalty(entry: dict) -> float:
        value, length = 0.0, entry.get("duration")
        if isinstance(length, (int, float)):
            if duration_seconds:
                value += abs(length - duration_seconds)
            if length > _MAX_SENSIBLE_SECONDS:
                value += 200
        elif duration_seconds:
            value += 60
        name = str(entry.get("title") or "").lower()
        value += sum(40 for word in _UNWANTED_WORDS if word in name and word not in wanted)
        return value

    return min(usable, key=penalty)


def _stream_from(info: dict) -> Optional[ResolvedAudio]:
    url = info.get("url")
    if not (isinstance(url, str) and url.startswith("http")):
        audio_formats = [f for f in info.get("formats") or []
                         if isinstance(f, dict) and f.get("vcodec") == "none"
                         and isinstance(f.get("url"), str) and f["url"].startswith("http")]
        if not audio_formats:
            return None
        url = audio_formats[-1]["url"]
    headers = info.get("http_headers") if isinstance(info.get("http_headers"), dict) else {}
    duration = info.get("duration")
    return ResolvedAudio(url=url, user_agent=str(headers.get("User-Agent", "")),
                         title=str(info.get("title") or ""), duration_seconds=int(duration) if duration else 0)


class YtDlpClient:
    def search_official_channels(self, channel_ids: List[str], query: str, count: int = 20,
                                 min_duration_minutes: int = 60) -> List[YouTubeSearchResult]:
        """
        Get recent uploads from official movie channels.
        Fast and reliable - these channels only post full-length movies.
        """
        try:
            import yt_dlp
        except ImportError:
            return []

        min_seconds = min_duration_minutes * 60
        results: List[YouTubeSearchResult] = []
        seen_ids: set = set()

        # Get recent uploads from each official channel
        for channel_id in channel_ids:
            if len(results) >= count:
                break
            
            try:
                # Fetch recent uploads from this channel's uploads playlist
                channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
                
                with yt_dlp.YoutubeDL({**_BASE_OPTIONS, "extract_flat": "in_playlist", "playlistend": 20}) as ydl:
                    info = ydl.extract_info(channel_url, download=False)
                
                entries = info.get("entries") if isinstance(info, dict) else None
                if not entries:
                    continue

                for entry in entries:
                    if len(results) >= count:
                        break
                        
                    if not isinstance(entry, dict):
                        continue
                    
                    video_id = entry.get("id") or str(entry.get("url") or "").split("=")[-1]
                    raw_title = str(entry.get("title") or "")
                    video_title = raw_title.lower()
                    duration = entry.get("duration")

                    if not video_id or not duration:
                        continue

                    if duration < min_seconds or duration > 240 * 60:
                        continue

                    if any(word in video_title for word in _TRAILER_WORDS):
                        continue

                    if query and len(query) > 2:
                        query_lower = query.lower()
                        if query_lower not in video_title:
                            continue

                    thumbs = entry.get("thumbnails") if isinstance(entry.get("thumbnails"), list) else []
                    thumb_url = str(
                        entry.get("thumbnail")
                        or (thumbs[-1].get("url", "") if thumbs and isinstance(thumbs[-1], dict) else "")
                    )
                    channel_name = str(
                        entry.get("channel") or entry.get("uploader")
                        or info.get("channel") or info.get("uploader") or info.get("title") or ""
                    )

                    seen_ids.add(video_id)
                    results.append(YouTubeSearchResult(
                        video_id=video_id,
                        title=raw_title,
                        channel_name=channel_name,
                        channel_id=str(entry.get("channel_id") or channel_id),
                        duration_seconds=int(duration),
                        description=str(entry.get("description") or ""),
                        thumbnail_url=thumb_url,
                        upload_date=str(entry.get("upload_date") or ""),
                    ))

            except Exception as exc:  # noqa: BLE001
                logger.warning("Channel %s fetch failed: %s", channel_id, exc)
                continue

        logger.info("Found %d movies from %d official channels", len(results), len(channel_ids))
        return results

    def search_youtube_movies(self, title: str, year: int, min_duration_minutes: int = 60) -> List[YouTubeSearchResult]:
        """Search YouTube for full-length movie uploads. Returns metadata only, no stream extraction."""
        try:
            import yt_dlp
        except ImportError:
            return []
        
        queries = [
            f"{title} {year} full movie",
            f"{title} full movie {year}",
            f"{title} complete film {year}",
        ]
        
        all_results = []
        min_seconds = min_duration_minutes * 60
        
        for query in queries:
            try:
                with yt_dlp.YoutubeDL({**_BASE_OPTIONS, "extract_flat": "in_playlist"}) as searcher:
                    found = searcher.extract_info(f"ytsearch{_MOVIE_SEARCH_COUNT}:{query}", download=False)
                entries = found.get("entries") if isinstance(found, dict) else None
                if not entries:
                    continue
                
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    
                    video_id = entry.get("id")
                    video_title = str(entry.get("title") or "").lower()
                    duration = entry.get("duration")
                    
                    if not video_id or not duration:
                        continue
                    
                    # Filter by duration (must be feature-length)
                    if duration < min_seconds:
                        continue
                    
                    # Reject very long videos (>4 hours likely compilations/marathons)
                    if duration > 240 * 60:
                        continue
                    
                    # Filter trailers and clips (more strict)
                    if any(word in video_title for word in _TRAILER_WORDS):
                        continue
                    
                    # Require movie indicators in title for better accuracy
                    has_movie_indicator = any(
                        indicator in video_title
                        for indicator in ("full movie", "full length", "complete movie", "full film",
                                         "complete film", "película completa", "filme completo")
                    )
                    
                    # If duration is > 90 minutes and title matches the search, allow it
                    # even without explicit movie indicators (some official uploads don't have them)
                    title_lower = title.lower()
                    title_words = set(re.findall(r'\w+', title_lower))
                    video_words = set(re.findall(r'\w+', video_title))
                    title_overlap = len(title_words & video_words) / len(title_words) if title_words else 0
                    
                    if not has_movie_indicator and not (duration >= 90 * 60 and title_overlap >= 0.7):
                        continue
                    
                    # Skip if already in results
                    if any(r.video_id == video_id for r in all_results):
                        continue
                    
                    result = YouTubeSearchResult(
                        video_id=video_id,
                        title=str(entry.get("title") or ""),
                        channel_name=str(entry.get("channel") or entry.get("uploader") or ""),
                        channel_id=str(entry.get("channel_id") or ""),
                        duration_seconds=int(duration),
                        description=str(entry.get("description") or ""),
                        thumbnail_url=str(entry.get("thumbnail") or ""),
                        upload_date=str(entry.get("upload_date") or ""),
                    )
                    all_results.append(result)
                    
            except Exception as exc:  # noqa: BLE001
                logger.warning("YouTube search failed for '%s': %s", query, exc)
                continue
        
        return all_results

    def get_video_info(self, video_id: str) -> Optional[YouTubeSearchResult]:
        """Fetch metadata for a single YouTube video ID without extracting streams."""
        try:
            import yt_dlp
        except ImportError:
            return None
        yt_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL({**_BASE_OPTIONS}) as ydl:
                info = ydl.extract_info(yt_url, download=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch metadata for %s: %s", video_id, exc)
            return None
        if not isinstance(info, dict):
            return None
        thumbs = info.get("thumbnails") if isinstance(info.get("thumbnails"), list) else []
        thumb_url = str(
            info.get("thumbnail")
            or (thumbs[-1].get("url", "") if thumbs and isinstance(thumbs[-1], dict) else "")
        )
        return YouTubeSearchResult(
            video_id=str(info.get("id") or video_id),
            title=str(info.get("title") or ""),
            channel_name=str(info.get("channel") or info.get("uploader") or ""),
            channel_id=str(info.get("channel_id") or ""),
            duration_seconds=int(info.get("duration") or 0),
            description=str(info.get("description") or ""),
            thumbnail_url=thumb_url,
            upload_date=str(info.get("upload_date") or ""),
        )

    def resolve_video(self, source: str) -> "ResolvedVideo":
        """Extract video + audio stream URLs for VLC from a YouTube video ID or http(s) URL.

        Results are cached in memory for 4 hours so replaying or resuming
        a movie skips the yt-dlp network call entirely.
        """
        source = (source or "").strip()
        if not source:
            raise MediaSourceError("No video source provided.")

        if "://" in source and not source.startswith(("http://", "https://")):
            raise MediaSourceError("Only http:// and https:// links are supported.")

        cache_key = source
        with _INFLIGHT_VIDEO_GUARD:
            key_lock = _INFLIGHT_VIDEO_LOCKS.setdefault(cache_key, threading.Lock())

        with key_lock:
            return self._resolve_video_locked(source, cache_key)

    def _resolve_video_locked(self, source: str, cache_key: str) -> "ResolvedVideo":
        with _STREAM_CACHE_LOCK:
            cached = _STREAM_CACHE.get(cache_key)
            if cached is not None:
                resolved, expiry = cached
                if time.time() < expiry:
                    logger.debug("Stream cache hit for %s", cache_key)
                    return resolved
                del _STREAM_CACHE[cache_key]
        try:
            import yt_dlp
        except ImportError as exc:
            raise MediaSourceError("yt-dlp is not installed.") from exc

        target_url = source if source.startswith(("http://", "https://")) else f"https://www.youtube.com/watch?v={source}"
        opts = {**_BASE_OPTIONS}  # no "format" key — avoids format-not-available errors

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
        except Exception as exc:  # noqa: BLE001
            raise MediaSourceError(f"Could not fetch video info: {exc}") from exc

        if not isinstance(info, dict):
            raise MediaSourceError("yt-dlp returned no video information.")

        formats: list = info.get("formats") or []
        top_headers: dict = info.get("http_headers") or {}
        default_ua = str(top_headers.get("User-Agent", ""))

        def _is_direct(f: dict) -> bool:
            """Only accept direct https streams — skip HLS/DASH manifests."""
            proto = f.get("protocol") or ""
            url = f.get("url") or ""
            return (
                proto in ("https", "http", "")
                and isinstance(url, str)
                and url.startswith("http")
                and "manifest" not in url
                and proto != "m3u8_native"
                and proto != "m3u8"
            )

        def _vcodec(f: dict) -> str:
            return (f.get("vcodec") or "").strip()

        def _acodec(f: dict) -> str:
            return (f.get("acodec") or "").strip()

        # --- Video-only direct streams ---
        video_streams = [
            f for f in formats
            if isinstance(f, dict)
            and _vcodec(f) not in ("", "none")
            and _acodec(f) in ("", "none")
            and _is_direct(f)
        ]

        # --- Audio-only direct streams ---
        audio_streams = [
            f for f in formats
            if isinstance(f, dict)
            and _acodec(f) not in ("", "none")
            and _vcodec(f) in ("", "none")
            and _is_direct(f)
        ]

        # --- Combined streams (video+audio in one) ---
        combined_streams = [
            f for f in formats
            if isinstance(f, dict)
            and _vcodec(f) not in ("", "none")
            and _acodec(f) not in ("", "none")
            and _is_direct(f)
        ]

        # Best video: H.264 mp4 ≤720p first (most VLC-compatible), then highest res
        def _video_score(f: dict):
            height = f.get("height") or 0
            is_h264 = "avc" in _vcodec(f)
            is_mp4 = f.get("ext") == "mp4"
            # prefer H.264 mp4, closest to 720p
            return (
                0 if (is_h264 and is_mp4) else (1 if is_mp4 else 2),
                abs(height - 720),
            )

        # Best audio: AAC m4a first (most VLC-compatible)
        def _audio_score(f: dict):
            is_aac = "mp4a" in _acodec(f)
            is_m4a = f.get("ext") == "m4a"
            tbr = -(f.get("tbr") or 0)
            return (0 if (is_aac and is_m4a) else (1 if is_m4a else 2), tbr)

        def _combined_score(f: dict):
            height = f.get("height") or 0
            tbr = -(f.get("tbr") or 0)
            is_mp4 = f.get("ext") == "mp4"
            # prefer mp4, closest to 720p, highest bitrate
            return (0 if is_mp4 else 1, abs(height - 720), tbr)

        # Try DASH (separate video+audio) first — best quality
        if video_streams and audio_streams:
            video_streams.sort(key=_video_score)
            audio_streams.sort(key=_audio_score)

            best_v = video_streams[0]
            best_a = audio_streams[0]
            v_ua = str((best_v.get("http_headers") or {}).get("User-Agent", default_ua))

            logger.info(
                "Resolved DASH for %s — video: id=%s ext=%s %sp codec=%s | audio: id=%s ext=%s codec=%s",
                cache_key,
                best_v.get("format_id"), best_v.get("ext"), best_v.get("height"), _vcodec(best_v),
                best_a.get("format_id"), best_a.get("ext"), _acodec(best_a),
            )

            result = ResolvedVideo(
                url=best_v["url"],
                audio_url=best_a["url"],
                user_agent=v_ua,
                has_audio=True,
            )
            _cache_stream(cache_key, result)
            return result

        # Fallback: combined stream (video+audio in one)
        if combined_streams:
            combined_streams.sort(key=_combined_score)
            best = combined_streams[0]
            ua = str((best.get("http_headers") or {}).get("User-Agent", default_ua))

            logger.info(
                "Resolved combined stream for %s — id=%s ext=%s %sp vcodec=%s acodec=%s",
                cache_key,
                best.get("format_id"), best.get("ext"), best.get("height"),
                _vcodec(best), _acodec(best),
            )

            result = ResolvedVideo(
                url=best["url"],
                audio_url="",  # no separate audio needed
                user_agent=ua,
                has_audio=True,
            )
            _cache_stream(cache_key, result)
            return result

        # Single-URL fallback (e.g. direct video file or non-YouTube extractor)
        direct_url = info.get("url")
        if isinstance(direct_url, str) and direct_url.startswith("http"):
            result = ResolvedVideo(
                url=direct_url,
                audio_url="",
                user_agent=default_ua,
                has_audio=True,
            )
            _cache_stream(cache_key, result)
            return result

        # No suitable format found
        raise MediaSourceError(
            "No compatible video format found. This video may be restricted or unavailable."
        )

    def resolve_audio(self, artist: str, title: str, duration_seconds: int = 0) -> ResolvedAudio:
        """Search '<artist> <title> audio' and return a stream URL. Raises MediaSourceError on any failure."""
        cache_key = (artist.strip().lower(), title.strip().lower())
        with _AUDIO_CACHE_LOCK:
            cached = _AUDIO_CACHE.get(cache_key)
            if cached is not None:
                resolved, expiry = cached
                if time.time() < expiry:
                    logger.debug("Audio cache hit for %s - %s", artist, title)
                    return resolved
                del _AUDIO_CACHE[cache_key]

        try:
            import yt_dlp
        except ImportError as exc:
            raise MediaSourceError("yt-dlp is not installed.") from exc
        query = f"{artist} {title} audio"
        try:
            with yt_dlp.YoutubeDL({**_BASE_OPTIONS, "extract_flat": True}) as search:
                found = search.extract_info(f"ytsearch{_SEARCH_COUNT}:{query}", download=False)
            entries = found.get("entries") if isinstance(found, dict) else None
            best = _pick_best(entries or [], title, duration_seconds)
            if best is None:
                raise MediaSourceError("No audio source was found for this song.")
            page = best.get("url") if str(best.get("url", "")).startswith("http") else \
                f"https://www.youtube.com/watch?v={best['id']}"
            with yt_dlp.YoutubeDL({**_BASE_OPTIONS, "format": "bestaudio/best"}) as extractor:
                info = extractor.extract_info(page, download=False)
        except MediaSourceError:
            raise
        except Exception as exc:  # noqa: BLE001 - yt-dlp raises many error types
            logger.warning("yt-dlp failed for '%s': %s", query, type(exc).__name__)
            raise MediaSourceError("Could not get a playable source for this song.") from exc
        resolved = _stream_from(info) if isinstance(info, dict) else None
        if resolved is None:
            raise MediaSourceError("No playable audio stream was found.")
        with _AUDIO_CACHE_LOCK:
            _AUDIO_CACHE[cache_key] = (resolved, time.time() + _STREAM_CACHE_TTL)
        return resolved

def _cache_stream(video_id: str, resolved: "ResolvedVideo") -> None:
    """Store a resolved stream URL in the in-memory cache."""
    with _STREAM_CACHE_LOCK:
        _STREAM_CACHE[video_id] = (resolved, time.time() + _STREAM_CACHE_TTL)
