"""Featured Tracks row: a few MediaCards for the default iTunes query."""
from typing import Callable, Dict, List, Optional, Set

import customtkinter as ctk

from models.music import Track
from presentation.components.cards import FavoriteTracker, MediaCard, SectionHeader
from presentation.components.loaders import StateMessage
from presentation.styles.colors import Spacing

FEATURED_VISIBLE = 4

PlayAction = Callable[[Track, List[Track]], None]
FavoriteAction = Callable[[Track], Optional[bool]]


class FeaturedTracksSection(ctk.CTkFrame):
    """FeaturedTracksSection(parent, tracker, on_play(track, queue), on_favorite(track) -> bool)"""

    def __init__(self, parent, tracker: FavoriteTracker, on_play: PlayAction, on_favorite: FavoriteAction) -> None:
        super().__init__(parent, fg_color="transparent")
        self._tracker, self._on_play, self._on_favorite = tracker, on_play, on_favorite
        self._cards: Dict[str, MediaCard] = {}
        SectionHeader(self, "Featured Tracks").pack(fill="x", pady=(0, Spacing.MD))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="x")

    def _clear(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._cards.clear()

    def show_loading(self) -> None:
        self._clear()
        StateMessage(self._body, "loading", "Loading featured tracks...").pack(fill="x")

    def show_error(self, message: str, on_retry: Callable[[], None]) -> None:
        self._clear()
        StateMessage(self._body, "error", message, on_retry).pack(fill="x")

    def show_tracks(self, tracks: List[Track], favorite_ids: Set[str]) -> None:
        self._clear()
        if not tracks:
            StateMessage(self._body, "empty", "No featured tracks right now.").pack(fill="x")
            return
        visible = tracks[:FEATURED_VISIBLE]
        for column in range(FEATURED_VISIBLE):
            self._body.grid_columnconfigure(column, weight=1, uniform="featured_tracks")
        for column, track in enumerate(visible):
            play = lambda _item, t=track: self._on_play(t, tracks)  # noqa: E731 - small callback
            card = MediaCard(self._body, track.to_media_item(), favorite=track.track_id in favorite_ids,
                             show_play=True, on_open=play, on_play=play,
                             on_favorite=lambda _item, t=track: self._on_favorite(t))
            card.grid(row=0, column=column, sticky="nsew",
                      padx=(0, 0 if column == FEATURED_VISIBLE - 1 else Spacing.MD))
            self._cards[track.track_id] = card
            self._tracker.track(card)

    def set_current(self, track_id: Optional[str]) -> None:
        for key, card in self._cards.items():
            card.set_highlighted(key == track_id)
