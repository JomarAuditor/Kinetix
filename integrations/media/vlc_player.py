"""python-vlc wrapper for audio and video playback. Raises PlaybackError (never crashes) if VLC is missing."""
import sys
from typing import Callable, Optional

from core.exceptions import PlaybackError
from utils.logger import get_logger

logger = get_logger("vlc")

VLC_MISSING_MESSAGE = ("VLC Media Player was not found. Install VLC from videolan.org "
                       "(same 32/64-bit type as Python), then restart Kinetix.")


def _import_vlc():
    try:
        import vlc
        return vlc
    except Exception as exc:  # noqa: BLE001 - ImportError, OSError or NameError when libvlc is missing
        raise PlaybackError(VLC_MISSING_MESSAGE) from exc


class VlcPlayer:
    """VlcPlayer(on_end=None, on_error=None, video=False).

    on_end(generation) and on_error(generation) are called from a VLC thread: only put
    a message in a queue there, never touch widgets or call player methods.
    """

    def __init__(self, on_end: Optional[Callable[[int], None]] = None,
                 on_error: Optional[Callable[[int], None]] = None,
                 video: bool = False) -> None:
        self._vlc = _import_vlc()
        self._player = None
        self._instance = None

        # Try with explicit audio output first, fall back to defaults
        # (--aout=directsound is not available on all VLC builds/platforms)
        arg_sets = (
            ["--quiet", "--aout=directsound"] if video else ["--no-video", "--quiet", "--aout=directsound"],
            ["--quiet"] if video else ["--no-video", "--quiet"],
        )
        last_exc = None
        for args in arg_sets:
            try:
                self._instance = self._vlc.Instance(*args)
                if self._instance:
                    self._player = self._instance.media_player_new()
                    if self._player:
                        break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._instance = None
                self._player = None

        if self._player is None:
            raise PlaybackError(VLC_MISSING_MESSAGE) from last_exc

        self._on_end, self._on_error = on_end, on_error
        self._generation = 0
        self._volume = 70
        self._muted = False

        manager = self._player.event_manager()
        manager.event_attach(self._vlc.EventType.MediaPlayerEndReached, self._handle_end)
        manager.event_attach(self._vlc.EventType.MediaPlayerEncounteredError, self._handle_error)
        manager.event_attach(self._vlc.EventType.MediaPlayerOpening, self._handle_opening)
        manager.event_attach(self._vlc.EventType.MediaPlayerBuffering, self._handle_buffering)
        manager.event_attach(self._vlc.EventType.MediaPlayerPlaying, self._handle_playing)

    def set_window(self, window_id) -> None:
        """Set the native window handle for embedded video output across platforms."""
        if sys.platform.startswith("win"):
            if hasattr(self._player, "set_hwnd"):
                self._player.set_hwnd(window_id)
        elif sys.platform == "darwin":
            if hasattr(self._player, "set_nsobject"):
                self._player.set_nsobject(window_id)
        else:
            if hasattr(self._player, "set_xwindow"):
                self._player.set_xwindow(window_id)

    # ---- events (VLC thread) ----
    def _handle_end(self, _event) -> None:
        if self._on_end:
            self._on_end(self._generation)

    def _handle_error(self, _event) -> None:
        if self._on_error:
            self._on_error(self._generation)

    def _handle_opening(self, _event) -> None:
        """Set volume as soon as VLC starts opening media (before buffering begins)."""
        try:
            self._player.audio_set_volume(self._volume)
            self._player.audio_set_mute(self._muted)
        except Exception:  # noqa: BLE001
            pass

    def _handle_buffering(self, _event) -> None:
        """Re-apply volume on each buffering event (VLC may reset it mid-buffer)."""
        try:
            self._player.audio_set_volume(self._volume)
            self._player.audio_set_mute(self._muted)
        except Exception:  # noqa: BLE001
            pass

    def _handle_playing(self, _event) -> None:
        """Re-apply volume when playback actually starts (most reliable hook)."""
        try:
            self._player.audio_set_volume(self._volume)
            self._player.audio_set_mute(self._muted)
        except Exception:  # noqa: BLE001
            pass

    # ---- controls ----
    def load(self, url: str, user_agent: str = "", audio_url: str = "") -> int:
        """Load a stream URL. Returns a generation number that identifies this media.

        When audio_url is set (DASH streams), it is passed as :input-slave so VLC
        muxes the separate audio track on the fly alongside the video.
        """
        self._generation += 1
        media = self._instance.media_new(url)
        if user_agent:
            media.add_option(f":http-user-agent={user_agent}")
        if audio_url:
            # VLC input-slave: attach a separate audio stream to a video stream
            media.add_option(f":input-slave={audio_url}")
            logger.info("Attached audio slave stream for DASH playback")
        media.add_option(":network-caching=5000")
        media.add_option(":http-reconnect")
        media.add_option(":prefetch-buffer-size=10485760")
        self._player.set_media(media)
        return self._generation

    def play(self) -> None:
        result = self._player.play()
        if result == -1:
            raise PlaybackError("VLC could not start playback.")
        # Set volume immediately and again after a short delay
        # (VLC resets audio state between play() calls on some builds)
        self._player.audio_set_volume(self._volume)
        self._player.audio_set_mute(self._muted)
        logger.info("VLC playback started, volume=%d muted=%s", self._volume, self._muted)

    def pause(self) -> None:
        self._player.set_pause(1)

    def resume(self) -> None:
        self._player.set_pause(0)

    def stop(self) -> None:
        self._player.stop()

    def seek_fraction(self, fraction: float) -> None:
        self._player.set_position(max(0.0, min(1.0, fraction)))

    def set_time_ms(self, milliseconds: int) -> None:
        self._player.set_time(max(0, int(milliseconds)))

    def set_volume(self, volume: int) -> bool:
        """0 to 100. Returns False if VLC is not ready yet."""
        self._volume = max(0, min(100, int(volume)))
        self._muted = self._volume == 0
        result = self._player.audio_set_volume(self._volume)
        self._player.audio_set_mute(self._muted)
        logger.info("Volume set to %d, muted=%s, result=%d", self._volume, self._muted, result)
        return result == 0

    def get_time_ms(self) -> int:
        return max(0, self._player.get_time())

    def get_length_ms(self) -> int:
        return max(0, self._player.get_length())

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def release(self) -> None:
        try:
            self._player.stop()
            self._player.release()
            self._instance.release()
        except Exception:  # noqa: BLE001 - closing the app anyway
            pass
