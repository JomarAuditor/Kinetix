"""Movie playback coordination: manages VLC video player state and events."""
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from core.exceptions import MediaSourceError, PlaybackError
from integrations.media.vlc_player import VlcPlayer
from integrations.media.ytdlp_client import YtDlpClient
from models.movie import MatchedMovie
from utils.logger import get_logger

logger = get_logger("movie_playback")

EVENT_STATE = "state_changed"
EVENT_PROGRESS = "progress"
EVENT_ERROR = "error"

STATE_IDLE = "idle"
STATE_LOADING = "loading"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_ERROR = "error"


@dataclass
class PlaybackState:
    state: str = STATE_IDLE
    matched_movie: Optional[MatchedMovie] = None
    error_message: str = ""
    position_ms: int = 0
    duration_ms: int = 0


class MoviePlaybackService:
    """Manages movie playback with VLC."""

    def __init__(self, ytdlp: Optional[YtDlpClient] = None) -> None:
        self._ytdlp = ytdlp or YtDlpClient()
        self._player: Optional[VlcPlayer] = None
        self._state = PlaybackState()
        self._generation = 0
        self._subscribers: list[Callable[[str, any], None]] = []
        self._event_queue: "queue.Queue" = queue.Queue()
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state.state

    @property
    def current_movie(self) -> Optional[MatchedMovie]:
        return self._state.matched_movie

    @property
    def position_ms(self) -> int:
        return self._state.position_ms

    @property
    def duration_ms(self) -> int:
        return self._state.duration_ms

    def subscribe(self, callback: Callable[[str, any], None]) -> Callable[[], None]:
        """Subscribe to events. Returns an unsubscribe function."""
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback) if callback in self._subscribers else None

    def _notify(self, event: str, payload=None) -> None:
        for callback in self._subscribers[:]:
            try:
                callback(event, payload)
            except Exception as exc:  # noqa: BLE001
                logger.error("Event callback error: %s", exc)

    def play_movie(self, matched_movie: MatchedMovie, hwnd=None, volume: int = 70) -> None:
        """Start playing a matched movie. Must be called from a worker thread."""
        if matched_movie.video is None:
            raise MediaSourceError("No video source available.")
        if not matched_movie.is_playable:
            raise MediaSourceError("This source is not verified for direct playback.")

        with self._lock:
            self._state = PlaybackState(state=STATE_LOADING, matched_movie=matched_movie)

        self._play_source(matched_movie.video.video_id, hwnd, volume)

    def play_url(self, url: str, hwnd=None, volume: int = 70) -> None:
        """Resolve and play a user-provided authorized URL. Must be called from a worker thread."""
        cleaned = (url or "").strip()
        if not cleaned.startswith(("http://", "https://")):
            raise MediaSourceError("Enter a valid http:// or https:// video link.")

        with self._lock:
            self._state = PlaybackState(state=STATE_LOADING, matched_movie=self._state.matched_movie)

        self._play_source(cleaned, hwnd, volume)

    def _play_source(self, source: str, hwnd, volume: int) -> None:
        resolved = self._ytdlp.resolve_video(source)

        if self._player is None:
            self._player = VlcPlayer(
                on_end=self._on_end,
                on_error=self._on_error,
                video=True,
            )
        else:
            self._player.stop()

        self._player.set_volume(volume)
        if hwnd is not None:
            self._player.set_window(hwnd)

        self._generation = self._player.load(resolved.url, resolved.user_agent, resolved.audio_url)
        self._player.play()

        with self._lock:
            self._state.state = STATE_PLAYING

    def toggle_pause(self) -> None:
        """Toggle between playing and paused."""
        if self._player is None:
            return

        with self._lock:
            if self._state.state == STATE_PLAYING:
                self._player.pause()
                self._state.state = STATE_PAUSED
                self._notify(EVENT_STATE, self._state)
            elif self._state.state == STATE_PAUSED:
                self._player.resume()
                self._state.state = STATE_PLAYING
                self._notify(EVENT_STATE, self._state)

    def stop(self) -> None:
        """Stop playback and return to idle state."""
        if self._player is not None:
            self._player.stop()
        
        with self._lock:
            self._state = PlaybackState(state=STATE_IDLE)
            self._notify(EVENT_STATE, self._state)

    def seek(self, fraction: float) -> None:
        """Seek to a position (0.0 to 1.0)."""
        if self._player is not None and self._state.state in (STATE_PLAYING, STATE_PAUSED):
            self._player.seek_fraction(fraction)
            self._update_progress()

    def seek_ms(self, milliseconds: int) -> None:
        """Seek to an absolute position in milliseconds."""
        if self._player is not None and self._state.state in (STATE_PLAYING, STATE_PAUSED):
            self._player.set_time_ms(milliseconds)
            self._update_progress()

    def set_volume(self, volume: int) -> None:
        """Set volume (0 to 100)."""
        if self._player is not None:
            self._player.set_volume(volume)

    def update_progress(self) -> None:
        """Update current playback progress. Call this periodically from the UI."""
        if self._state.state == STATE_PLAYING:
            self._update_progress()

    def _update_progress(self) -> None:
        if self._player is None:
            return

        try:
            position = self._player.get_time_ms()
            duration = self._player.get_length_ms()
            
            with self._lock:
                self._state.position_ms = position
                self._state.duration_ms = duration
                self._notify(EVENT_PROGRESS, (position, duration))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Progress update failed: %s", exc)

    def _on_end(self, generation: int) -> None:
        """Called from VLC thread when playback ends."""
        if generation == self._generation:
            self._event_queue.put(("end", None))

    def _on_error(self, generation: int) -> None:
        """Called from VLC thread when an error occurs."""
        if generation == self._generation:
            self._event_queue.put(("error", "VLC could not play this stream."))

    def poll_events(self) -> Optional[tuple]:
        """Check for pending VLC events (end/error). Call from the UI thread."""
        try:
            return self._event_queue.get_nowait()
        except queue.Empty:
            return None

    def release(self) -> None:
        """Release player resources."""
        if self._player is not None:
            self._player.release()
            self._player = None
        self._state = PlaybackState(state=STATE_IDLE)
