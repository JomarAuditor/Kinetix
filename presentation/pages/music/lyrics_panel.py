"""Lyrics panel (340px, right side of the Music page).

Loads lyrics in the background, shows them line by line and, when the song has
timestamps, highlights the current line in teal and scrolls to it.
"""
from typing import Callable, List, Optional

import customtkinter as ctk

from models.music import Lyrics, Track
from presentation.components.buttons import IconButton
from presentation.components.cards import FitLabel
from presentation.components.images import ImageView
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from utils.helpers import run_in_background

NOT_AVAILABLE_TEXT = "Lyrics not available for this song."
_LINE_WRAP = Sizes.LYRICS_PANEL_WIDTH - 2 * Spacing.LG - 28


class LyricsPanel(ctk.CTkFrame):
    """LyricsPanel(parent, ctx, on_close). Methods: show_track(track|None), refresh(position_ms)."""

    def __init__(self, parent, ctx, on_close: Callable[[], None]) -> None:
        super().__init__(parent, width=Sizes.LYRICS_PANEL_WIDTH, fg_color=Colors.CARD, border_width=1,
                         border_color=Colors.BORDER, corner_radius=Sizes.CARD_RADIUS)
        self.pack_propagate(False)
        self.ctx = ctx
        self._token = 0
        self._lyrics: Optional[Lyrics] = None
        self._labels: List[ctk.CTkLabel] = []
        self._active = -1

        self._build_header(on_close)
        self._build_track_block()
        ctk.CTkFrame(self, height=1, fg_color=Colors.BORDER).pack(fill="x", padx=Spacing.LG)
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=Colors.BORDER,
                                              scrollbar_button_hover_color=Colors.HOVER)
        self._scroll.pack(fill="both", expand=True, padx=(Spacing.SM, Spacing.XS), pady=Spacing.SM)
        self._build_footer()
        self._show_message("Play a song to see its lyrics.")

    # ---------------------------------------------------------------- layout
    def _build_header(self, on_close: Callable[[], None]) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        ctk.CTkLabel(header, text="Lyrics", font=typography.section(), text_color=Colors.TEXT).pack(side="left")
        IconButton(header, "close", on_close, style="ghost", size=32).pack(side="right")

    def _build_track_block(self) -> None:
        block = ctk.CTkFrame(self, fg_color="transparent")
        block.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        self.art = ImageView(block, (Sizes.LYRICS_ART_SIZE, Sizes.LYRICS_ART_SIZE), placeholder="music")
        self.art.pack(side="left")
        text = ctk.CTkFrame(block, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(Spacing.MD, 0))
        self.title_label = FitLabel(text, "", typography.card(), Colors.TEXT)
        self.title_label.pack(fill="x")
        self.artist_label = FitLabel(text, "", typography.body(), Colors.TEXT_SECONDARY)
        self.artist_label.pack(fill="x")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        self._scroll_label = ctk.CTkLabel(footer, text="", font=typography.tiny(), text_color=Colors.TEXT_MUTED)
        self._scroll_label.pack(side="left")
        self._live_label = ctk.CTkLabel(footer, text="", font=typography.tiny(), text_color=Colors.ACCENT)
        self._live_label.pack(side="right")

    # ---------------------------------------------------------------- public
    def show_track(self, track: Optional[Track]) -> None:
        self._token += 1
        if track is None:
            self.art.show_placeholder()
            self.title_label.set_text("")
            self.artist_label.set_text("")
            self._show_message("Play a song to see its lyrics.")
            return
        self.art.load(track.artwork_url)
        self.title_label.set_text(track.title)
        self.artist_label.set_text(track.artist)
        self._show_message("Loading lyrics...")
        token, service = self._token, self.ctx.music_service
        run_in_background(self, lambda: service.lyrics(track), lambda r, e: self._on_loaded(token, r, e))

    def refresh(self, position_ms: int) -> None:
        """Move the teal highlight to the line at position_ms (only for synced lyrics)."""
        if self._lyrics is None or not self._lyrics.has_synced:
            return
        index = self._lyrics.line_index_at(position_ms)
        if index != self._active:
            self._set_active(index)

    # ---------------------------------------------------------------- loading result
    def _on_loaded(self, token: int, lyrics: Optional[Lyrics], error: Optional[Exception]) -> None:
        if token != self._token:
            return  # another song was chosen meanwhile
        if error is not None:
            self._show_message("Could not load lyrics. Check your connection.")
        elif lyrics is None or not lyrics.has_text:
            self._show_message(NOT_AVAILABLE_TEXT)
        else:
            self._show_lines(lyrics)

    def _clear(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        self._labels, self._lyrics, self._active = [], None, -1
        self._scroll_label.configure(text="")
        self._live_label.configure(text="")

    def _show_message(self, text: str) -> None:
        self._clear()
        ctk.CTkLabel(self._scroll, text=text, font=typography.body(), text_color=Colors.TEXT_MUTED,
                     anchor="w", justify="left", wraplength=_LINE_WRAP).pack(fill="x", padx=Spacing.SM,
                                                                              pady=Spacing.SM)

    def _show_lines(self, lyrics: Lyrics) -> None:
        self._clear()
        self._lyrics = lyrics
        for line in lyrics.plain_lines():
            label = ctk.CTkLabel(self._scroll, text=line, font=typography.card(), text_color=Colors.TEXT_SECONDARY,
                                 anchor="w", justify="left", wraplength=_LINE_WRAP, corner_radius=6)
            label.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)
            self._labels.append(label)
        self._scroll_label.configure(text="Auto-scroll: Enabled" if lyrics.has_synced else "Plain lyrics (not synced)")
        self._live_label.configure(text="Live" if lyrics.has_synced else "")

    # ---------------------------------------------------------------- highlight and scroll
    def _set_active(self, index: int) -> None:
        if 0 <= self._active < len(self._labels):
            self._labels[self._active].configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)
        self._active = index
        if 0 <= index < len(self._labels):
            label = self._labels[index]
            label.configure(fg_color=Colors.ACCENT_TINT_CARD, text_color=Colors.ACCENT)
            self.after(30, lambda: self._scroll_to(label))

    def _scroll_to(self, label: ctk.CTkLabel) -> None:
        try:
            if not label.winfo_exists():
                return
            canvas = self._scroll._parent_canvas  # CustomTkinter keeps its canvas here
            total = max(1, self._scroll.winfo_height())
            target = label.winfo_y() + label.winfo_height() / 2 - canvas.winfo_height() / 2
            canvas.yview_moveto(max(0.0, min(1.0, target / total)))
        except Exception:  # noqa: BLE001 - scrolling is a nicety, never a crash
            pass
