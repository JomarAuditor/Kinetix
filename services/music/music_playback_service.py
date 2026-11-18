"""Music playback: queue, yt-dlp resolving (background thread) and VLC. No widgets here.

The GUI calls play_track / toggle_pause / next / previous / seek_fraction / set_volume and
listens with subscribe(). All listener calls happen on the Tk thread, because background
threads and VLC only put messages in a queue that pump() reads (the PlayerBar calls pump
every few hundred milliseconds).

Events sent to listeners (event name, payload):
  track(Track|None)  state(str)  started(Track)  notice(str)  error(str)
  favorite((track_id, bool))  lyrics_visible(bool)
"""
import queue
import threading
from typing import Callable, List, Optional

from core.exceptions import MediaSourceError, PlaybackError
from integrations.media.vlc_player import VlcPlayer
from integrations.media.ytdlp_client import YtDlpClient
from models.music import Track
from utils.logger import get_logger

logger = get_logger("playback")

STATE_IDLE = "idle"
STATE_LOADING = "loading"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"

EVENT_TRACK = "track"
EVENT_STATE = "state"
EVENT_STARTED = "started"
EVENT_NOTICE = "notice"
EVENT_ERROR = "error"
EVENT_FAVORITE = "favorite"
EVENT_LYRICS_VISIBLE = "lyrics_visible"

PREVIEW_NOTICE = "Full audio was not available. Playing the 30-second preview."
_PREVIEW_LENGTH_MS = 30_000
_RESTART_THRESHOLD_MS = 3000
Listener = Callable[[str, object], None]


class MusicPlaybackService:
    def __init__(self, resolver: Optional[YtDlpClient] = None) -> None:
        self._resolver = resolver or YtDlpClient()
        self._player: Optional[VlcPlayer] = None
        self._events: "queue.Queue" = queue.Queue()
        self._listeners: List[Listener] = []
        self._pumping = False
        self._request_id = 0
        self._player_generation = 0
        self._volume_pending = False

        self.current: Optional[Track] = None
        self.queue: List[Track] = []
        self.index = -1
        self.state = STATE_IDLE
        self.is_preview = False
        self.volume = 70
        self.autoplay_next = True
        self.lyrics_visible = True

    # ---------------------------------------------------------------- setup
    def configure(self, volume: int, autoplay_next: bool, show_lyrics: bool) -> None:
        """Apply the saved playback settings (called once after sign in)."""
        self.volume, self.autoplay_next, self.lyrics_visible = volume, autoplay_next, show_lyrics
        if self._player is not None:
            self._player.set_volume(volume)

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)
        return unsubscribe

    # ---------------------------------------------------------------- controls
    def play_track(self, track: Track, queue_tracks: Optional[List[Track]] = None) -> None:
        """Play `track`. Previous/next use `queue_tracks` (the list the song was chosen from)."""
        if queue_tracks is not None:
            self.queue = list(queue_tracks)
        ids = [item.track_id for item in self.queue]
        if track.track_id in ids:
            self.index = ids.index(track.track_id)
        else:
            self.queue, self.index = [track], 0
        self._start(track)
        self.pump()

    def toggle_pause(self) -> None:
        if self._player is not None and self.state == STATE_PLAYING:
            self._player.pause()
            self._set_state(STATE_PAUSED)
        elif self._player is not None and self.state == STATE_PAUSED:
            self._player.resume()
            self._set_state(STATE_PLAYING)
        elif self.state == STATE_IDLE and self.current is not None:
            self._start(self.current)
        self.pump()

    def next(self) -> bool:
        if self.index + 1 >= len(self.queue):
            return False
        self.index += 1
        self._start(self.queue[self.index])
        self.pump()
        return True

    def previous(self) -> None:
        if self.current is None:
            return
        if self.position_ms() > _RESTART_THRESHOLD_MS or self.index <= 0:
            self.seek_fraction(0.0)
        else:
            self.index -= 1
            self._start(self.queue[self.index])
        self.pump()

    def seek_fraction(self, fraction: float) -> None:
        if self._player is not None and self.state in (STATE_PLAYING, STATE_PAUSED):
            self._player.seek_fraction(fraction)

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))
        if self._player is not None:
            self._player.set_volume(self.volume)

    def set_lyrics_visible(self, visible: bool) -> None:
        self.lyrics_visible = visible
        self._post(EVENT_LYRICS_VISIBLE, visible)
        self.pump()

    def announce_favorite(self, track_id: str, favorite: bool) -> None:
        """Tell the player bar and the Music page that a heart changed."""
        self._post(EVENT_FAVORITE, (track_id, favorite))
        self.pump()

    def stop(self) -> None:
        """Stop and forget the queue (used on logout)."""
        self._request_id += 1
        if self._player is not None:
            self._player.stop()
        self.current, self.queue, self.index, self.is_preview = None, [], -1, False
        self._set_state(STATE_IDLE)
        self._post(EVENT_TRACK, None)
        self.pump()

    def shutdown(self) -> None:
        """Release VLC when the app closes."""
        self._request_id += 1
        if self._player is not None:
            self._player.release()
            self._player = None

    # ---------------------------------------------------------------- reading state
    def position_ms(self) -> int:
        if self._player is None or self.state not in (STATE_PLAYING, STATE_PAUSED):
            return 0
        return self._player.get_time_ms()

    def length_ms(self) -> int:
        if self.current is None:
            return 0
        if self._player is not None and self.state in (STATE_PLAYING, STATE_PAUSED):
            length = self._player.get_length_ms()
            if length > 0:
                return length
        return _PREVIEW_LENGTH_MS if self.is_preview else self.current.duration_ms

    # ---------------------------------------------------------------- starting a track
    def _ensure_player(self) -> VlcPlayer:
        if self._player is None:
            self._player = VlcPlayer(
                on_end=lambda gen: self._events.put(("_media_end", gen)),
                on_error=lambda gen: self._events.put(("_media_error", gen)),
            )
            self._player.set_volume(self.volume)
        return self._player

    def _start(self, track: Track) -> None:
        try:
            player = self._ensure_player()
        except PlaybackError as exc:
            self._post(EVENT_ERROR, str(exc))
            return
        self._request_id += 1
        request_id = self._request_id
        player.stop()
        self.current, self.is_preview = track, False
        self._set_state(STATE_LOADING)
        self._post(EVENT_TRACK, track)
        threading.Thread(target=self._resolve, args=(request_id, track), daemon=True).start()

    def _resolve(self, request_id: int, track: Track) -> None:
        """Runs in a background thread. Only puts a message in the queue."""
        try:
            audio = self._resolver.resolve_audio(track.artist, track.title, track.duration_ms // 1000)
            self._events.put(("_resolved", (request_id, audio.url, audio.user_agent, False)))
        except MediaSourceError as exc:
            if track.preview_url:
                self._events.put(("_resolved", (request_id, track.preview_url, "", True)))
            else:
                self._events.put(("_failed", (request_id, str(exc))))

    # ---------------------------------------------------------------- queue handling (Tk thread)
    def _post(self, event: str, payload: object = None) -> None:
        self._events.put((event, payload))

    def _set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self._post(EVENT_STATE, state)

    def pump(self) -> None:
        """Handle queued messages and call the listeners. Must run on the Tk thread."""
        if self._pumping:
            return
        self._pumping = True
        try:
            while True:
                try:
                    event, payload = self._events.get_nowait()
                except queue.Empty:
                    break
                if event.startswith("_"):
                    self._handle_internal(event, payload)
                else:
                    self._dispatch(event, payload)
            self._apply_pending_volume()
        finally:
            self._pumping = False

    def _dispatch(self, event: str, payload: object) -> None:
        for listener in list(self._listeners):
            try:
                listener(event, payload)
            except Exception:  # noqa: BLE001 - one broken listener must not stop playback
                logger.exception("Playback listener failed")

    def _handle_internal(self, event: str, payload) -> None:
        if event == "_resolved":
            self._play_url(*payload)
        elif event == "_failed":
            request_id, message = payload
            if request_id == self._request_id:
                self._set_state(STATE_IDLE)
                self._post(EVENT_ERROR, message)
        elif event == "_media_end" and payload == self._player_generation:
            self._on_media_end()
        elif event == "_media_error" and payload == self._player_generation:
            self._on_media_error()

    def _play_url(self, request_id: int, url: str, user_agent: str, preview: bool) -> None:
        if request_id != self._request_id or self._player is None or self.current is None:
            return  # the user already chose another song
        try:
            self._player_generation = self._player.load(url, user_agent)
            self._player.play()
        except PlaybackError as exc:
            self._set_state(STATE_IDLE)
            self._post(EVENT_ERROR, str(exc))
            return
        self.is_preview = preview
        if preview:
            self._post(EVENT_NOTICE, PREVIEW_NOTICE)
        self._volume_pending = True
        self._set_state(STATE_PLAYING)
        self._post(EVENT_STARTED, self.current)

    def _on_media_end(self) -> None:
        if self.state != STATE_PLAYING:
            return
        if self.autoplay_next and self.index + 1 < len(self.queue):
            self.index += 1
            self._start(self.queue[self.index])
        else:
            self._set_state(STATE_IDLE)

    def _on_media_error(self) -> None:
        """VLC could not play the stream. Try the 30-second preview once, otherwise report it."""
        track = self.current
        if track is not None and not self.is_preview and track.preview_url:
            self._request_id += 1
            self._play_url(self._request_id, track.preview_url, "", True)
            return
        self._set_state(STATE_IDLE)
        self._post(EVENT_ERROR, "This song could not be played.")

    def _apply_pending_volume(self) -> None:
        if self._volume_pending and self._player is not None:
            self._volume_pending = not self._player.set_volume(self.volume)
