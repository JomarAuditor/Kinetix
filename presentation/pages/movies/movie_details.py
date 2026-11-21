"""Movie Details view: poster, metadata, genres, Favorite/Play, and embedded VideoPlayer."""
from typing import Callable, Optional

import customtkinter as ctk

from config.constants import MEDIA_MOVIE
from core.exceptions import KinetixError
from models.movie import MatchedMovie
from presentation.components.buttons import GhostButton, PrimaryButton, SecondaryButton
from presentation.components.cards import Chip, HeartButton, SectionHeader
from presentation.components.dialogs import show_toast
from presentation.components.images import ImageView
from presentation.pages.movies.video_player import VideoPlayer
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing
from utils.logger import get_logger

logger = get_logger("movie_details")


class MovieDetailsView(ctk.CTkFrame):
    """Details and embedded playback view for a single movie."""

    def __init__(
        self,
        parent,
        ctx,
        matched: MatchedMovie,
        *,
        is_favorite: bool = False,
        autoplay: bool = False,
        on_back: Callable[[], None],
        on_favorite_changed: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.ctx = ctx
        self._matched = matched
        self._is_favorite = is_favorite
        self._on_back = on_back
        self._on_favorite_changed = on_favorite_changed

        self._build_top_bar()
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._scroll.pack(fill="both", expand=True)

        self._content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._content.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.XL))

        self._build_hero_card(self._content)
        self._build_player_section(self._content)

        self._player.set_movie(matched, autoplay=autoplay)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> None:
        self._nav_bar = ctk.CTkFrame(self, fg_color="transparent")
        self._nav_bar.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.MD))

        GhostButton(
            self._nav_bar, " Back to Movies", command=self._handle_back,
            image=icons.icon("arrow_left", Colors.TEXT_SECONDARY, 16), compound="left", width=150,
        ).pack(side="left")

        self._header_heart = HeartButton(
            self._nav_bar, favorite=self._is_favorite, command=self._toggle_favorite, circle=True,
        )
        self._header_heart.pack(side="right")

    def _build_hero_card(self, parent) -> None:
        movie = self._matched.movie
        self._hero_card = ctk.CTkFrame(
            parent, fg_color=Colors.CARD, corner_radius=Sizes.CARD_RADIUS,
            border_width=1, border_color=Colors.BORDER,
        )
        self._hero_card.pack(fill="x", pady=(0, Spacing.XL))

        row = ctk.CTkFrame(self._hero_card, fg_color="transparent")
        row.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        poster = ImageView(
            row, (Sizes.DETAILS_POSTER_WIDTH, Sizes.DETAILS_POSTER_HEIGHT),
            placeholder="movie", radius=Sizes.IMAGE_RADIUS,
        )
        poster.pack(side="left", anchor="n")
        poster.load(movie.poster_url)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(Spacing.XL, 0))

        ctk.CTkLabel(
            info, text=movie.title, font=typography.title(),
            text_color=Colors.TEXT, anchor="w", wraplength=640, justify="left",
        ).pack(fill="x")

        # Metadata row: year, runtime, rating, rights chip
        meta = ctk.CTkFrame(info, fg_color="transparent")
        meta.pack(fill="x", pady=(Spacing.SM, Spacing.MD))

        parts = []
        if movie.release_year:
            parts.append(str(movie.release_year))
        if movie.runtime:
            parts.append(f"{movie.runtime} min")
        elif self._matched.duration_minutes:
            parts.append(f"{self._matched.duration_minutes} min")
        if parts:
            ctk.CTkLabel(
                meta, text="  •  ".join(parts), font=typography.body(),
                text_color=Colors.TEXT_SECONDARY,
            ).pack(side="left", padx=(0, Spacing.MD))

        if movie.rating > 0:
            ctk.CTkLabel(meta, text="", image=icons.icon("star", Colors.WARNING, 14)).pack(side="left")
            ctk.CTkLabel(
                meta, text=f" {movie.rating:.1f}", font=typography.body_bold(),
                text_color=Colors.TEXT,
            ).pack(side="left", padx=(0, Spacing.MD))

        status_text = "Verified Free Source" if self._matched.is_playable else "Metadata Only"
        Chip(meta, status_text, accent=self._matched.is_playable).pack(side="left")

        if self._matched.video and self._matched.video.channel_name:
            ctk.CTkLabel(
                meta, text=f"Source: {self._matched.video.channel_name}",
                font=typography.small(), text_color=Colors.TEXT_MUTED,
            ).pack(side="left", padx=(Spacing.MD, 0))

        # Genre chips
        genres = [g.strip() for g in movie.genres.split(",") if g.strip()]
        if genres:
            chips_row = ctk.CTkFrame(info, fg_color="transparent")
            chips_row.pack(fill="x", pady=(0, Spacing.MD))
            for genre in genres[:6]:
                Chip(chips_row, genre).pack(side="left", padx=(0, Spacing.SM))

        # Overview
        overview = movie.overview.strip() or "No description available for this movie."
        ctk.CTkLabel(
            info, text=overview, font=typography.body(), text_color=Colors.TEXT_SECONDARY,
            anchor="w", justify="left", wraplength=660,
        ).pack(fill="x", pady=(0, Spacing.LG))

        # Buttons
        actions = ctk.CTkFrame(info, fg_color="transparent")
        actions.pack(fill="x")

        play_label = " Play Movie" if self._matched.is_playable else " Source Unavailable"
        play_btn = PrimaryButton(
            actions, play_label, command=self._play_movie,
            image=icons.icon("play", Colors.ON_ACCENT, 15), compound="left", width=160,
        )
        play_btn.pack(side="left", padx=(0, Spacing.MD))
        if not self._matched.is_playable:
            play_btn.configure(state="disabled")

        self._fav_btn = SecondaryButton(
            actions, self._fav_label(), command=self._on_fav_button_click,
            image=icons.icon("heart_filled" if self._is_favorite else "heart",
                             Colors.ACCENT if self._is_favorite else Colors.TEXT, 15),
            compound="left", width=160,
        )
        self._fav_btn.pack(side="left")

    def _build_player_section(self, parent) -> None:
        self._player_header = SectionHeader(parent, "Watch Inside Kinetix")
        self._player_header.pack(fill="x", pady=(0, Spacing.MD))

        self._player_holder = ctk.CTkFrame(parent, fg_color="transparent")
        self._player_holder.pack(fill="x", pady=(0, Spacing.MD))

        self._player = VideoPlayer(
            self,
            self.ctx,
            on_play_started=self._record_history,
            on_fullscreen_change=self._on_fullscreen_change,
        )
        self._player.pack(in_=self._player_holder, fill="x")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _play_movie(self) -> None:
        self._player.play_movie()

    def _on_fav_button_click(self) -> None:
        state = self._toggle_favorite()
        if state is not None:
            self._header_heart.set_favorite(state)

    def _toggle_favorite(self) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return None
        try:
            state = self.ctx.library.toggle_favorite(user.id, self._matched.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._is_favorite = state
        self._refresh_fav_button()
        if self._on_favorite_changed is not None:
            self._on_favorite_changed(self._matched.external_key, state)
        return state

    def _fav_label(self) -> str:
        return " Favorited" if self._is_favorite else " Add to Favorites"

    def _refresh_fav_button(self) -> None:
        self._fav_btn.configure(
            text=self._fav_label(),
            image=icons.icon("heart_filled" if self._is_favorite else "heart",
                             Colors.ACCENT if self._is_favorite else Colors.TEXT, 15),
        )

    def _record_history(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        try:
            self.ctx.library.record_play(user.id, self._matched.to_media_item())
        except KinetixError as exc:
            logger.debug("Could not log movie history: %s", exc)

    def _on_fullscreen_change(self, enabled: bool) -> None:
        if enabled:
            self._nav_bar.pack_forget()
            self._scroll.pack_forget()
            self._player.pack_forget()
            self._player.pack(fill="both", expand=True)
            self._player.tkraise()
        else:
            self._player.pack_forget()
            self._nav_bar.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.MD))
            self._scroll.pack(fill="both", expand=True)
            self._player.pack(in_=self._player_holder, fill="x")

    def _handle_back(self) -> None:
        self.release()
        self._on_back()

    def release(self) -> None:
        self._player.stop_and_release()

    def destroy(self) -> None:
        self.release()
        super().destroy()
