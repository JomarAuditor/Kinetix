"""PlayerBar: the persistent 88px music player at the bottom of the shell.

It lives in AppShell.player_slot, so it keeps playing (and stays visible) while the user
moves between pages. It appears when the first song starts. All playback goes through
ctx.music_playback (MusicPlaybackService); this file only draws and sends commands.
"""
from typing import Optional

import customtkinter as ctk

from app.navigation import Route
from config.constants import MEDIA_MUSIC
from core.exceptions import KinetixError
from models.music import Track
from presentation.components.buttons import IconButton
from presentation.components.cards import FitLabel, HeartButton
from presentation.components.dialogs import show_toast
from presentation.components.images import ImageView
from presentation.components.inputs import Slider
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing
from services.music import music_playback_service as events
from utils.helpers import format_duration
from utils.logger import get_logger

logger = get_logger("player_bar")
_TICK_MS = 250
_NOTICE_MS = 5000
_ERROR_MS = 6500
_TIME_LABEL_WIDTH = 44


class PlayerBar(ctk.CTkFrame):
    def __init__(self, parent, ctx) -> None:
        super().__init__(parent, height=Sizes.PLAYER_BAR_HEIGHT, fg_color=Colors.SIDEBAR, corner_radius=0)
        self.pack_propagate(False)
        self.ctx = ctx
        self._playback = ctx.music_playback
        self._shown = False
        self._dragging = False
        self._job: Optional[str] = None
        self._volume_before_mute = 0
        self._last_elapsed = "0:00"
        self._last_total = "0:00"

        ctk.CTkFrame(self, height=1, fg_color=Colors.BORDER, corner_radius=0).pack(side="top", fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=Spacing.LG)
        row.grid_rowconfigure(0, weight=1)
        row.grid_columnconfigure(0, weight=1, uniform="bar")
        row.grid_columnconfigure(1, weight=2)
        row.grid_columnconfigure(2, weight=1, uniform="bar")
        self._build_track_info(row).grid(row=0, column=0, sticky="nsew")
        self._build_center(row).grid(row=0, column=1, sticky="nsew", padx=Spacing.LG)
        self._build_right(row).grid(row=0, column=2, sticky="nsew")

        self._unsubscribe = self._playback.subscribe(self._on_event)
        self._tick()

    # ---------------------------------------------------------------- layout
    def _build_track_info(self, parent) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.art = ImageView(frame, (Sizes.PLAYER_ART_SIZE, Sizes.PLAYER_ART_SIZE), placeholder="music")
        self.art.pack(side="left")
        self.heart = HeartButton(frame, False, self._toggle_favorite)
        self.heart.pack(side="right", padx=(Spacing.SM, 0))
        text = ctk.CTkFrame(frame, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(Spacing.MD, 0))
        self.title_label = FitLabel(text, "", typography.card(), Colors.TEXT)
        self.title_label.pack(fill="x")
        self.artist_label = FitLabel(text, "", typography.body(), Colors.TEXT_SECONDARY)
        self.artist_label.pack(fill="x")
        return frame

    def _build_center(self, parent) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.pack(pady=(Spacing.SM, 0))
        IconButton(controls, "skip_prev", self._playback.previous, style="ghost", icon_color=Colors.TEXT,
                   icon_size=18).pack(side="left", padx=Spacing.SM)
        self.play_button = IconButton(controls, "play", self._playback.toggle_pause, style="accent",
                                      round_=True, size=Sizes.PLAYER_PLAY_SIZE, icon_size=18)
        self.play_button.pack(side="left", padx=Spacing.SM)
        IconButton(controls, "skip_next", self._next, style="ghost", icon_color=Colors.TEXT,
                   icon_size=18).pack(side="left", padx=Spacing.SM)

        progress = ctk.CTkFrame(frame, fg_color="transparent")
        progress.pack(fill="x", pady=(0, Spacing.XS))
        self.elapsed_label = ctk.CTkLabel(progress, text="0:00", width=_TIME_LABEL_WIDTH, anchor="e",
                                          font=typography.small(), text_color=Colors.TEXT_SECONDARY)
        self.elapsed_label.pack(side="left")
        self.total_label = ctk.CTkLabel(progress, text="0:00", width=_TIME_LABEL_WIDTH, anchor="w",
                                        font=typography.small(), text_color=Colors.TEXT_SECONDARY)
        self.total_label.pack(side="right")
        self.progress = Slider(progress, from_=0, to=1, value=0, command=self._on_drag,
                               width=Sizes.PROGRESS_SLIDER_WIDTH)
        self.progress.pack(side="left", fill="x", expand=True, padx=Spacing.SM)
        self.progress.bind("<ButtonRelease-1>", self._on_release)
        return frame

    def _build_right(self, parent) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.volume = Slider(frame, from_=0, to=100, value=self._playback.volume, command=self._on_volume,
                             width=Sizes.VOLUME_SLIDER_WIDTH)
        self.volume.pack(side="right")
        self.volume_button = IconButton(frame, "volume", self._toggle_mute, style="ghost", size=32)
        self.volume_button.pack(side="right", padx=(Spacing.MD, Spacing.XS))
        self.lyrics_button = ctk.CTkButton(frame, text=" Lyrics", compound="left", width=88, height=34,
                                           corner_radius=Sizes.BUTTON_RADIUS, border_width=1,
                                           font=typography.body_bold(), command=self._toggle_lyrics)
        self.lyrics_button.pack(side="right")
        self._style_lyrics_button()
        self._refresh_volume_icon()
        return frame

    # ---------------------------------------------------------------- showing and hiding
    def _show(self) -> None:
        if not self._shown:
            self._shown = True
            self.pack(fill="x")

    def _hide(self) -> None:
        if self._shown:
            self._shown = False
            self.pack_forget()
            self.master.configure(height=0)  # give the space back to the page

    # ---------------------------------------------------------------- playback events
    def _on_event(self, event: str, payload) -> None:
        if event == events.EVENT_TRACK:
            self._show_track(payload)
        elif event == events.EVENT_STATE:
            self._refresh_state()
        elif event == events.EVENT_STARTED:
            self._record_history(payload)
        elif event == events.EVENT_NOTICE:
            show_toast(self, str(payload), "info", _NOTICE_MS)
        elif event == events.EVENT_ERROR:
            show_toast(self, str(payload), "error", _ERROR_MS)
        elif event == events.EVENT_FAVORITE:
            self._sync_favorite(*payload)
        elif event == events.EVENT_LYRICS_VISIBLE:
            self._style_lyrics_button()

    def _show_track(self, track: Optional[Track]) -> None:
        if track is None:
            self._hide()
            return
        self._show()
        self.art.load(track.artwork_url)
        self.title_label.set_text(track.title)
        self.heart.set_favorite(self._is_favorite(track))
        self._reset_progress(track)
        self._refresh_state()

    def _refresh_state(self) -> None:
        state, track = self._playback.state, self._playback.current
        self.play_button.set_icon("pause" if state in (events.STATE_PLAYING, events.STATE_LOADING) else "play")
        if track is None:
            return
        if state == events.STATE_LOADING:
            status = "Finding audio..."
        elif self._playback.is_preview:
            status = f"{track.artist} - 30s preview"
        else:
            status = track.artist
        self.artist_label.set_text(status)

    def _record_history(self, track: Optional[Track]) -> None:
        user = self.ctx.session_service.current_user
        if user is None or track is None:
            return
        try:
            self.ctx.library.record_play(user.id, track.to_media_item())
        except KinetixError as exc:
            logger.warning("Could not save history: %s", exc)

    # ---------------------------------------------------------------- favorites
    def _is_favorite(self, track: Track) -> bool:
        user = self.ctx.session_service.current_user
        if user is None:
            return False
        try:
            return self.ctx.library.is_favorite(user.id, MEDIA_MUSIC, track.track_id)
        except KinetixError:
            return False

    def _toggle_favorite(self) -> Optional[bool]:
        track, user = self._playback.current, self.ctx.session_service.current_user
        if track is None or user is None:
            return None
        try:
            state = self.ctx.library.toggle_favorite(user.id, track.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._playback.announce_favorite(track.track_id, state)
        return state

    def _sync_favorite(self, track_id: str, favorite: bool) -> None:
        track = self._playback.current
        if track is not None and track.track_id == track_id:
            self.heart.set_favorite(favorite)

    # ---------------------------------------------------------------- progress
    def _tick(self) -> None:
        self._playback.pump()
        if self._shown and not self._dragging:
            self._update_progress()
        self._job = self.after(_TICK_MS, self._tick)

    def _update_progress(self) -> None:
        if self._playback.state not in (events.STATE_PLAYING, events.STATE_PAUSED):
            if self._playback.state == events.STATE_IDLE and self._playback.current is not None:
                self._reset_progress(self._playback.current)
            return
        position, length = self._playback.position_ms(), self._playback.length_ms()
        self.progress.set(min(1.0, position / length) if length else 0)
        elapsed_text = format_duration(position)
        total_text = format_duration(length)
        if elapsed_text != self._last_elapsed:
            self._last_elapsed = elapsed_text
            self.elapsed_label.configure(text=elapsed_text)
        if total_text != self._last_total:
            self._last_total = total_text
            self.total_label.configure(text=total_text)

    def _reset_progress(self, track: Track) -> None:
        self.progress.set(0)
        self._last_elapsed = "0:00"
        self._last_total = format_duration(track.duration_ms)
        self.elapsed_label.configure(text="0:00")
        self.total_label.configure(text=self._last_total)

    def _on_drag(self, value: float) -> None:
        self._dragging = True
        self.elapsed_label.configure(text=format_duration(int(value * self._playback.length_ms())))

    def _on_release(self, _event) -> None:
        if self._dragging:
            self._playback.seek_fraction(self.progress.get())
        self._dragging = False

    # ---------------------------------------------------------------- buttons
    def _next(self) -> None:
        if not self._playback.next():
            show_toast(self, "This is the last song in the queue.", "info")

    def _on_volume(self, value: float) -> None:
        self._playback.set_volume(int(value))
        self._refresh_volume_icon()

    def _toggle_mute(self) -> None:
        if self._playback.volume > 0:
            self._volume_before_mute = self._playback.volume
            target = 0
        else:
            target = self._volume_before_mute or 70
        self._playback.set_volume(target)
        self.volume.set(target)
        self._refresh_volume_icon()

    def _refresh_volume_icon(self) -> None:
        self.volume_button.set_icon("volume_off" if self._playback.volume == 0 else "volume")

    def _toggle_lyrics(self) -> None:
        visible = not self._playback.lyrics_visible
        self._playback.set_lyrics_visible(visible)
        if visible and self.ctx.navigator.current_route != Route.MUSIC:
            self.ctx.navigator.go(Route.MUSIC)

    def _style_lyrics_button(self) -> None:
        on = self._playback.lyrics_visible
        self.lyrics_button.configure(
            image=icons.icon("mic", Colors.ACCENT if on else Colors.TEXT_SECONDARY, 16),
            fg_color=Colors.ACCENT_TINT if on else "transparent", hover_color=Colors.ACCENT_TINT if on else Colors.HOVER,
            border_color=Colors.ACCENT if on else Colors.BORDER,
            text_color=Colors.ACCENT if on else Colors.TEXT_SECONDARY)

    def destroy(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:  # noqa: BLE001
                pass
            self._job = None
        self._unsubscribe()
        super().destroy()
