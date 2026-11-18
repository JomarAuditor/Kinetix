"""Music page: Featured Tracks, Search Results and the lyrics panel.

The persistent player bar is not part of this page (it lives in the shell), so music keeps
playing when this page is closed. This page only clears its own timer and listener.
"""
from typing import List, Optional, Set

import customtkinter as ctk

from config.constants import MEDIA_MUSIC
from core.exceptions import ApiError, KinetixError
from models.media import MediaItem
from models.music import Track
from presentation.components.cards import FavoriteTracker
from presentation.components.dialogs import show_toast
from presentation.pages.base_page import BasePage
from presentation.pages.music.lyrics_panel import LyricsPanel
from presentation.pages.music.music_library import FeaturedTracksSection
from presentation.pages.music.music_search import SearchResultsSection
from presentation.styles.colors import Colors, Spacing
from services.music import music_playback_service as events
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("music_page")
_LYRICS_TICK_MS = 300
_ERROR_TEXT = "Could not load results. Check your connection."


class MusicPage(BasePage):
    """MusicPage(parent, ctx, item=None, autoplay=False). `item` comes from the Dashboard."""

    def __init__(self, parent, ctx, item: Optional[MediaItem] = None, autoplay: bool = False) -> None:
        super().__init__(parent, ctx)
        self._service, self._playback, self._library = ctx.music_service, ctx.music_playback, ctx.library
        self._hearts = FavoriteTracker()
        self._favorite_ids: Set[str] = set()
        self._search_token = 0
        self._last_query = ""
        self._timer: Optional[str] = None

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        self._lyrics_panel = LyricsPanel(body, ctx, lambda: self._playback.set_lyrics_visible(False))
        # Plain holder frame: the lyrics panel is packed "before" it. (A CTkScrollableFrame cannot be
        # used for `before=` because packing it really packs its hidden outer frame.)
        self._main_holder = ctk.CTkFrame(body, fg_color="transparent")
        self._main_holder.pack(side="left", fill="both", expand=True)
        self._main = ctk.CTkScrollableFrame(self._main_holder, fg_color="transparent",
                                            scrollbar_button_color=Colors.BORDER,
                                            scrollbar_button_hover_color=Colors.HOVER)
        self._main.pack(fill="both", expand=True)
        content = ctk.CTkFrame(self._main, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)
        self._featured = FeaturedTracksSection(content, self._hearts, self._play, self._toggle_favorite)
        self._featured.pack(fill="x", pady=(0, Spacing.XL))
        self._results = SearchResultsSection(content, self._hearts, self._play, self._toggle_favorite)
        self._results.pack(fill="x")

        self._unsubscribe = self._playback.subscribe(self._on_playback_event)
        self._apply_lyrics_visibility()
        self._sync_current()
        self._tick_lyrics()
        self._start(item, autoplay)

    # ---------------------------------------------------------------- start up
    def _start(self, item: Optional[MediaItem], autoplay: bool) -> None:
        user = self.ctx.session_service.current_user
        library = self._library

        def work() -> Set[str]:
            return library.favorite_ids(user.id, MEDIA_MUSIC) if user else set()

        def done(ids, error) -> None:
            self._favorite_ids = ids if error is None and ids else set()
            self._load_featured()
            if item is not None:
                self._open_dashboard_item(item, autoplay)

        run_in_background(self, work, done)

    # ---------------------------------------------------------------- Featured
    def _load_featured(self) -> None:
        self._featured.show_loading()
        service = self._service
        run_in_background(self, service.featured, self._on_featured)

    def _on_featured(self, tracks: Optional[List[Track]], error: Optional[Exception]) -> None:
        if error is not None:
            logger.warning("Featured tracks failed: %s", error)
            self._featured.show_error(str(error) if isinstance(error, ApiError) else "Could not load featured tracks.",
                                      self._load_featured)
            return
        self._featured.show_tracks(tracks or [], self._favorite_ids)
        self._sync_current()

    # ---------------------------------------------------------------- Search
    def handle_search(self, query: str) -> bool:
        self._search(query)
        return True

    def _search(self, query: str) -> None:
        self._search_token += 1
        token, service = self._search_token, self._service
        self._last_query = query
        self._results.show_loading(query)
        run_in_background(self, lambda: service.search(query), lambda r, e: self._on_results(token, query, r, e))

    def _on_results(self, token: int, query: str, tracks: Optional[List[Track]], error: Optional[Exception]) -> None:
        if token != self._search_token:
            return  # a newer search replaced this one
        if error is not None:
            logger.warning("Search failed: %s", error)
            self._results.show_error(str(error) if isinstance(error, ApiError) else _ERROR_TEXT,
                                     lambda: self._search(query))
            return
        self._results.show_results(tracks or [], self._favorite_ids, query)
        self._sync_current()

    # ---------------------------------------------------------------- opened from the Dashboard
    def _open_dashboard_item(self, item: MediaItem, autoplay: bool) -> None:
        """Show the song (and similar ones) in Search Results; play it when the play button was used."""
        self._search_token += 1
        token, service = self._search_token, self._service
        query = f"{item.title} {item.subtitle}".strip()
        self._results.show_loading(query)

        def work():
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_lookup = pool.submit(self._lookup, item)
                f_related = pool.submit(self._related, query)
                return f_lookup.result(), f_related.result()

        run_in_background(self, work, lambda r, e: self._on_dashboard_item(token, item, query, autoplay, r, e))

    def _lookup(self, item: MediaItem) -> Optional[Track]:
        try:
            return self._service.lookup(item.external_id)
        except ApiError:
            return None

    def _related(self, query: str) -> List[Track]:
        try:
            return self._service.search(query)
        except ApiError:
            return []

    def _on_dashboard_item(self, token: int, item: MediaItem, query: str, autoplay: bool, result, error) -> None:
        if token != self._search_token or error is not None or result is None:
            return
        track, related = result
        track = track or Track(track_id=item.external_id, title=item.title, artist=item.subtitle,
                               artwork_url=item.image_url)
        tracks = [track] + [other for other in related if other.track_id != track.track_id]
        self._results.show_results(tracks, self._favorite_ids, query)
        if autoplay and not self._is_playing(track):
            self._playback.play_track(track, tracks)
        self._sync_current()

    def _is_playing(self, track: Track) -> bool:
        current = self._playback.current
        return current is not None and current.track_id == track.track_id and \
            self._playback.state in (events.STATE_PLAYING, events.STATE_LOADING)

    # ---------------------------------------------------------------- actions
    def _play(self, track: Track, queue: List[Track]) -> None:
        current = self._playback.current
        if current is not None and current.track_id == track.track_id:
            if self._playback.state in (events.STATE_PLAYING, events.STATE_PAUSED):
                self._playback.toggle_pause()  # clicking the current song pauses or resumes it
                return
            if self._playback.state == events.STATE_LOADING:
                return
        self._playback.play_track(track, queue)

    def _toggle_favorite(self, track: Track) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None:
            return None
        try:
            state = self._library.toggle_favorite(user.id, track.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._apply_favorite(track.track_id, state)
        self._playback.announce_favorite(track.track_id, state)
        return state

    def _apply_favorite(self, track_id: str, favorite: bool) -> None:
        if favorite:
            self._favorite_ids.add(track_id)
        else:
            self._favorite_ids.discard(track_id)
        self._hearts.update(MEDIA_MUSIC, track_id, favorite)

    # ---------------------------------------------------------------- playback events
    def _on_playback_event(self, event: str, payload) -> None:
        if event in (events.EVENT_TRACK, events.EVENT_STATE):
            self._sync_current()
            if event == events.EVENT_TRACK and self._playback.lyrics_visible:
                self._lyrics_panel.show_track(payload)
        elif event == events.EVENT_FAVORITE:
            self._apply_favorite(*payload)
        elif event == events.EVENT_LYRICS_VISIBLE:
            self._apply_lyrics_visibility()

    def _sync_current(self) -> None:
        current = self._playback.current
        track_id = current.track_id if current else None
        playing = self._playback.state in (events.STATE_PLAYING, events.STATE_LOADING)
        self._featured.set_current(track_id)
        self._results.set_current(track_id, playing)

    # ---------------------------------------------------------------- lyrics panel
    def _apply_lyrics_visibility(self) -> None:
        visible = self._playback.lyrics_visible
        if visible and not self._lyrics_panel.winfo_ismapped():
            self._lyrics_panel.pack(side="right", fill="y", padx=(0, Spacing.XL), pady=Spacing.XL, before=self._main_holder)
            self._lyrics_panel.show_track(self._playback.current)
        elif not visible:
            self._lyrics_panel.pack_forget()

    def _tick_lyrics(self) -> None:
        if self._playback.lyrics_visible and self._playback.state == events.STATE_PLAYING:
            self._lyrics_panel.refresh(self._playback.position_ms())
        self._timer = self.after(_LYRICS_TICK_MS, self._tick_lyrics)

    def destroy(self) -> None:
        """Clean up this page only. The music keeps playing."""
        if self._timer is not None:
            try:
                self.after_cancel(self._timer)
            except Exception:  # noqa: BLE001
                pass
            self._timer = None
        self._unsubscribe()
        super().destroy()
