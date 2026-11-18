"""Search Results: MediaRows with art, title, artist, album, duration, heart and a Play button."""
from typing import Callable, Dict, List, Optional, Set

import customtkinter as ctk

from models.music import Track
from presentation.components.cards import FavoriteTracker, MediaRow, SectionHeader
from presentation.components.loaders import StateMessage
from presentation.styles.colors import Spacing

PlayAction = Callable[[Track, List[Track]], None]
FavoriteAction = Callable[[Track], Optional[bool]]


class SearchResultsSection(ctk.CTkFrame):
    """SearchResultsSection(parent, tracker, on_play(track, queue), on_favorite(track) -> bool)

    States: show_idle(), show_loading(query), show_error(message, on_retry), show_results(tracks, favorite_ids, query).
    """

    def __init__(self, parent, tracker: FavoriteTracker, on_play: PlayAction, on_favorite: FavoriteAction) -> None:
        super().__init__(parent, fg_color="transparent")
        self._tracker, self._on_play, self._on_favorite = tracker, on_play, on_favorite
        self._rows: Dict[str, MediaRow] = {}
        self._header = SectionHeader(self, "Search Results")
        self._header.pack(fill="x", pady=(0, Spacing.MD))
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="x")
        self.show_idle()

    def _reset(self, chip: str = "") -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._rows.clear()
        self._header.set_chip(chip)

    def show_idle(self) -> None:
        self._reset()
        StateMessage(self._body, "empty", "Search for a song, artist or album to see results.").pack(fill="x")

    def show_loading(self, query: str) -> None:
        self._reset()
        StateMessage(self._body, "loading", f"Searching for \"{query}\"...").pack(fill="x")

    def show_error(self, message: str, on_retry: Callable[[], None]) -> None:
        self._reset()
        StateMessage(self._body, "error", message, on_retry).pack(fill="x")

    def show_results(self, tracks: List[Track], favorite_ids: Set[str], query: str) -> None:
        if not tracks:
            self._reset()
            StateMessage(self._body, "empty", f"No results found for \"{query}\". Try a different search.").pack(fill="x")
            return
        self._reset(f"{len(tracks)} tracks found")
        for track in tracks:
            play = lambda _item, t=track: self._on_play(t, tracks)  # noqa: E731 - small callback
            row = MediaRow(self._body, track.to_media_item(), detail=track.album, time_text=track.duration_text,
                           favorite=track.track_id in favorite_ids,
                           on_favorite=lambda _item, t=track: self._on_favorite(t),
                           action_icon="play", action_style="accent", on_action=play, on_open=play)
            row.pack(fill="x", pady=(0, Spacing.SM))
            self._rows[track.track_id] = row
            self._tracker.track(row)

    def set_current(self, track_id: Optional[str], playing: bool) -> None:
        """Teal highlight on the current song; its button shows pause while it plays."""
        for key, row in self._rows.items():
            row.clear_playing()
            if key == track_id:
                if playing:
                    row.set_playing(True)
                else:
                    row.set_highlighted(True)
