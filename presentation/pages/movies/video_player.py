"""Embedded 16:9 VLC video player inside the Movie Details view."""
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from core.exceptions import MediaSourceError, PlaybackError
from models.movie import MatchedMovie
from presentation.components.buttons import IconButton
from presentation.components.dialogs import show_toast
from presentation.components.media_controls import TimeSlider, VolumeControl, format_media_time
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing
from services.movies.movie_playback_service import (
    EVENT_ERROR,
    EVENT_PROGRESS,
    EVENT_STATE,
    MoviePlaybackService,
    STATE_IDLE,
    STATE_LOADING,
    STATE_PAUSED,
    STATE_PLAYING,
)
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("video_player")

_PROGRESS_TICK_MS = 500
_MIN_RESUME_MS = 5000


class VideoPlayer(ctk.CTkFrame):
    """Embedded 16:9 VLC player with play/pause, stop, time slider, volume and fullscreen."""

    def __init__(
        self,
        parent,
        ctx,
        on_play_started: Optional[Callable[[], None]] = None,
        on_fullscreen_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(parent, fg_color=Colors.CARD, corner_radius=Sizes.CARD_RADIUS,
                         border_width=1, border_color=Colors.BORDER)
        self.ctx = ctx
        self._on_play_started = on_play_started
        self._on_fullscreen_change = on_fullscreen_change
        self._playback = MoviePlaybackService()
        self._unsubscribe = self._playback.subscribe(self._on_playback_event)

        self._matched: Optional[MatchedMovie] = None
        self._custom_url: Optional[str] = None
        self._progress_job: Optional[str] = None
        self._volume_jobs: list[str] = []
        self._is_fullscreen = False
        self._pending_resume_ms = 0
        self._resume_applied = False
        self._remember_position = False
        self._volume = 70
        self._escape_bound = False

        self._load_user_settings()
        self._build_ui()
        self.show_idle()

    # ------------------------------------------------------------------
    # Setup & UI
    # ------------------------------------------------------------------

    def _load_user_settings(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        try:
            saved = self.ctx.library.movie_settings(user.id)
            self._volume = saved.volume
            self._remember_position = saved.remember_position
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load movie settings: %s", exc)

    def _build_ui(self) -> None:
        self._stage = ctk.CTkFrame(
            self, height=Sizes.VIDEO_HEIGHT,
            fg_color=Colors.VIDEO_BACKGROUND, corner_radius=0,
        )
        self._stage.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))
        self._stage.pack_propagate(False)
        self._stage.grid_rowconfigure(0, weight=1)
        self._stage.grid_columnconfigure(0, weight=1)
        self._stage.bind("<Configure>", self._on_stage_configure, add="+")

        # Dedicated surface for VLC native window handle (must contain no child widgets)
        self._video_surface = ctk.CTkFrame(
            self._stage, fg_color=Colors.VIDEO_BACKGROUND, corner_radius=0,
        )
        self._video_surface.grid(row=0, column=0, sticky="nsew")

        # Overlay for idle ("Press Play to start"), loading, and error states
        self._overlay = ctk.CTkFrame(
            self._stage, fg_color=Colors.VIDEO_BACKGROUND, corner_radius=0,
        )
        self._overlay.grid(row=0, column=0, sticky="nsew")

        self._overlay_inner = ctk.CTkFrame(self._overlay, fg_color="transparent")
        self._overlay_inner.place(relx=0.5, rely=0.5, anchor="center")

        self._overlay_icon = ctk.CTkLabel(
            self._overlay_inner, text="", image=icons.icon("movie", Colors.ACCENT, 40),
        )
        self._overlay_icon.pack(pady=(0, Spacing.MD))

        self._overlay_title = ctk.CTkLabel(
            self._overlay_inner, text="Press Play to start",
            font=typography.section(), text_color=Colors.TEXT,
        )
        self._overlay_title.pack(pady=(0, Spacing.XS))

        self._overlay_sub = ctk.CTkLabel(
            self._overlay_inner, text="", font=typography.body(),
            text_color=Colors.TEXT_SECONDARY, wraplength=440, justify="center",
        )
        self._overlay_sub.pack()

        # Controls bar
        self._controls = ctk.CTkFrame(self, fg_color=Colors.SIDEBAR, corner_radius=Sizes.BUTTON_RADIUS)
        self._controls.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        self._time_slider = TimeSlider(self._controls, on_seek=self._on_seek)
        self._time_slider.pack(fill="x", padx=Spacing.MD, pady=(Spacing.SM, 0))

        bar = ctk.CTkFrame(self._controls, fg_color="transparent")
        bar.pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left")

        self._play_btn = IconButton(
            left, "play", self._on_play_pause_click,
            style="accent", round_=True, size=Sizes.PLAYER_PLAY_SIZE, icon_size=18,
        )
        self._play_btn.pack(side="left", padx=(0, Spacing.SM))

        self._stop_btn = IconButton(
            left, "stop", self.stop, style="outline", size=Sizes.ICON_BUTTON_SIZE, icon_size=15,
        )
        self._stop_btn.pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right")

        self._volume_ctrl = VolumeControl(right, initial_volume=self._volume, on_change=self._on_volume_change)
        self._volume_ctrl.pack(side="left", padx=(0, Spacing.SM))

        self._fs_btn = IconButton(
            right, "fullscreen", self.toggle_fullscreen, style="ghost", size=Sizes.ICON_BUTTON_SIZE, icon_size=16,
        )
        self._fs_btn.pack(side="left")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_movie(self, matched: MatchedMovie, autoplay: bool = False) -> None:
        """Bind a MatchedMovie to the player, showing the idle state or auto-starting."""
        self._matched = matched
        self._custom_url = None
        self._pending_resume_ms = self._load_saved_position()
        self._resume_applied = False

        if autoplay and matched.is_playable:
            self.play_movie()
        elif matched.is_playable:
            hint = "Press Play below to start watching."
            if self._pending_resume_ms > _MIN_RESUME_MS:
                hint = f"Will resume from {format_media_time(self._pending_resume_ms)}."
            self.show_idle(hint)
        else:
            self.show_idle("No verified free stream is available for this movie.")

    def play_movie(self) -> None:
        if self._matched is None or not self._matched.is_playable:
            self.show_error("This movie does not have a verified playable source.")
            return
        self._custom_url = None
        self._pending_resume_ms = self._load_saved_position()
        self._resume_applied = False
        self._start_source(lambda hwnd, vol: self._playback.play_movie(self._matched, hwnd, volume=vol))

    def play_url(self, url: str) -> None:
        cleaned = (url or "").strip()
        if not cleaned.startswith(("http://", "https://")):
            show_toast(self, "Enter a valid http:// or https:// video URL.", "error")
            return
        self._custom_url = cleaned
        self._pending_resume_ms = 0
        self._resume_applied = True
        self._start_source(lambda hwnd, vol: self._playback.play_url(cleaned, hwnd, volume=vol))

    def stop(self) -> None:
        self._save_current_position()
        self._cancel_timers()
        self._playback.stop()
        self._time_slider.reset()
        self._play_btn.set_icon("play")
        self.show_idle()

    def stop_and_release(self) -> None:
        if self._is_fullscreen:
            self.set_fullscreen(False)
        self._save_current_position()
        self._cancel_timers()
        self._playback.release()

    # ------------------------------------------------------------------
    # Overlay states
    # ------------------------------------------------------------------

    def show_idle(self, subtitle: str = "Click Play to start watching inside Kinetix.") -> None:
        self._set_overlay("movie", Colors.ACCENT, "Press Play to start", subtitle)

    def show_loading(self, message: str = "Resolving stream with yt-dlp...") -> None:
        self._set_overlay("movie", Colors.ACCENT, "Loading video...", message)

    def show_error(self, message: str) -> None:
        self._set_overlay("alert", Colors.ERROR, "Could not play this video", message)
        self._play_btn.set_icon("play")

    def _set_overlay(self, icon_name: str, color: str, title: str, subtitle: str) -> None:
        if not self._alive():
            return
        self._overlay_icon.configure(image=icons.icon(icon_name, color, 40))
        self._overlay_title.configure(text=title)
        self._overlay_sub.configure(text=subtitle)
        self._overlay.grid(row=0, column=0, sticky="nsew")
        self._overlay.tkraise()

    def _hide_overlay(self) -> None:
        if self._alive():
            self._overlay.grid_remove()

    # ------------------------------------------------------------------
    # Playback execution
    # ------------------------------------------------------------------

    def _start_source(self, worker_fn: Callable[[int, int], None]) -> None:
        self._pause_music_if_playing()
        self.show_loading()
        self._play_btn.set_enabled(False)

        try:
            self._video_surface.update()
            hwnd = self._video_surface.winfo_id()
        except Exception as exc:  # noqa: BLE001
            self._play_btn.set_enabled(True)
            self.show_error(f"Could not initialize video surface: {exc}")
            return

        volume = self._volume_ctrl.volume

        def work() -> None:
            worker_fn(hwnd, volume)

        def done(_res, error: Optional[Exception]) -> None:
            if not self._alive():
                return
            self._play_btn.set_enabled(True)
            if error is not None:
                msg = str(error) if isinstance(error, (MediaSourceError, PlaybackError)) else f"Playback failed: {error}"
                show_toast(self, msg, "error", 5000)
                self.show_error(msg)
                return
            self._hide_overlay()
            self._play_btn.set_icon("pause")
            self._start_progress_loop()
            self._schedule_volume_enforce()
            if self._on_play_started is not None:
                self._on_play_started()

        run_in_background(self, work, done)

    def _pause_music_if_playing(self) -> None:
        music = self.ctx.music_playback
        if music is not None and music.state != "idle":
            music.stop()
            show_toast(self, "Music stopped", "info", 2000)

    def _schedule_volume_enforce(self) -> None:
        for delay in (600, 1500):
            try:
                job = self.after(delay, self._apply_volume_now)
                self._volume_jobs.append(job)
            except tk.TclError:
                pass

    def _apply_volume_now(self) -> None:
        if self._alive():
            self._playback.set_volume(self._volume_ctrl.volume)

    # ------------------------------------------------------------------
    # Controls & Events
    # ------------------------------------------------------------------

    def _on_play_pause_click(self) -> None:
        state = self._playback.state
        if state in (STATE_PLAYING, STATE_PAUSED):
            if state == STATE_PAUSED:
                self._pause_music_if_playing()
            self._playback.toggle_pause()
        elif self._custom_url:
            self.play_url(self._custom_url)
        else:
            self.play_movie()

    def _on_seek(self, fraction: float) -> None:
        self._playback.seek(fraction)

    def _on_volume_change(self, volume: int) -> None:
        self._volume = volume
        self._playback.set_volume(volume)

    def _on_playback_event(self, event: str, payload) -> None:
        if not self._alive():
            return
        if event == EVENT_STATE:
            state = self._playback.state
            self._play_btn.set_icon("pause" if state == STATE_PLAYING else "play")
        elif event == EVENT_PROGRESS:
            pos_ms, dur_ms = payload
            self._time_slider.set_progress(pos_ms, dur_ms)
            self._try_apply_resume(dur_ms)
        elif event == EVENT_ERROR:
            self.show_error(str(payload))

    def _try_apply_resume(self, duration_ms: int) -> None:
        if self._resume_applied or self._pending_resume_ms <= _MIN_RESUME_MS:
            return
        if duration_ms <= 0:
            return
        self._resume_applied = True
        if self._pending_resume_ms < duration_ms * 0.95:
            target = self._pending_resume_ms
            self._playback.seek_ms(target)
            show_toast(self, f"Resumed from {format_media_time(target)}", "info", 2500)

    def _start_progress_loop(self) -> None:
        self._cancel_progress_job()
        self._tick_progress()

    def _tick_progress(self) -> None:
        if not self._alive():
            return
        if self._playback.state == STATE_PLAYING:
            self._playback.update_progress()

        ev = self._playback.poll_events()
        if ev is not None:
            kind, payload = ev
            if kind == "error":
                show_toast(self, str(payload), "error", 5000)
                self.show_error(str(payload))
                return
            if kind == "end":
                self._clear_saved_position()
                self._playback.stop()
                self._play_btn.set_icon("play")
                self._time_slider.reset()
                self.show_idle("Playback finished. Press Play to watch again.")
                return

        try:
            self._progress_job = self.after(_PROGRESS_TICK_MS, self._tick_progress)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Fullscreen
    # ------------------------------------------------------------------

    def _on_stage_configure(self, event) -> None:
        if self._is_fullscreen or not self._alive():
            return
        try:
            scaling = self._get_widget_scaling()
        except Exception:  # noqa: BLE001
            scaling = 1.0
        logical_w = event.width / max(scaling, 0.1)
        if logical_w < 320:
            return
        target_h = max(Sizes.VIDEO_HEIGHT, min(780, round(logical_w * 0.62)))
        if abs(target_h - self._stage.cget("height")) >= 8:
            self._stage.configure(height=target_h)

    def toggle_fullscreen(self) -> None:
        self.set_fullscreen(not self._is_fullscreen)

    def set_fullscreen(self, enabled: bool) -> None:
        if enabled == self._is_fullscreen or not self._alive():
            return
        self._is_fullscreen = enabled
        self._fs_btn.set_icon("exit_fullscreen" if enabled else "fullscreen")

        if enabled:
            self.configure(corner_radius=0, border_width=0, fg_color=Colors.VIDEO_BACKGROUND)
            self._stage.pack_configure(fill="both", expand=True, padx=0, pady=0)
            self._controls.pack_configure(padx=Spacing.LG, pady=Spacing.SM)
            self._bind_escape()
        else:
            self._unbind_escape()
            self.configure(corner_radius=Sizes.CARD_RADIUS, border_width=1, fg_color=Colors.CARD)
            self._stage.configure(height=Sizes.VIDEO_HEIGHT)
            self._stage.pack_configure(fill="x", expand=False, padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))
            self._controls.pack_configure(padx=Spacing.MD, pady=(0, Spacing.MD))

        shell = self._find_shell()
        if shell is not None and hasattr(shell, "set_fullscreen_mode"):
            shell.set_fullscreen_mode(enabled)
        if self._on_fullscreen_change is not None:
            self._on_fullscreen_change(enabled)
        try:
            self._video_surface.update_idletasks()
        except Exception:  # noqa: BLE001
            pass

    def _find_shell(self):
        widget = self.master
        while widget is not None:
            if hasattr(widget, "set_fullscreen_mode"):
                return widget
            widget = getattr(widget, "master", None)
        return None

    def _bind_escape(self) -> None:
        if self._escape_bound:
            return
        try:
            self.winfo_toplevel().bind("<Escape>", self._on_escape, add="+")
            self._escape_bound = True
        except Exception:  # noqa: BLE001
            pass

    def _unbind_escape(self) -> None:
        if not self._escape_bound:
            return
        try:
            self.winfo_toplevel().unbind("<Escape>")
        except Exception:  # noqa: BLE001
            pass
        self._escape_bound = False

    def _on_escape(self, _event=None) -> None:
        if self._is_fullscreen:
            self.set_fullscreen(False)

    # ------------------------------------------------------------------
    # Position persistence
    # ------------------------------------------------------------------

    def _load_saved_position(self) -> int:
        if not self._remember_position or self._matched is None:
            return 0
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return 0
        try:
            return self.ctx.library.get_movie_position(user.id, self._matched.external_key)
        except Exception:  # noqa: BLE001
            return 0

    def _save_current_position(self) -> None:
        if not self._remember_position or self._matched is None or self._custom_url is not None:
            return
        if self._playback.state not in (STATE_PLAYING, STATE_PAUSED):
            return
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        pos = self._playback.position_ms
        dur = self._playback.duration_ms
        if pos <= _MIN_RESUME_MS or (dur > 0 and pos >= dur * 0.95):
            pos = 0
        try:
            self.ctx.library.save_movie_position(user.id, self._matched.external_key, pos)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not save movie position: %s", exc)

    def _clear_saved_position(self) -> None:
        if not self._remember_position or self._matched is None:
            return
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        try:
            self.ctx.library.save_movie_position(user.id, self._matched.external_key, 0)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cancel_progress_job(self) -> None:
        if self._progress_job is not None:
            try:
                self.after_cancel(self._progress_job)
            except Exception:  # noqa: BLE001
                pass
            self._progress_job = None

    def _cancel_timers(self) -> None:
        self._cancel_progress_job()
        for job in self._volume_jobs:
            try:
                self.after_cancel(job)
            except Exception:  # noqa: BLE001
                pass
        self._volume_jobs.clear()

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:  # noqa: BLE001
            return False

    def destroy(self) -> None:
        self.stop_and_release()
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        super().destroy()
