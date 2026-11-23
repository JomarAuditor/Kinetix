"""Games page: live API-backed playable games (Open Trivia DB, Deck of Cards, Datamuse Word API)."""
from typing import Dict, List, Optional, Set

import customtkinter as ctk

from config.constants import MEDIA_GAME
from core.exceptions import ApiError, KinetixError
from models.game import GameItem
from models.media import MediaItem
from presentation.components.cards import FavoriteTracker, MediaCard, SectionHeader
from presentation.components.dialogs import show_toast
from presentation.components.loaders import StateMessage
from presentation.pages.base_page import BasePage
from presentation.pages.games.game_details import GamePlayView
from presentation.pages.games.game_search import GameSearchSection
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from services.games.game_service import GameService
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("games_page")

_COLUMNS = 4
_ERROR_TEXT = "Could not load games. Check your internet connection."

_CATEGORIES = (
    ("all", "All Games"),
    ("Arcade", "Arcade"),
    ("Trivia", "Trivia"),
    ("Cards", "Cards"),
    ("Words", "Words"),
)


class GamesPage(BasePage):
    """Browse, search, favorite, and play API-powered games directly inside Kinetix."""

    def __init__(
        self,
        parent,
        ctx,
        item: Optional[MediaItem] = None,
        autoplay: bool = False,
        **_params,
    ) -> None:
        super().__init__(parent, ctx)
        self._service: GameService = ctx.game_service or GameService()
        self._library = ctx.library
        self._hearts = FavoriteTracker()
        self._favorite_ids: Set[str] = set()
        self._active_category = "all"
        self._catalog_token = 0
        self._search_token = 0
        self._route_token = 0
        self._play_view: Optional[GamePlayView] = None
        self._category_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_browse_view()
        self._load_favorites_and_start(item, autoplay)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_browse_view(self) -> None:
        self._browse_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._browse_scroll.pack(fill="both", expand=True)

        self._browse_content = ctk.CTkFrame(self._browse_scroll, fg_color="transparent")
        self._browse_content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        header = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(
            header, text="Games", font=typography.title(),
            text_color=Colors.TEXT, anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            header, text="Play live API-powered games right inside Kinetix",
            font=typography.small(), text_color=Colors.TEXT_MUTED, anchor="e",
        ).pack(side="right")

        SectionHeader(self._browse_content, "Featured Games", "4 playable picks").pack(
            fill="x", pady=(0, Spacing.MD),
        )
        self._featured_box = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        self._featured_box.pack(fill="x", pady=(0, Spacing.XL))

        self._search_section = GameSearchSection(
            self._browse_content,
            self._hearts,
            on_play=self._open_game,
            on_favorite=self._toggle_favorite,
        )

        cat_bar = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        cat_bar.pack(fill="x", pady=(0, Spacing.MD))
        self._catalog_header = SectionHeader(cat_bar, "Playable Games")
        self._catalog_header.pack(side="left", fill="x", expand=True)

        chips = ctk.CTkFrame(cat_bar, fg_color="transparent")
        chips.pack(side="right")
        for key, label in _CATEGORIES:
            btn = ctk.CTkButton(
                chips, text=label, font=typography.small(),
                height=Sizes.CHIP_BAR_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
                fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                text_color=Colors.TEXT_SECONDARY, border_width=1, border_color=Colors.BORDER,
                width=84,
                command=lambda k=key: self._select_category(k),
            )
            btn.pack(side="left", padx=(Spacing.SM, 0))
            self._category_buttons[key] = btn

        self._catalog_box = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        self._catalog_box.pack(fill="x")

        self._route_loader = ctk.CTkFrame(self, fg_color="transparent")

    # ------------------------------------------------------------------
    # Startup & Routing
    # ------------------------------------------------------------------

    def _load_favorites_and_start(self, item: Optional[MediaItem], autoplay: bool) -> None:
        self._render_featured()
        self._select_category("all", force=True)
        if item is not None:
            self._open_routed_item(item, autoplay)

        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return

        def work() -> Set[str]:
            return self._library.favorite_ids(user.id, MEDIA_GAME)

        def done(ids, error) -> None:
            if not self._alive() or error is not None or not ids:
                return
            self._favorite_ids = ids
            for ext_id in ids:
                self._hearts.update(MEDIA_GAME, ext_id, True)

        run_in_background(self, work, done)

    def _open_routed_item(self, item: MediaItem, _autoplay: bool) -> None:
        self._route_token += 1
        token = self._route_token
        self._show_route_loading(f'Loading "{item.title}"...')

        run_in_background(
            self,
            lambda: self._service.get_game(item.external_id),
            lambda g, e: self._on_routed_done(token, item, g, e),
        )

    def _on_routed_done(
        self,
        token: int,
        item: MediaItem,
        game: Optional[GameItem],
        error: Optional[Exception],
    ) -> None:
        if token != self._route_token or not self._alive():
            return
        self._hide_route_loading()
        if error is not None or game is None:
            show_toast(self, f'"{item.title}" is no longer available.', "info", 3500)
            return
        self._open_game(game)

    def _show_route_loading(self, text: str) -> None:
        self._browse_scroll.pack_forget()
        self._clear(self._route_loader)
        StateMessage(self._route_loader, "loading", text).pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)
        self._route_loader.pack(fill="both", expand=True)

    def _hide_route_loading(self) -> None:
        self._route_loader.pack_forget()
        self._clear(self._route_loader)
        if self._play_view is None and not self._browse_scroll.winfo_ismapped():
            self._browse_scroll.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def handle_search(self, query: str) -> bool:
        query = query.strip()
        if self._play_view is not None:
            self._close_game()
        if not query:
            self._search_section.pack_forget()
            return True

        self._search_token += 1
        token = self._search_token
        self._search_section.pack(fill="x", pady=(0, Spacing.XL), after=self._featured_box)
        self._search_section.show_loading(query)

        run_in_background(
            self,
            lambda: self._service.search(query),
            lambda r, e: self._on_search_done(token, query, r, e),
        )
        return True

    def _on_search_done(
        self,
        token: int,
        query: str,
        games: Optional[List[GameItem]],
        error: Optional[Exception],
    ) -> None:
        if token != self._search_token or not self._alive():
            return
        if error is not None:
            msg = str(error) if isinstance(error, ApiError) else _ERROR_TEXT
            self._search_section.show_error(msg, lambda: self.handle_search(query))
            return
        self._search_section.show_results(games or [], self._favorite_ids, query)

    # ------------------------------------------------------------------
    # Featured & Catalog
    # ------------------------------------------------------------------

    def _render_featured(self) -> None:
        self._clear(self._featured_box)
        games = self._service.featured_games(limit=4)
        self._render_grid(self._featured_box, games, spotlight_first=True)

    def _select_category(self, category: str, force: bool = False) -> None:
        if category == self._active_category and not force:
            return
        self._active_category = category
        for key, btn in self._category_buttons.items():
            if key == category:
                btn.configure(fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
                              text_color=Colors.ON_ACCENT, border_color=Colors.ACCENT)
            else:
                btn.configure(fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                              text_color=Colors.TEXT_SECONDARY, border_color=Colors.BORDER)
        self._load_catalog(category)

    def _load_catalog(self, category: str) -> None:
        self._catalog_token += 1
        token = self._catalog_token
        if self._service.is_catalog_cached:
            self._on_catalog_done(token, category, self._service.discover_games(category), None)
            return
        self._clear(self._catalog_box)
        StateMessage(self._catalog_box, "loading", "Loading live game modes...").pack(fill="x")

        run_in_background(
            self,
            lambda: self._service.discover_games(category),
            lambda r, e: self._on_catalog_done(token, category, r, e),
        )

    def _on_catalog_done(
        self,
        token: int,
        category: str,
        games: Optional[List[GameItem]],
        error: Optional[Exception],
    ) -> None:
        if token != self._catalog_token or not self._alive():
            return
        self._clear(self._catalog_box)
        if error is not None:
            msg = str(error) if isinstance(error, ApiError) else _ERROR_TEXT
            StateMessage(self._catalog_box, "error", msg, lambda: self._load_catalog(category)).pack(fill="x")
            return
        if not games:
            StateMessage(self._catalog_box, "empty", "No games available in this category.").pack(fill="x")
            return
        self._catalog_header.set_chip(f"{len(games)} games")
        self._render_grid(self._catalog_box, games, spotlight_first=False)

    def _render_grid(self, container: ctk.CTkFrame, games: List[GameItem], spotlight_first: bool) -> None:
        for col in range(_COLUMNS):
            container.grid_columnconfigure(col, weight=1, uniform=f"games_{id(container)}")

        for idx, game in enumerate(games):
            item = game.to_media_item()
            tag = "Spotlight" if (spotlight_first and idx == 0) else game.category
            card = MediaCard(
                container,
                item,
                image_size=Sizes.CARD_IMAGE_DEFAULT,
                aspect_ratio=Sizes.GAME_CARD_ASPECT,
                tag=tag,
                favorite=game.game_id in self._favorite_ids,
                show_play=True,
                on_open=lambda _i, g=game: self._open_game(g),
                on_play=lambda _i, g=game: self._open_game(g),
                on_favorite=lambda _i, g=game: self._toggle_favorite(g),
            )
            row, col = divmod(idx, _COLUMNS)
            card.grid(
                row=row, column=col, sticky="nsew",
                padx=(0, Spacing.MD if col < _COLUMNS - 1 else 0),
                pady=(0, Spacing.MD),
            )
            self._hearts.track(card)

    # ------------------------------------------------------------------
    # Play Arena Navigation
    # ------------------------------------------------------------------

    def _open_game(self, game: GameItem) -> None:
        self._close_game()
        self._browse_scroll.pack_forget()
        self._route_loader.pack_forget()

        self._play_view = GamePlayView(
            self,
            self.ctx,
            game,
            is_favorite=game.game_id in self._favorite_ids,
            on_back=self._close_game,
            on_favorite_changed=self._on_favorite_changed,
        )
        self._play_view.pack(fill="both", expand=True)

    def _close_game(self) -> None:
        if self._play_view is not None:
            self._play_view.destroy()
            self._play_view = None
        if not self._browse_scroll.winfo_ismapped():
            self._browse_scroll.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Favorites & Helpers
    # ------------------------------------------------------------------

    def _toggle_favorite(self, game: GameItem) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return None
        try:
            state = self._library.toggle_favorite(user.id, game.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._on_favorite_changed(game.game_id, state)
        return state

    def _on_favorite_changed(self, ext_id: str, state: bool) -> None:
        if state:
            self._favorite_ids.add(ext_id)
        else:
            self._favorite_ids.discard(ext_id)
        self._hearts.update(MEDIA_GAME, ext_id, state)

    @staticmethod
    def _clear(container: ctk.CTkFrame) -> None:
        for child in container.winfo_children():
            child.destroy()

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:  # noqa: BLE001
            return False

    def destroy(self) -> None:
        self._catalog_token += 1
        self._search_token += 1
        self._route_token += 1
        super().destroy()
