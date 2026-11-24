"""Favorites page – saved items (music, movies, games) with filter tabs and grid of MediaCards."""
import threading
from typing import Dict, List, Optional, Set

import customtkinter as ctk

from app.navigation import Route
from config.constants import MEDIA_GAME, MEDIA_LABELS, MEDIA_MOVIE, MEDIA_MUSIC
from models.media import MediaItem
from presentation.components.cards import FavoriteTracker, MediaCard, SectionHeader
from presentation.components.dialogs import show_toast
from presentation.components.loaders import StateMessage
from presentation.pages.base_page import BasePage
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from presentation.styles.smooth_scroll import scroll_to_top
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("favorites_page")

_COLUMNS = 4
_FILTER_ALL = "all"
_FILTERS = (
    (_FILTER_ALL, "All"),
    (MEDIA_MUSIC, "Music"),
    (MEDIA_MOVIE, "Movies"),
    (MEDIA_GAME, "Games"),
)
_ACTION_LABELS = {
    MEDIA_MUSIC: "Play",
    MEDIA_MOVIE: "Play",
    MEDIA_GAME: "View",
}


class FavoritesPage(BasePage):
    """Grid of saved MediaItems with filter tabs and undo-able remove."""

    def __init__(self, parent, ctx, **_params) -> None:
        super().__init__(parent, ctx)
        self._library = ctx.library
        self._hearts = FavoriteTracker()
        self._active_filter = _FILTER_ALL
        self._all_items: List[MediaItem] = []
        self._filter_buttons: Dict[str, ctk.CTkButton] = {}
        self._load_token = 0
        self._pending_undo: Optional[MediaItem] = None

        self._build_ui()
        self._load()

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._scroll.pack(fill="both", expand=True)

        content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        # heading row
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.LG))
        self._heading = ctk.CTkLabel(
            header, text="Favorites",
            font=typography.title(), text_color=Colors.TEXT, anchor="w",
        )
        self._heading.pack(side="left")
        self._count_label = ctk.CTkLabel(
            header, text="",
            font=typography.body(), text_color=Colors.TEXT_SECONDARY, anchor="e",
        )
        self._count_label.pack(side="right")

        # filter chips
        chip_row = ctk.CTkFrame(content, fg_color="transparent")
        chip_row.pack(fill="x", pady=(0, Spacing.LG))
        for key, label in _FILTERS:
            btn = ctk.CTkButton(
                chip_row, text=label, font=typography.small(),
                height=Sizes.CHIP_BAR_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
                fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                text_color=Colors.TEXT_SECONDARY,
                border_width=1, border_color=Colors.BORDER,
                width=80,
                command=lambda k=key: self._select_filter(k),
            )
            btn.pack(side="left", padx=(0, Spacing.SM))
            self._filter_buttons[key] = btn

        # grid area
        self._grid_container = ctk.CTkFrame(content, fg_color="transparent")
        self._grid_container.pack(fill="x")
        self._state_msg: Optional[StateMessage] = None

        self._select_filter(_FILTER_ALL, force=True)

    # ------------------------------------------------------------------ filter

    def _select_filter(self, key: str, force: bool = False) -> None:
        if key == self._active_filter and not force:
            return
        self._active_filter = key
        for k, btn in self._filter_buttons.items():
            is_active = k == key
            btn.configure(
                fg_color=Colors.ACCENT if is_active else Colors.SURFACE,
                text_color=Colors.ON_ACCENT if is_active else Colors.TEXT_SECONDARY,
                border_color=Colors.ACCENT if is_active else Colors.BORDER,
            )
        self._render_grid()
        scroll_to_top(self._scroll)

    # ------------------------------------------------------------------ data

    def _load(self) -> None:
        self._load_token += 1
        token = self._load_token
        self._show_state("loading", "Loading favorites…")
        user = self.ctx.session_service.current_user
        library = self._library

        def work() -> List[MediaItem]:
            if user is None or library is None:
                return []
            from data.repositories.favorites_repository import FavoritesRepository
            repo = FavoritesRepository()
            return repo.list_for_user(user.id)

        def done(items: List[MediaItem], error) -> None:
            if token != self._load_token:
                return
            if not self._alive():
                return
            if error is not None:
                logger.error("Failed to load favorites: %s", error)
                self._show_state("error", "Could not load favorites.")
                return
            self._all_items = items or []
            self._render_grid()
        scroll_to_top(self._scroll)

        run_in_background(self, work, done)

    def _render_grid(self) -> None:
        if not self._alive():
            return
        self._clear(self._grid_container)
        if self._state_msg is not None:
            try:
                self._state_msg.destroy()
            except Exception:
                pass
            self._state_msg = None

        items = self._filtered_items()
        total = len(self._all_items)
        self._count_label.configure(
            text=f"{total} saved item{'s' if total != 1 else ''}"
        )

        if not items:
            msg = (
                "No favorites yet. Heart an item to save it here."
                if self._active_filter == _FILTER_ALL
                else f"No {MEDIA_LABELS.get(self._active_filter, '')} in your favorites."
            )
            self._show_state("empty", msg)
            return

        for col in range(_COLUMNS):
            self._grid_container.grid_columnconfigure(col, weight=1, uniform="fav_grid")

        user = self.ctx.session_service.current_user
        for idx, item in enumerate(items):
            action_label = _ACTION_LABELS.get(item.media_type, "Open")
            card = MediaCard(
                self._grid_container,
                item,
                image_size=Sizes.CARD_IMAGE_DEFAULT,
                aspect_ratio=(Sizes.POSTER_ASPECT if item.media_type == MEDIA_MOVIE else
                               Sizes.GAME_CARD_ASPECT if item.media_type == MEDIA_GAME else 1.0),
                tag=MEDIA_LABELS.get(item.media_type, ""),
                favorite=True,
                show_play=True,
                on_open=lambda i=item: self._on_open(i),
                on_play=lambda i=item: self._on_open(i),
                on_favorite=lambda i=item: self._on_remove(i),
            )
            row, col = divmod(idx, _COLUMNS)
            card.grid(
                row=row, column=col, sticky="nsew",
                padx=(0, Spacing.MD if col < _COLUMNS - 1 else 0),
                pady=(0, Spacing.MD),
            )
            self._hearts.track(card)

    # ------------------------------------------------------------------ helpers

    def _filtered_items(self) -> List[MediaItem]:
        if self._active_filter == _FILTER_ALL:
            return list(self._all_items)
        return [i for i in self._all_items if i.media_type == self._active_filter]

    def _show_state(self, kind: str, text: str) -> None:
        if self._state_msg is not None:
            try:
                self._state_msg.destroy()
            except Exception:
                pass
        self._state_msg = StateMessage(self._grid_container, kind=kind, text=text)
        self._state_msg.pack(fill="x", pady=Spacing.LG)

    def _clear(self, container: ctk.CTkFrame) -> None:
        for child in container.winfo_children():
            child.destroy()

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    # ------------------------------------------------------------------ actions

    def _on_remove(self, item: MediaItem) -> Optional[bool]:
        """Remove from favorites, show toast with Undo."""
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return None
        try:
            self._library._favorites.remove(user.id, item.media_type, item.external_id)
        except Exception as exc:
            logger.error("Failed to remove favorite: %s", exc)
            show_toast(self, "Could not remove from favorites.", "error")
            return None

        self._all_items = [i for i in self._all_items if not (
            i.media_type == item.media_type and i.external_id == item.external_id)]
        self._pending_undo = item
        self._hearts.update(item.media_type, item.external_id, False)
        self._render_grid()
        scroll_to_top(self._scroll)

        # Show toast with Undo – we build a custom approach using the existing show_toast
        # then place a separate undo link that re-adds the item
        self._show_remove_toast(item)
        return False

    def _show_remove_toast(self, item: MediaItem) -> None:
        """Show 'Removed from favorites' toast with an Undo link."""
        try:
            root = self.winfo_toplevel()
            # Destroy any existing toast
            old = getattr(root, "_kinetix_toast", None)
            if old is not None:
                try:
                    old.destroy()
                except Exception:
                    pass

            from presentation.components.dialogs import Toast
            toast = _UndoToast(root, item, self._undo_remove)
            toast.place(relx=1.0, rely=1.0, x=-Spacing.XL, y=-Spacing.XL, anchor="se")
            toast.lift()
            toast.schedule_close(5000)
            setattr(root, "_kinetix_toast", toast)
        except Exception as exc:
            logger.error("Failed to show undo toast: %s", exc)

    def _undo_remove(self, item: MediaItem) -> None:
        """Re-add a just-removed favorite."""
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return
        try:
            self._library._favorites.add(user.id, item)
        except Exception as exc:
            logger.error("Failed to undo remove: %s", exc)
            show_toast(self, "Could not restore favorite.", "error")
            return
        self._all_items.insert(0, item)
        self._hearts.update(item.media_type, item.external_id, True)
        self._pending_undo = None
        self._render_grid()
        scroll_to_top(self._scroll)
        show_toast(self, f"'{item.title}' restored to favorites.", "success")

    def _on_open(self, item: MediaItem) -> None:
        """Navigate to the right page with the item as a route parameter."""
        nav = self.ctx.navigator
        if item.media_type == MEDIA_MUSIC:
            nav.go(Route.MUSIC, item=item, autoplay=True)
        elif item.media_type == MEDIA_MOVIE:
            nav.go(Route.MOVIES, item=item, autoplay=False)
        elif item.media_type == MEDIA_GAME:
            nav.go(Route.GAMES, item=item)

    def handle_search(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            self._render_grid()
            scroll_to_top(self._scroll)
            return True
        self._clear(self._grid_container)
        results = [
            i for i in self._all_items
            if q in i.title.lower() or q in i.subtitle.lower()
            if self._active_filter == _FILTER_ALL or i.media_type == self._active_filter
        ]
        if not results:
            self._show_state("empty", f"No favorites match '{query}'.")
        else:
            for col in range(_COLUMNS):
                self._grid_container.grid_columnconfigure(col, weight=1, uniform="fav_search")
            for idx, item in enumerate(results):
                card = MediaCard(
                    self._grid_container, item,
                    image_size=Sizes.CARD_IMAGE_DEFAULT,
                    aspect_ratio=(Sizes.POSTER_ASPECT if item.media_type == MEDIA_MOVIE else
                                  Sizes.GAME_CARD_ASPECT if item.media_type == MEDIA_GAME else 1.0),
                    tag=MEDIA_LABELS.get(item.media_type, ""),
                    favorite=True,
                    show_play=True,
                    on_open=lambda i=item: self._on_open(i),
                    on_play=lambda i=item: self._on_open(i),
                    on_favorite=lambda i=item: self._on_remove(i),
                )
                row_idx, col = divmod(idx, _COLUMNS)
                card.grid(
                    row=row_idx, column=col, sticky="nsew",
                    padx=(0, Spacing.MD if col < _COLUMNS - 1 else 0),
                    pady=(0, Spacing.MD),
                )
        return True

    def destroy(self) -> None:
        self._load_token += 1
        super().destroy()


class _UndoToast(ctk.CTkFrame):
    """'Removed from favorites' toast with an Undo link."""

    def __init__(self, parent, item: MediaItem, on_undo):
        super().__init__(
            parent, fg_color=Colors.CARD,
            border_width=1, border_color=Colors.ACCENT,
            corner_radius=Sizes.CARD_RADIUS,
        )
        self._job: Optional[str] = None
        from presentation.styles import icons
        ctk.CTkLabel(self, text="", image=icons.icon("heart", Colors.ACCENT, 18)).pack(
            side="left", padx=(Spacing.MD, Spacing.SM), pady=Spacing.MD,
        )
        ctk.CTkLabel(
            self, text="Removed from favorites",
            font=typography.body(), text_color=Colors.TEXT, anchor="w",
        ).pack(side="left", padx=(0, Spacing.SM), pady=Spacing.MD)
        undo_lbl = ctk.CTkLabel(
            self, text="Undo", font=typography.body_bold(),
            text_color=Colors.ACCENT, cursor="hand2",
        )
        undo_lbl.pack(side="left", padx=(0, Spacing.LG), pady=Spacing.MD)
        undo_lbl.bind("<Button-1>", lambda _e: self._do_undo(item, on_undo))

    def _do_undo(self, item: MediaItem, on_undo) -> None:
        self.destroy()
        on_undo(item)

    def schedule_close(self, milliseconds: int) -> None:
        self._job = self.after(milliseconds, self.destroy)

    def destroy(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        try:
            super().destroy()
        except Exception:
            pass
