"""Games Search Results section: displays playable API games in a 4-column MediaCard grid."""
from typing import Callable, List, Optional, Set

import customtkinter as ctk

from models.game import GameItem
from presentation.components.cards import FavoriteTracker, MediaCard, SectionHeader
from presentation.components.loaders import StateMessage
from presentation.styles.colors import Sizes, Spacing

PlayGameAction = Callable[[GameItem], None]
FavoriteGameAction = Callable[[GameItem], Optional[bool]]

_COLUMNS = 4


class GameSearchSection(ctk.CTkFrame):
    """Search results section for playable in-app games."""

    def __init__(
        self,
        parent,
        tracker: FavoriteTracker,
        on_play: PlayGameAction,
        on_favorite: FavoriteGameAction,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._tracker = tracker
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
        StateMessage(self._body, "loading", f'Searching games for "{query}"...').pack(fill="x")

    def show_error(self, message: str, on_retry: Optional[Callable[[], None]] = None) -> None:
        self._reset()
        StateMessage(self._body, "error", message, on_retry).pack(fill="x")

    def show_results(self, games: List[GameItem], favorite_ids: Set[str], query: str) -> None:
        if not games:
            self._reset()
            StateMessage(self._body, "empty", f'No games found for "{query}". Try "trivia", "cards", or "word".').pack(fill="x")
            return

        self._reset(f"{len(games)} found")
        for col in range(_COLUMNS):
            self._body.grid_columnconfigure(col, weight=1, uniform="game_search")

        for idx, game in enumerate(games):
            item = game.to_media_item()
            card = MediaCard(
                self._body,
                item,
                image_size=Sizes.CARD_IMAGE_DEFAULT,
                aspect_ratio=Sizes.GAME_CARD_ASPECT,
                tag=game.category if game.playable else "Info Only",
                rating=game.rating if game.rating > 0 else None,
                favorite=game.game_id in favorite_ids,
                show_play=game.playable,
                on_open=lambda _i, g=game: self._on_play(g),
                on_play=lambda _i, g=game: self._on_play(g),
                on_favorite=lambda _i, g=game: self._on_favorite(g),
            )
            row, col = divmod(idx, _COLUMNS)
            card.grid(
                row=row, column=col, sticky="nsew",
                padx=(0, Spacing.MD if col < _COLUMNS - 1 else 0),
                pady=(0, Spacing.MD),
            )
            self._tracker.track(card)
