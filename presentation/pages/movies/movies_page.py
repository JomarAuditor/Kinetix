"""Movies page: featured banner, category chips, 2:3 poster grid, search, and details view."""
from typing import Dict, List, Optional, Set

import customtkinter as ctk

from config.constants import MEDIA_MOVIE
from config.movie_channels import MOVIE_CATEGORIES
from core.exceptions import ApiError, KinetixError, MissingApiKeyError
from models.media import MediaItem
from models.movie import MatchedMovie
from presentation.components.buttons import PrimaryButton, SecondaryButton
from presentation.components.cards import Chip, FavoriteTracker, MediaCard, SectionHeader
from presentation.components.dialogs import show_toast
from presentation.components.images import ImageView
from presentation.components.loaders import StateMessage
from presentation.pages.base_page import BasePage
from presentation.pages.movies.movie_details import MovieDetailsView
from presentation.pages.movies.movie_search import MovieSearchSection
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing
from services.movies.movie_service import MovieService
from utils import image_cache
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("movies_page")

_GRID_COLUMNS = 4
_CATEGORY_LIMIT = 12
_SEARCH_LIMIT = 12
_CAROUSEL_INTERVAL_MS = 6000
_MISSING_KEY_TEXT = "Add your TMDB key in .env"
_ERROR_TEXT = "Could not load movies. Check your internet connection."

_CATEGORY_ORDER = (
    ("popular", "Popular"),
    ("action", "Action"),
    ("horror", "Horror"),
    ("classics", "Classics"),
    ("western", "Western"),
    ("family", "Family"),
    ("asian", "Asian"),
    ("bollywood", "Bollywood"),
)


class MoviesPage(BasePage):
    """Movies discovery, search, details, and embedded VLC playback."""

    def __init__(
        self,
        parent,
        ctx,
        item: Optional[MediaItem] = None,
        autoplay: bool = False,
        matched_movie: Optional[MatchedMovie] = None,
        **_params,
    ) -> None:
        super().__init__(parent, ctx)
        self._service: MovieService = ctx.movie_service or MovieService()
        self._library = ctx.library
        self._hearts = FavoriteTracker()
        self._favorite_ids: Set[str] = set()
        self._active_category = "popular"
        self._catalog_token = 0
        self._search_token = 0
        self._route_token = 0
        self._featured_movie: Optional[MatchedMovie] = None
        self._carousel_items: List[MatchedMovie] = []
        self._carousel_index = 0
        self._carousel_job: Optional[str] = None
        self._slide_anim_job: Optional[str] = None
        self._details_view: Optional[MovieDetailsView] = None
        self._category_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_browse_view()
        self._load_favorites_and_start(item, autoplay, matched_movie)

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

        # Page header
        header = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(
            header, text="Movies", font=typography.title(),
            text_color=Colors.TEXT, anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            header, text="Free full-length movies from verified official channels",
            font=typography.small(), text_color=Colors.TEXT_MUTED, anchor="w",
        ).pack(side="left", padx=(Spacing.MD, 0))

        # Featured banner container
        self._banner_box = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        self._banner_box.pack(fill="x", pady=(0, Spacing.XL))

        # Search results (hidden until a query is entered in the TopBar)
        self._search_section = MovieSearchSection(
            self._browse_content,
            self._hearts,
            on_open=lambda m: self._open_details(m, autoplay=False),
            on_play=lambda m: self._open_details(m, autoplay=True),
            on_favorite=self._toggle_favorite,
        )

        # Category filter chips
        chips_bar = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        chips_bar.pack(fill="x", pady=(0, Spacing.LG))
        for key, label in _CATEGORY_ORDER:
            if key not in MOVIE_CATEGORIES:
                continue
            btn = ctk.CTkButton(
                chips_bar, text=label, font=typography.small(),
                height=Sizes.CHIP_BAR_HEIGHT, corner_radius=Sizes.CHIP_BAR_HEIGHT // 2,
                fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                text_color=Colors.TEXT_SECONDARY, border_width=1, border_color=Colors.BORDER,
                width=84,
                command=lambda k=key: self._select_category(k),
            )
            btn.pack(side="left", padx=(0, Spacing.SM))
            self._category_buttons[key] = btn

        # Catalog header + grid
        self._grid_header = SectionHeader(self._browse_content, "Popular Free Movies")
        self._grid_header.pack(fill="x", pady=(0, Spacing.MD))

        self._grid_box = ctk.CTkFrame(self._browse_content, fg_color="transparent")
        self._grid_box.pack(fill="x")

        # Route item loading overlay frame (shown when resolving a Dashboard/Favorites click)
        self._route_loader = ctk.CTkFrame(self, fg_color="transparent")

    # ------------------------------------------------------------------
    # Startup & Route Handling
    # ------------------------------------------------------------------

    def _load_favorites_and_start(
        self,
        item: Optional[MediaItem],
        autoplay: bool,
        matched_movie: Optional[MatchedMovie],
    ) -> None:
        user = self.ctx.session_service.current_user

        def work() -> Set[str]:
            if user is None or self._library is None:
                return set()
            return self._library.favorite_ids(user.id, MEDIA_MOVIE)

        def done(ids, error) -> None:
            self._favorite_ids = ids if error is None and ids else set()
            self._select_category("popular", force=True)
            if matched_movie is not None:
                self._open_details(matched_movie, autoplay=autoplay)
            elif item is not None:
                self._open_routed_item(item, autoplay=autoplay)

        run_in_background(self, work, done)

    def _open_routed_item(self, item: MediaItem, autoplay: bool) -> None:
        """Resolve a MediaItem passed from Dashboard, Favorites, or Recently Played."""
        self._route_token += 1
        token = self._route_token
        self._show_route_loading(f'Loading "{item.title}"...')

        def work():
            return self._service.resolve_media_item(item)

        def done(matched: Optional[MatchedMovie], error: Optional[Exception]) -> None:
            if token != self._route_token or not self._alive():
                return
            self._hide_route_loading()
            if isinstance(error, MissingApiKeyError):
                show_toast(self, _MISSING_KEY_TEXT, "error", 5000)
                return
            if error is not None or matched is None:
                show_toast(self, f'Could not load details for "{item.title}".', "error", 4000)
                return
            if autoplay and not matched.is_playable:
                show_toast(
                    self,
                    f'No verified free stream is currently available for "{matched.movie.title}".',
                    "info", 5000,
                )
            self._open_details(matched, autoplay=autoplay and matched.is_playable)

        run_in_background(self, work, done)

    def _show_route_loading(self, text: str) -> None:
        self._browse_scroll.pack_forget()
        self._clear(self._route_loader)
        StateMessage(self._route_loader, "loading", text).pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)
        self._route_loader.pack(fill="both", expand=True)

    def _hide_route_loading(self) -> None:
        self._route_loader.pack_forget()
        self._clear(self._route_loader)
        if self._details_view is None and not self._browse_scroll.winfo_ismapped():
            self._browse_scroll.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Search (TopBar routes here)
    # ------------------------------------------------------------------

    def handle_search(self, query: str) -> bool:
        query = query.strip()
        if self._details_view is not None:
            self._close_details()
        if not query:
            self._search_section.pack_forget()
            return True

        self._search_token += 1
        token = self._search_token
        self._search_section.pack(fill="x", pady=(0, Spacing.XL), after=self._banner_box)
        self._search_section.show_loading(query)

        run_in_background(
            self,
            lambda: self._service.search_official_channels(query, limit=_SEARCH_LIMIT),
            lambda r, e: self._on_search_done(token, query, r, e),
        )
        return True

    def _on_search_done(
        self,
        token: int,
        query: str,
        movies: Optional[List[MatchedMovie]],
        error: Optional[Exception],
    ) -> None:
        if token != self._search_token or not self._alive():
            return
        if error is not None:
            if isinstance(error, MissingApiKeyError):
                self._search_section.show_error(_MISSING_KEY_TEXT)
            else:
                msg = str(error) if isinstance(error, ApiError) else _ERROR_TEXT
                self._search_section.show_error(msg, lambda: self.handle_search(query))
            return
        self._search_section.show_results(movies or [], self._favorite_ids, query)

    # ------------------------------------------------------------------
    # Categories & Catalog Grid
    # ------------------------------------------------------------------

    def _select_category(self, key: str, force: bool = False) -> None:
        if key == self._active_category and not force:
            return
        self._active_category = key
        for k, btn in self._category_buttons.items():
            if k == key:
                btn.configure(fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
                              text_color=Colors.ON_ACCENT, border_color=Colors.ACCENT)
            else:
                btn.configure(fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                              text_color=Colors.TEXT_SECONDARY, border_color=Colors.BORDER)

        cat_name = MOVIE_CATEGORIES.get(key, {}).get("name", "Movies")
        self._grid_header.set_title(cat_name)
        self._grid_header.set_chip("")
        self._load_category(key)

    def _load_category(self, key: str) -> None:
        self._catalog_token += 1
        token = self._catalog_token
        self._clear(self._grid_box)
        StateMessage(self._grid_box, "loading", "Loading free movies...").pack(fill="x")
        if key == "popular" and self._featured_movie is None:
            self._clear(self._banner_box)
            StateMessage(self._banner_box, "loading", "Loading featured movie...").pack(fill="x")

        run_in_background(
            self,
            lambda: self._service.discover_from_official_channels(key, limit=_CATEGORY_LIMIT),
            lambda r, e: self._on_category_done(key, token, r, e),
        )

    def _on_category_done(
        self,
        key: str,
        token: int,
        movies: Optional[List[MatchedMovie]],
        error: Optional[Exception],
    ) -> None:
        if token != self._catalog_token or not self._alive():
            return
        self._clear(self._grid_box)

        if error is not None:
            if isinstance(error, MissingApiKeyError):
                self._clear(self._banner_box)
                StateMessage(self._grid_box, "error", _MISSING_KEY_TEXT).pack(fill="x")
            else:
                msg = str(error) if isinstance(error, ApiError) else _ERROR_TEXT
                StateMessage(self._grid_box, "error", msg, lambda: self._load_category(key)).pack(fill="x")
                if key == "popular" and self._featured_movie is None:
                    self._clear(self._banner_box)
            return

        if not movies:
            StateMessage(self._grid_box, "empty", "No movies available in this category right now.").pack(fill="x")
            if key == "popular" and self._featured_movie is None:
                self._clear(self._banner_box)
            return

        if key == "popular":
            playable = [m for m in movies if m.is_playable] or movies
            self._carousel_items = playable
            self._carousel_index = 0
            self._featured_movie = self._carousel_items[0]
            self._render_featured_banner(self._featured_movie)
            self._schedule_carousel()

        self._grid_header.set_chip(f"{len(movies)} movies")
        self._render_poster_grid(self._grid_box, movies)

    def _render_featured_banner(self, matched: MatchedMovie) -> None:
        if not hasattr(self, "_banner_frame") or not self._banner_frame.winfo_exists():
            self._build_banner_ui()
        self._update_banner_slide(matched)

    def _build_banner_ui(self) -> None:
        self._clear(self._banner_box)
        self._banner_frame = ctk.CTkFrame(
            self._banner_box, fg_color=Colors.CARD, corner_radius=Sizes.CARD_RADIUS,
            border_width=1, border_color=Colors.BORDER, height=Sizes.BANNER_HEIGHT,
        )
        self._banner_frame.pack(fill="x")
        self._banner_frame.pack_propagate(False)
        self._banner_frame.bind("<Enter>", lambda _e: self._cancel_carousel(), add="+")
        self._banner_frame.bind("<Leave>", lambda _e: self._schedule_carousel(), add="+")

        viewport = ctk.CTkFrame(self._banner_frame, fg_color="transparent", corner_radius=0)
        viewport.pack(fill="both", expand=True, padx=1, pady=1)

        backdrop_w = round(Sizes.BANNER_HEIGHT * 16 / 9)
        self._banner_slide = ctk.CTkFrame(viewport, fg_color="transparent")
        self._banner_slide.pack(fill="both", expand=True)

        self._banner_backdrop = ImageView(
            self._banner_slide, (backdrop_w, Sizes.BANNER_HEIGHT - 2),
            placeholder="movie", radius=Sizes.CARD_RADIUS,
        )
        self._banner_backdrop.pack(side="left", padx=(0, Spacing.XL), pady=0)

        info = ctk.CTkFrame(self._banner_slide, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(0, Spacing.XL), pady=Spacing.LG)

        top_tags = ctk.CTkFrame(info, fg_color="transparent")
        top_tags.pack(fill="x", pady=(0, Spacing.XS))
        self._banner_badge = Chip(top_tags, "Featured Free Movie", accent=True)
        self._banner_badge.pack(side="left", padx=(0, Spacing.SM))
        self._banner_channel = Chip(top_tags, "")
        self._banner_channel.pack(side="left")

        self._banner_title = ctk.CTkLabel(
            info, text="", font=typography.title(),
            text_color=Colors.TEXT, anchor="w",
        )
        self._banner_title.pack(fill="x")

        self._banner_meta = ctk.CTkFrame(info, fg_color="transparent")
        self._banner_meta.pack(fill="x", pady=(Spacing.XS, Spacing.SM))

        self._banner_overview = ctk.CTkLabel(
            info, text="", font=typography.body(), text_color=Colors.TEXT_SECONDARY,
            anchor="w", justify="left", wraplength=520,
        )
        self._banner_overview.pack(fill="x", pady=(0, Spacing.MD))

        btns = ctk.CTkFrame(info, fg_color="transparent")
        btns.pack(side="bottom", fill="x")
        self._banner_play_btn = PrimaryButton(
            btns, " Play Now", command=self._play_current_banner,
            image=icons.icon("play", Colors.ON_ACCENT, 14), compound="left", width=130,
        )
        self._banner_play_btn.pack(side="left", padx=(0, Spacing.SM))
        self._banner_details_btn = SecondaryButton(
            btns, "Details", command=self._open_current_banner, width=100,
        )
        self._banner_details_btn.pack(side="left", padx=(0, Spacing.SM))

        self._banner_fav_btn = SecondaryButton(
            btns, " Favorite",
            command=self._toggle_current_banner_favorite,
            image=icons.icon("heart", Colors.TEXT, 14),
            compound="left", width=120,
        )
        self._banner_fav_btn.pack(side="left")

        self._banner_nav = ctk.CTkFrame(btns, fg_color="transparent")
        self._banner_nav.pack(side="right")

    def _update_banner_slide(self, matched: MatchedMovie) -> None:
        movie = matched.movie
        total = max(1, len(self._carousel_items))
        self._banner_badge.configure(text=" Featured Free Movie ")

        ch_name = matched.video.channel_name if matched.video else ""
        if ch_name:
            self._banner_channel.configure(text=f" {ch_name} ")
            self._banner_channel.pack(side="left")
        else:
            self._banner_channel.pack_forget()

        self._banner_backdrop.load(movie.backdrop_url or movie.poster_url)
        self._banner_title.configure(text=movie.title)

        self._clear(self._banner_meta)
        meta_parts = [p for p in (
            str(movie.release_year) if movie.release_year else "",
            movie.genres,
            f"{movie.runtime} min" if movie.runtime else "",
        ) if p]
        if meta_parts:
            ctk.CTkLabel(
                self._banner_meta, text="  •  ".join(meta_parts), font=typography.small(),
                text_color=Colors.TEXT_SECONDARY,
            ).pack(side="left", padx=(0, Spacing.MD))
        if movie.rating > 0:
            ctk.CTkLabel(self._banner_meta, text="", image=icons.icon("star", Colors.WARNING, 12)).pack(side="left")
            ctk.CTkLabel(
                self._banner_meta, text=f" {movie.rating:.1f}", font=typography.small(),
                text_color=Colors.TEXT,
            ).pack(side="left")

        overview = (movie.overview or "").strip()
        if len(overview) > 190:
            overview = overview[:187].rstrip() + "..."
        self._banner_overview.configure(text=overview)

        is_fav = matched.external_key in self._favorite_ids
        self._banner_fav_btn.configure(
            text=" Favorited" if is_fav else " Favorite",
            image=icons.icon("heart_filled" if is_fav else "heart",
                             Colors.ACCENT if is_fav else Colors.TEXT, 14),
        )

        self._clear(self._banner_nav)
        if total > 1:
            for idx in range(total):
                is_cur = idx == self._carousel_index
                ctk.CTkButton(
                    self._banner_nav, text="", width=18 if is_cur else 6, height=6, corner_radius=3,
                    fg_color=Colors.ACCENT if is_cur else Colors.BORDER,
                    hover_color=Colors.ACCENT_HOVER,
                    command=lambda i=idx: self._jump_carousel(i),
                ).pack(side="left", padx=2)
            # Preload next slide's backdrop so transitions are instant
            nxt = self._carousel_items[(self._carousel_index + 1) % total].movie
            next_url = nxt.backdrop_url or nxt.poster_url
            if image_cache.is_valid_url(next_url):
                image_cache.request_image(next_url)

    def _play_current_banner(self) -> None:
        if self._featured_movie is not None:
            self._open_details(self._featured_movie, autoplay=True)

    def _open_current_banner(self) -> None:
        if self._featured_movie is not None:
            self._open_details(self._featured_movie, autoplay=False)

    def _toggle_current_banner_favorite(self) -> None:
        if self._featured_movie is not None:
            self._toggle_banner_favorite(self._featured_movie)

    def _schedule_carousel(self) -> None:
        self._cancel_carousel()
        if len(self._carousel_items) <= 1 or not self._alive() or self._details_view is not None:
            return
        try:
            self._carousel_job = self.after(_CAROUSEL_INTERVAL_MS, self._advance_carousel)
        except Exception:  # noqa: BLE001
            self._carousel_job = None

    def _cancel_carousel(self) -> None:
        if self._carousel_job is not None:
            try:
                self.after_cancel(self._carousel_job)
            except Exception:  # noqa: BLE001
                pass
            self._carousel_job = None
        if self._slide_anim_job is not None:
            try:
                self.after_cancel(self._slide_anim_job)
            except Exception:  # noqa: BLE001
                pass
            self._slide_anim_job = None

    def _animate_banner_slide(self, step: int = 0) -> None:
        # Transitions are instant and tear-free; avoid place_configure loops inside CTkScrollableFrame.
        return

    def _advance_carousel(self) -> None:
        self._carousel_job = None
        if not self._alive() or self._details_view is not None or len(self._carousel_items) <= 1:
            return
        self._carousel_index = (self._carousel_index + 1) % len(self._carousel_items)
        self._featured_movie = self._carousel_items[self._carousel_index]
        self._render_featured_banner(self._featured_movie)
        self._animate_banner_slide()
        self._schedule_carousel()

    def _jump_carousel(self, index: int) -> None:
        if not (0 <= index < len(self._carousel_items)) or index == self._carousel_index:
            return
        self._carousel_index = index
        self._featured_movie = self._carousel_items[index]
        self._render_featured_banner(self._featured_movie)
        self._animate_banner_slide()
        self._schedule_carousel()

    def _toggle_banner_favorite(self, matched: MatchedMovie) -> None:
        state = self._toggle_favorite(matched)
        if state is None:
            return
        self._banner_fav_btn.configure(
            text=" Favorited" if state else " Favorite",
            image=icons.icon("heart_filled" if state else "heart",
                             Colors.ACCENT if state else Colors.TEXT, 14),
        )

    def _render_poster_grid(self, container: ctk.CTkFrame, movies: List[MatchedMovie]) -> None:
        for col in range(_GRID_COLUMNS):
            container.grid_columnconfigure(col, weight=1, uniform="movies_grid")

        for idx, matched in enumerate(movies):
            movie = matched.movie
            item = matched.to_media_item()
            card = MediaCard(
                container,
                item,
                image_size=Sizes.CARD_IMAGE_DEFAULT,
                aspect_ratio=Sizes.POSTER_ASPECT,
                rating=movie.rating if movie.rating > 0 else None,
                favorite=matched.external_key in self._favorite_ids,
                show_play=matched.is_playable,
                on_open=lambda _i, m=matched: self._open_details(m, autoplay=False),
                on_play=lambda _i, m=matched: self._open_details(m, autoplay=True),
                on_favorite=lambda _i, m=matched: self._toggle_favorite(m),
            )
            row, col = divmod(idx, _GRID_COLUMNS)
            card.grid(
                row=row, column=col, sticky="nsew",
                padx=(0, Spacing.MD if col < _GRID_COLUMNS - 1 else 0),
                pady=(0, Spacing.MD),
            )
            self._hearts.track(card)

    # ------------------------------------------------------------------
    # Details Navigation
    # ------------------------------------------------------------------

    def _open_details(self, matched: MatchedMovie, autoplay: bool = False) -> None:
        self._cancel_carousel()
        self._close_details()
        self._browse_scroll.pack_forget()
        self._route_loader.pack_forget()

        self._details_view = MovieDetailsView(
            self,
            self.ctx,
            matched,
            is_favorite=matched.external_key in self._favorite_ids,
            autoplay=autoplay,
            on_back=self._close_details,
            on_favorite_changed=self._on_details_favorite_changed,
        )
        self._details_view.pack(fill="both", expand=True)

    def _close_details(self) -> None:
        if self._details_view is not None:
            self._details_view.destroy()
            self._details_view = None
        if not self._browse_scroll.winfo_ismapped():
            self._browse_scroll.pack(fill="both", expand=True)
        self._schedule_carousel()

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------

    def _toggle_favorite(self, matched: MatchedMovie) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            return None
        try:
            state = self._library.toggle_favorite(user.id, matched.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._on_details_favorite_changed(matched.external_key, state)
        return state

    def _on_details_favorite_changed(self, ext_id: str, state: bool) -> None:
        if state:
            self._favorite_ids.add(ext_id)
        else:
            self._favorite_ids.discard(ext_id)
        self._hearts.update(MEDIA_MOVIE, ext_id, state)
        if self._featured_movie and self._featured_movie.external_key == ext_id and hasattr(self, "_banner_fav_btn"):
            try:
                if self._banner_fav_btn.winfo_exists():
                    self._banner_fav_btn.configure(
                        text=" Favorited" if state else " Favorite",
                        image=icons.icon("heart_filled" if state else "heart",
                                         Colors.ACCENT if state else Colors.TEXT, 14),
                    )
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Cleanup & Helpers
    # ------------------------------------------------------------------

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
        self._cancel_carousel()
        self._route_token += 1
        self._catalog_token += 1
        self._search_token += 1
        if self._details_view is not None:
            self._details_view.release()
        super().destroy()
