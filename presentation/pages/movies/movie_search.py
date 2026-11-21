"""Movies Search Results section: displays matched movies in a 2:3 poster grid."""
from typing import Callable, List, Optional, Set

import customtkinter as ctk

from models.movie import MatchedMovie
from presentation.components.cards import FavoriteTracker, MediaCard, SectionHeader
from presentation.components.loaders import StateMessage
from presentation.styles.colors import Sizes, Spacing

OpenMovieAction = Callable[[MatchedMovie], None]
PlayMovieAction = Callable[[MatchedMovie], None]
FavoriteMovieAction = Callable[[MatchedMovie], Optional[bool]]


class MovieSearchSection(ctk.CTkFrame):
    """Search results section for MoviesPage."""

    def __init__(
        self,
        parent,
        tracker: FavoriteTracker,
        on_open: OpenMovieAction,
        on_play: PlayMovieAction,
        on_favorite: FavoriteMovieAction,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._tracker = tracker
        self._on_open = on_open
        self._on_play = on_play
        self._on_favorite = on_favorite

        self._header = SectionHeader(self, "Search Results")
        self._header.pack(fill="x", pady=(0, Spacing.MD))

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="x")

    def _reset(self, chip: str = "") -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._header.set_chip(chip)

    def show_loading(self, query: str) -> None:
        self._reset()
        StateMessage(self._body, "loading", f'Searching movies for "{query}"...').pack(fill="x")

    def show_error(self, message: str, on_retry: Optional[Callable[[], None]] = None) -> None:
        self._reset()
        StateMessage(self._body, "error", message, on_retry).pack(fill="x")

    def show_results(self, movies: List[MatchedMovie], favorite_ids: Set[str], query: str) -> None:
        if not movies:
            self._reset()
            StateMessage(
                self._body, "empty",
                f'No movies found for "{query}". Try another title or paste a direct link in any movie page.',
            ).pack(fill="x")
            return

        self._reset(f"{len(movies)} found")
        columns = 4
        for col in range(columns):
            self._body.grid_columnconfigure(col, weight=1, uniform="movie_search")

        for idx, matched in enumerate(movies):
            movie = matched.movie
            item = matched.to_media_item()
            tag = "Verified" if matched.is_playable else "Unverified"
            card = MediaCard(
                self._body,
                item,
                image_size=Sizes.CARD_IMAGE_DEFAULT,
                aspect_ratio=Sizes.POSTER_ASPECT,
                tag=tag,
                rating=movie.rating if movie.rating > 0 else None,
                favorite=matched.external_key in favorite_ids,
                show_play=matched.is_playable,
                on_open=lambda _i, m=matched: self._on_open(m),
                on_play=lambda _i, m=matched: self._on_play(m),
                on_favorite=lambda _i, m=matched: self._on_favorite(m),
            )
            row, col = divmod(idx, columns)
            card.grid(
                row=row, column=col, sticky="nsew",
                padx=(0, Spacing.MD if col < columns - 1 else 0),
                pady=(0, Spacing.MD),
            )
            self._tracker.track(card)
