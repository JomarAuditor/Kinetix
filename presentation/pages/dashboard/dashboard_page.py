"""Dashboard: welcome, service cards, Featured, Recently Played and Favorites."""
from typing import Callable, List, Optional, Set, Tuple

import customtkinter as ctk

from app.navigation import Route
from config.constants import (DASHBOARD_FAVORITES_COUNT, DASHBOARD_FEATURED_COUNT, DASHBOARD_LIST_COUNT, MEDIA_GAME,
                              MEDIA_LABELS, MEDIA_MOVIE, MEDIA_MUSIC, MEDIA_TYPES)
from core.exceptions import KinetixError
from models.media import MediaItem
from presentation.components.cards import FavoriteTracker, MediaCard, MediaRow, SectionHeader
from presentation.components.dialogs import show_toast
from presentation.components.loaders import StateMessage
from presentation.pages.base_page import BasePage
from presentation.pages.dashboard.service_selector import ServiceSelector
from presentation.styles import typography
from presentation.styles.colors import Colors, Spacing
from utils.helpers import relative_time, run_in_background
from utils.logger import get_logger

logger = get_logger("dashboard")
_ROUTES = {MEDIA_MUSIC: Route.MUSIC, MEDIA_MOVIE: Route.MOVIES, MEDIA_GAME: Route.GAMES}
_EMPTY_LIST_TEXT = "Nothing here yet. Start exploring."


class DashboardPage(BasePage):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self._hearts = FavoriteTracker()
        self._favorite_keys: Set[Tuple[str, str]] = set()
        self._library_ready = False

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=Colors.BORDER,
                                        scrollbar_button_hover_color=Colors.HOVER)
        scroll.pack(fill="both", expand=True)
        content = ctk.CTkFrame(scroll, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        self._build_welcome(content)
        self._build_explore(content)
        self._featured_box = self._build_section(content, "Featured", "Curated recommendations")
        self._recent_header, self._recent_box, self._favorites_header, self._favorites_box = \
            self._build_library_sections(content)

        self._load_featured()
        self._load_library()

    # ---------------------------------------------------------------- layout
    def _build_welcome(self, parent) -> None:
        user = self.ctx.session_service.current_user
        name = user.first_name if user else ""
        ctk.CTkLabel(parent, text=f"Welcome back, {name}" if name else "Welcome back", font=typography.title(),
                     text_color=Colors.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(parent, text="Pick up where you left off or explore something new.", font=typography.body(),
                     text_color=Colors.TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(Spacing.XS, Spacing.XL))

    def _build_explore(self, parent) -> None:
        SectionHeader(parent, "Explore").pack(fill="x", pady=(0, Spacing.MD))
        ServiceSelector(parent, lambda route: self.ctx.navigator.go(route)).pack(fill="x", pady=(0, Spacing.XL))

    @staticmethod
    def _build_section(parent, title: str, right_text: str = "") -> ctk.CTkFrame:
        SectionHeader(parent, title, right_text).pack(fill="x", pady=(0, Spacing.MD))
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=(0, Spacing.XL))
        return box

    def _build_library_sections(self, parent):
        columns = ctk.CTkFrame(parent, fg_color="transparent")
        columns.pack(fill="x")
        for index in range(2):
            columns.grid_columnconfigure(index, weight=1, uniform="library")
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, Spacing.MD))
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=(Spacing.MD, 0))
        recent_header = SectionHeader(left, "Recently Played")
        recent_header.pack(fill="x", pady=(0, Spacing.MD))
        recent_box = ctk.CTkFrame(left, fg_color="transparent")
        recent_box.pack(fill="x")
        favorites_header = SectionHeader(right, "Favorites", "Quick access")
        favorites_header.pack(fill="x", pady=(0, Spacing.MD))
        favorites_box = ctk.CTkFrame(right, fg_color="transparent")
        favorites_box.pack(fill="x")
        return recent_header, recent_box, favorites_header, favorites_box

    # ---------------------------------------------------------------- states
    @staticmethod
    def _clear(box) -> None:
        for child in box.winfo_children():
            child.destroy()

    def _show_state(self, box, kind: str, text: str, retry: Optional[Callable[[], None]] = None) -> None:
        self._clear(box)
        StateMessage(box, kind, text, retry).pack(fill="x")

    # ---------------------------------------------------------------- Featured
    def _load_featured(self, force: bool = False) -> None:
        self._show_state(self._featured_box, "loading", "Loading featured content...")
        service = self.ctx.featured
        run_in_background(self, lambda: service.load(DASHBOARD_FEATURED_COUNT, force), self._on_featured)

    def _on_featured(self, result, error: Optional[Exception]) -> None:
        if error is not None or result is None:
            logger.warning("Featured failed: %s", error)
            self._show_state(self._featured_box, "error", "Could not load featured content.",
                             lambda: self._load_featured(True))
        elif result.items:
            self._build_featured(result.items)
        elif result.only_missing_keys:
            self._show_state(self._featured_box, "empty",
                             "Add your TMDB key to .env to see featured movies.")
        elif result.errors:
            self._show_state(self._featured_box, "error", "Could not load featured content. Check your connection.",
                             lambda: self._load_featured(True))
        else:
            self._show_state(self._featured_box, "empty", _EMPTY_LIST_TEXT)

    def _build_featured(self, items: List[MediaItem]) -> None:
        self._clear(self._featured_box)
        for index in range(DASHBOARD_FEATURED_COUNT):
            self._featured_box.grid_columnconfigure(index, weight=1, uniform="featured")
        for index, item in enumerate(items[:DASHBOARD_FEATURED_COUNT]):
            card = MediaCard(self._featured_box, item, tag=MEDIA_LABELS.get(item.media_type, ""),
                             favorite=(item.media_type, item.external_id) in self._favorite_keys,
                             show_play=item.media_type == MEDIA_MUSIC, on_open=self._open_item,
                             on_play=self._play_item, on_favorite=self._toggle_favorite)
            card.grid(row=0, column=index, sticky="nsew",
                      padx=(0, 0 if index == DASHBOARD_FEATURED_COUNT - 1 else Spacing.MD))
            self._hearts.track(card)

    # ---------------------------------------------------------------- Recently Played + Favorites
    def _load_library(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None:
            return
        self._show_state(self._recent_box, "loading", "Loading...")
        self._show_state(self._favorites_box, "loading", "Loading...")
        library = self.ctx.library

        def work():
            recent = library.latest_history(user.id, DASHBOARD_LIST_COUNT)
            favorites = library.latest_favorites(user.id, DASHBOARD_FAVORITES_COUNT)
            keys = {(kind, ext_id) for kind in MEDIA_TYPES for ext_id in library.favorite_ids(user.id, kind)}
            return recent, favorites, keys

        run_in_background(self, work, self._on_library)

    def _on_library(self, result, error: Optional[Exception]) -> None:
        if error is not None or result is None:
            logger.warning("Library load failed: %s", error)
            self._show_state(self._recent_box, "error", "Could not load history.", self._load_library)
            self._show_state(self._favorites_box, "error", "Could not load favorites.", self._load_library)
            return
        recent, favorites, keys = result
        self._favorite_keys = keys
        self._library_ready = True
        self._build_recent(recent)
        self._build_favorites(favorites)
        for media_type, external_id in keys:  # featured cards may have been built before this finished
            self._hearts.update(media_type, external_id, True)

    def _build_recent(self, items: List[MediaItem]) -> None:
        self._clear(self._recent_box)
        self._recent_header.set_right_text(f"{len(items)} items" if items else "")
        if not items:
            self._show_state(self._recent_box, "empty", _EMPTY_LIST_TEXT)
            return
        for item in items:
            row = MediaRow(self._recent_box, item, tag=MEDIA_LABELS.get(item.media_type, ""),
                           time_text=relative_time(item.timestamp), action_icon="play",
                           on_action=self._play_item, on_open=self._open_item)
            row.pack(fill="x", pady=(0, Spacing.SM))

    def _build_favorites(self, items: List[MediaItem]) -> None:
        self._clear(self._favorites_box)
        if not items:
            self._show_state(self._favorites_box, "empty", _EMPTY_LIST_TEXT)
            return
        for column in range(2):
            self._favorites_box.grid_columnconfigure(column, weight=1, uniform="favorites")
        for index, item in enumerate(items):
            row = MediaRow(self._favorites_box, item, compact=True, favorite=True, on_favorite=self._toggle_favorite,
                           action_icon=None, on_open=self._open_item)
            row.grid(row=index // 2, column=index % 2, sticky="ew",
                     padx=(0, Spacing.SM) if index % 2 == 0 else (Spacing.SM, 0), pady=(0, Spacing.SM))
            self._hearts.track(row)

    # ---------------------------------------------------------------- actions
    def _open_item(self, item: MediaItem) -> None:
        self.ctx.navigator.go(_ROUTES.get(item.media_type, Route.HOME), item=item)

    def _play_item(self, item: MediaItem) -> None:
        self.ctx.navigator.go(_ROUTES.get(item.media_type, Route.HOME), item=item, autoplay=True)

    def _toggle_favorite(self, item: MediaItem) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None:
            return None
        try:
            state = self.ctx.library.toggle_favorite(user.id, item)
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        key = (item.media_type, item.external_id)
        self._favorite_keys.add(key) if state else self._favorite_keys.discard(key)
        self._hearts.update(item.media_type, item.external_id, state)
        if item.media_type == MEDIA_MUSIC and self.ctx.music_playback is not None:
            self.ctx.music_playback.announce_favorite(item.external_id, state)
        self._refresh_favorites(user.id)
        return state

    def _refresh_favorites(self, user_id: int) -> None:
        """Reload the Favorites list after a heart changed (done in the background, after the click ends)."""
        library = self.ctx.library
        run_in_background(self, lambda: library.latest_favorites(user_id, DASHBOARD_FAVORITES_COUNT),
                          lambda items, error: self._build_favorites(items) if error is None else None)
