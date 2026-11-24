"""Recently Played page – history rows grouped by Today/Yesterday/Earlier with filter tabs."""
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

import customtkinter as ctk

from app.navigation import Route
from config.constants import MEDIA_GAME, MEDIA_LABELS, MEDIA_MOVIE, MEDIA_MUSIC, MEDIA_TYPES
from models.media import MediaItem
from presentation.components.cards import FavoriteTracker, MediaRow, SectionHeader
from presentation.components.dialogs import ConfirmDialog, show_toast
from presentation.components.loaders import StateMessage
from presentation.pages.base_page import BasePage
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from presentation.styles.smooth_scroll import scroll_to_top
from utils.helpers import relative_time, run_in_background
from utils.logger import get_logger

logger = get_logger("recent_page")

_FILTER_ALL = "all"
_FILTERS = (
    (_FILTER_ALL, "All"),
    (MEDIA_MUSIC, "Music"),
    (MEDIA_MOVIE, "Movies"),
    (MEDIA_GAME, "Games"),
)
_HISTORY_LIMIT = 50
_ACTION_ICONS = {MEDIA_MUSIC: "play", MEDIA_MOVIE: "play", MEDIA_GAME: "games"}


def _group_key(timestamp: str) -> str:
    """Return 'Today', 'Yesterday', or 'Earlier'."""
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(timestamp, pattern).replace(tzinfo=timezone.utc)
            dt_local = dt.astimezone()
            today = date.today()
            delta = (today - dt_local.date()).days
            if delta == 0:
                return "Today"
            if delta == 1:
                return "Yesterday"
            return "Earlier"
        except (ValueError, TypeError):
            continue
    return "Earlier"


class RecentPage(BasePage):
    """History rows grouped by date with filter tabs and a Clear History button."""

    def __init__(self, parent, ctx, **_params) -> None:
        super().__init__(parent, ctx)
        self._library = ctx.library
        self._hearts = FavoriteTracker()
        self._favorite_keys: set = set()
        self._active_filter = _FILTER_ALL
        self._all_items: List[MediaItem] = []
        self._filter_buttons: Dict[str, ctk.CTkButton] = {}
        self._load_token = 0

        self._build_ui()
        self._load()

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._scroll.pack(fill="both", expand=True)

        content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        # heading row
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(
            header, text="Recently Played",
            font=typography.title(), text_color=Colors.TEXT, anchor="w",
        ).pack(side="left")
        self._clear_btn = ctk.CTkButton(
            header, text="Clear History", font=typography.small(),
            height=Sizes.CHIP_BAR_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
            fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
            text_color=Colors.TEXT_SECONDARY,
            border_width=1, border_color=Colors.BORDER,
            width=120,
            command=self._confirm_clear,
        )
        self._clear_btn.pack(side="right")

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

        # rows area
        self._rows_container = ctk.CTkFrame(content, fg_color="transparent")
        self._rows_container.pack(fill="x")
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
        self._render_rows()
        scroll_to_top(self._scroll)

    # ------------------------------------------------------------------ data

    def _load(self) -> None:
        self._load_token += 1
        token = self._load_token
        self._show_state("loading", "Loading history…")
        user = self.ctx.session_service.current_user
        library = self._library

        def work():
            if user is None or library is None:
                return [], set()
            from data.repositories.history_repository import HistoryRepository
            repo = HistoryRepository()
            items = repo.list_for_user(user.id, limit=_HISTORY_LIMIT)
            keys = {(kind, ext_id) for kind in MEDIA_TYPES for ext_id in library.favorite_ids(user.id, kind)}
            return items, keys

        def done(result, error) -> None:
            if token != self._load_token:
                return
            if not self._alive():
                return
            if error is not None:
                logger.error("Failed to load history: %s", error)
                self._show_state("error", "Could not load history.")
                return
            items, keys = result or ([], set())
            self._all_items = items or []
            self._favorite_keys = keys or set()
            self._render_rows()
        scroll_to_top(self._scroll)

        run_in_background(self, work, done)

    # ------------------------------------------------------------------ render

    def _render_rows(self) -> None:
        if not self._alive():
            return
        self._hearts.clear()
        self._clear(self._rows_container)
        if self._state_msg is not None:
            try:
                self._state_msg.destroy()
            except Exception:
                pass
            self._state_msg = None

        items = self._filtered_items()

        if not items:
            msg = (
                "Nothing here yet. Play some music, watch a movie, or try a game."
                if self._active_filter == _FILTER_ALL
                else f"No {MEDIA_LABELS.get(self._active_filter, '')} in your history."
            )
            self._show_state("empty", msg)
            return

        # Group by Today / Yesterday / Earlier
        groups: Dict[str, List[MediaItem]] = {"Today": [], "Yesterday": [], "Earlier": []}
        for item in items:
            groups[_group_key(item.timestamp)].append(item)

        for group_name in ("Today", "Yesterday", "Earlier"):
            group_items = groups[group_name]
            if not group_items:
                continue
            SectionHeader(self._rows_container, group_name, chip_text=str(len(group_items))).pack(
                fill="x", pady=(Spacing.MD, Spacing.SM),
            )
            for item in group_items:
                self._build_row(item)

    def _build_row(self, item: MediaItem) -> None:
        """Build a single MediaRow for the history item."""
        is_fav = (item.media_type, item.external_id) in self._favorite_keys

        tag = MEDIA_LABELS.get(item.media_type, "")
        time_text = relative_time(item.timestamp)
        action_icon = _ACTION_ICONS.get(item.media_type, "play")

        row = MediaRow(
            self._rows_container,
            item,
            tag=tag,
            time_text=time_text,
            favorite=is_fav,
            on_favorite=lambda i=item: self._toggle_favorite(i),
            action_icon=action_icon,
            action_style="outline",
            on_action=lambda i=item: self._on_open(i),
            on_open=lambda i=item: self._on_open(i),
        )
        row.pack(fill="x", pady=(0, Spacing.SM))
        self._hearts.track(row)

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
        self._state_msg = StateMessage(self._rows_container, kind=kind, text=text)
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

    def _on_open(self, item: MediaItem) -> None:
        nav = self.ctx.navigator
        if item.media_type == MEDIA_MUSIC:
            nav.go(Route.MUSIC, item=item, autoplay=True)
        elif item.media_type == MEDIA_MOVIE:
            nav.go(Route.MOVIES, item=item, autoplay=False)
        elif item.media_type == MEDIA_GAME:
            nav.go(Route.GAMES, item=item)

    def _toggle_favorite(self, item: MediaItem) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return None
        try:
            state = self._library.toggle_favorite(user.id, item)
        except Exception as exc:
            logger.error("Failed to toggle favorite: %s", exc)
            show_toast(self, "Could not update favorites.", "error")
            return None
        key = (item.media_type, item.external_id)
        if state:
            self._favorite_keys.add(key)
        else:
            self._favorite_keys.discard(key)
        self._hearts.update(item.media_type, item.external_id, state)
        return state

    def _confirm_clear(self) -> None:
        ConfirmDialog(
            self,
            "Clear History?",
            "This will remove all items from your recently played list. "
            "Your favorites will not be affected.",
            confirm_text="Clear History",
            danger=True,
            on_confirm=self._clear_history,
        )

    def _clear_history(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None:
            return
        try:
            from data.repositories.history_repository import HistoryRepository
            HistoryRepository().clear(user.id)
        except Exception as exc:
            logger.error("Failed to clear history: %s", exc)
            show_toast(self, "Could not clear history.", "error")
            return
        self._all_items = []
        self._render_rows()
        scroll_to_top(self._scroll)
        show_toast(self, "History cleared.", "success")

    def handle_search(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            self._render_rows()
            scroll_to_top(self._scroll)
            return True
        self._hearts.clear()
        self._clear(self._rows_container)
        if self._state_msg is not None:
            try:
                self._state_msg.destroy()
            except Exception:
                pass
            self._state_msg = None
        results = [
            i for i in self._all_items
            if (q in i.title.lower() or q in i.subtitle.lower())
            and (self._active_filter == _FILTER_ALL or i.media_type == self._active_filter)
        ]
        if not results:
            self._show_state("empty", f"No history matches '{query}'.")
        else:
            for item in results:
                self._build_row(item)
        return True

    def destroy(self) -> None:
        self._load_token += 1
        super().destroy()
