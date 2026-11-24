"""Settings page – Appearance, Playback, and About Kinetix sections."""
from typing import Optional

import customtkinter as ctk

from config.constants import (
    APP_NAME, APP_VERSION,
    SETTING_AUTOPLAY, SETTING_MOVIE_VOLUME, SETTING_REMEMBER_POSITION,
    SETTING_SHOW_LYRICS, SETTING_VOLUME,
)
from presentation.components.buttons import PrimaryButton, SecondaryButton
from presentation.components.dialogs import show_toast
from presentation.pages.base_page import BasePage
from presentation.styles import typography, widgets
from presentation.styles.colors import Colors, Sizes, Spacing
from utils.logger import get_logger

logger = get_logger("settings_page")

_DEFAULT_VOLUME = 70
_DEFAULT_MOVIE_VOLUME = 70

_TECH_STACK = "Python 3.14 · CustomTkinter 6 · SQLite · Pillow · python-vlc · yt-dlp"
_DATA_SOURCES = "iTunes Search API · TMDB (movies) · Open Trivia DB · Deck of Cards API · Datamuse Word API"
_MEDIA_TOOLS = "VLC (embedded video) · yt-dlp (stream resolution)"
_GAMES_NOTE = (
    "Games run 100% inside Kinetix using free public REST APIs – no API keys and no browser "
    "redirects required."
)


class SettingsPage(BasePage):
    """Per-user settings: Appearance, Playback, and About Kinetix."""

    def __init__(self, parent, ctx, **_params) -> None:
        super().__init__(parent, ctx)
        self._library = ctx.library
        self._load_token = 0
        self._saved: dict = {}
        self._build_ui()
        self._load_settings()

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

        ctk.CTkLabel(
            content, text="Settings",
            font=typography.title(), text_color=Colors.TEXT, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.XL))

        self._appearance_section(content)
        self._playback_section(content)
        self._about_section(content)

        # Save / Reset buttons
        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x", pady=(Spacing.XL, 0))
        PrimaryButton(btn_row, "Save Settings", self._save_settings, width=160).pack(side="left")
        SecondaryButton(
            btn_row, "Reset to Default", self._reset_defaults, width=160,
        ).pack(side="left", padx=(Spacing.MD, 0))

    # ---------------------------------------------------------------- Appearance

    def _appearance_section(self, parent) -> None:
        frame = self._section_card(parent, "Appearance")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(0, Spacing.SM))
        ctk.CTkLabel(row, text="Theme", font=typography.body_bold(), text_color=Colors.TEXT,
                     anchor="w").pack(side="left")

        theme_row = ctk.CTkFrame(frame, fg_color="transparent")
        theme_row.pack(fill="x", pady=(0, Spacing.MD))

        # Dark (active)
        dark_frame = ctk.CTkFrame(
            theme_row, fg_color=Colors.ACCENT_TINT_CARD,
            border_width=2, border_color=Colors.ACCENT, corner_radius=Sizes.CARD_RADIUS,
        )
        dark_frame.pack(side="left", ipadx=Spacing.LG, ipady=Spacing.MD)
        ctk.CTkLabel(dark_frame, text="Dark", font=typography.body_bold(),
                     text_color=Colors.ACCENT).pack(padx=Spacing.LG)
        ctk.CTkLabel(dark_frame, text="Active", font=typography.small(),
                     text_color=Colors.ACCENT).pack()

        light_frame = ctk.CTkFrame(
            theme_row, fg_color=Colors.SURFACE,
            border_width=1, border_color=Colors.BORDER, corner_radius=Sizes.CARD_RADIUS,
        )
        light_frame.pack(side="left", padx=(Spacing.MD, 0), ipadx=Spacing.LG, ipady=Spacing.MD)
        ctk.CTkLabel(light_frame, text="Light", font=typography.body_bold(),
                     text_color=Colors.TEXT_MUTED).pack(padx=Spacing.LG)
        ctk.CTkLabel(light_frame, text="Coming soon", font=typography.small(),
                     text_color=Colors.TEXT_MUTED).pack()

    # ---------------------------------------------------------------- Playback

    def _playback_section(self, parent) -> None:
        frame = self._section_card(parent, "Playback")

        # Default volume
        self._vol_label = ctk.CTkLabel(
            frame, text=f"Default Volume: {_DEFAULT_VOLUME}%",
            font=typography.body(), text_color=Colors.TEXT, anchor="w",
        )
        self._vol_label.pack(fill="x", pady=(0, Spacing.SM))
        self._vol_slider = ctk.CTkSlider(
            frame, from_=0, to=100,
            command=self._on_volume_change,
            **widgets.slider(),
        )
        self._vol_slider.set(_DEFAULT_VOLUME)
        self._vol_slider.pack(fill="x", pady=(0, Spacing.LG))

        # Default movie volume
        self._mvol_label = ctk.CTkLabel(
            frame, text=f"Default Movie Volume: {_DEFAULT_MOVIE_VOLUME}%",
            font=typography.body(), text_color=Colors.TEXT, anchor="w",
        )
        self._mvol_label.pack(fill="x", pady=(0, Spacing.SM))
        self._mvol_slider = ctk.CTkSlider(
            frame, from_=0, to=100,
            command=self._on_movie_volume_change,
            **widgets.slider(),
        )
        self._mvol_slider.set(_DEFAULT_MOVIE_VOLUME)
        self._mvol_slider.pack(fill="x", pady=(0, Spacing.LG))

        # Autoplay next track
        self._autoplay_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Autoplay next track",
            variable=self._autoplay_var,
            **widgets.checkbox(),
        ).pack(anchor="w", pady=(0, Spacing.SM))

        # Show lyrics by default
        self._lyrics_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Show lyrics by default",
            variable=self._lyrics_var,
            **widgets.checkbox(),
        ).pack(anchor="w", pady=(0, Spacing.SM))

        # Remember movie playback position
        self._remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame, text="Remember movie playback position",
            variable=self._remember_var,
            **widgets.checkbox(),
        ).pack(anchor="w", pady=(0, Spacing.SM))

    # ---------------------------------------------------------------- About

    def _about_section(self, parent) -> None:
        frame = self._section_card(parent, "About Kinetix")
        rows = [
            ("Version", f"{APP_NAME} {APP_VERSION}"),
            ("Tech Stack", _TECH_STACK),
            ("Data Sources", _DATA_SOURCES),
            ("Media Tools", _MEDIA_TOOLS),
            ("Games & Sources", _GAMES_NOTE),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=(0, Spacing.MD))
            ctk.CTkLabel(row, text=label, font=typography.body_bold(),
                         text_color=Colors.TEXT_SECONDARY, anchor="w", width=130).pack(side="left")
            ctk.CTkLabel(row, text=value, font=typography.body(),
                         text_color=Colors.TEXT, anchor="w", justify="left",
                         wraplength=520).pack(side="left", fill="x", expand=True)

    # ---------------------------------------------------------------- helpers

    def _section_card(self, parent, title: str) -> ctk.CTkFrame:
        """Create a labeled card section and return the inner content frame."""
        card = ctk.CTkFrame(parent, fg_color=Colors.CARD,
                            border_width=1, border_color=Colors.BORDER,
                            corner_radius=Sizes.CARD_RADIUS)
        card.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(card, text=title, font=typography.section(),
                     text_color=Colors.TEXT, anchor="w").pack(
            fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.MD),
        )
        ctk.CTkFrame(card, height=1, fg_color=Colors.BORDER, corner_radius=0).pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
        return inner

    def _on_volume_change(self, value: float) -> None:
        vol = int(value)
        self._vol_label.configure(text=f"Default Volume: {vol}%")

    def _on_movie_volume_change(self, value: float) -> None:
        vol = int(value)
        self._mvol_label.configure(text=f"Default Movie Volume: {vol}%")

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    # ---------------------------------------------------------------- load/save

    def _load_settings(self) -> None:
        self._load_token += 1
        token = self._load_token
        user = self.ctx.session_service.current_user
        library = self._library

        def work() -> dict:
            if user is None or library is None:
                return {}
            return library._settings.get_all(user.id)

        def done(saved: dict, error) -> None:
            if token != self._load_token or not self._alive():
                return
            if error is not None:
                return
            saved = saved or {}
            # Volume
            try:
                vol = max(0, min(100, int(float(saved.get(SETTING_VOLUME, _DEFAULT_VOLUME)))))
            except (ValueError, TypeError):
                vol = _DEFAULT_VOLUME
            self._vol_slider.set(vol)
            self._vol_label.configure(text=f"Default Volume: {vol}%")
            # Movie volume
            try:
                mvol = max(0, min(100, int(float(saved.get(SETTING_MOVIE_VOLUME, _DEFAULT_MOVIE_VOLUME)))))
            except (ValueError, TypeError):
                mvol = _DEFAULT_MOVIE_VOLUME
            self._mvol_slider.set(mvol)
            self._mvol_label.configure(text=f"Default Movie Volume: {mvol}%")
            # Booleans
            self._autoplay_var.set(_as_bool(saved.get(SETTING_AUTOPLAY, "true"), True))
            self._lyrics_var.set(_as_bool(saved.get(SETTING_SHOW_LYRICS, "true"), True))
            self._remember_var.set(_as_bool(saved.get(SETTING_REMEMBER_POSITION, "false"), False))

        from utils.helpers import run_in_background
        run_in_background(self, work, done)

    def _save_settings(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None or self._library is None:
            show_toast(self, "Not signed in.", "error")
            return
        values = {
            SETTING_VOLUME: str(int(self._vol_slider.get())),
            SETTING_MOVIE_VOLUME: str(int(self._mvol_slider.get())),
            SETTING_AUTOPLAY: "true" if self._autoplay_var.get() else "false",
            SETTING_SHOW_LYRICS: "true" if self._lyrics_var.get() else "false",
            SETTING_REMEMBER_POSITION: "true" if self._remember_var.get() else "false",
        }
        self._load_token += 1
        token = self._load_token
        library = self._library

        def work() -> None:
            library._settings.set_many(user.id, values)

        def done(_result, error) -> None:
            if token != self._load_token or not self._alive():
                return
            if error is not None:
                logger.error("Failed to save settings: %s", error)
                show_toast(self, "Could not save settings.", "error")
                return
            # Apply to live music playback
            if self.ctx.music_playback is not None:
                vol = int(self._vol_slider.get())
                autoplay = self._autoplay_var.get()
                lyrics = self._lyrics_var.get()
                self.ctx.music_playback.configure(vol, autoplay, lyrics)
            show_toast(self, "Settings saved.", "success")

        from utils.helpers import run_in_background
        run_in_background(self, work, done)

    def _reset_defaults(self) -> None:
        self._vol_slider.set(_DEFAULT_VOLUME)
        self._vol_label.configure(text=f"Default Volume: {_DEFAULT_VOLUME}%")
        self._mvol_slider.set(_DEFAULT_MOVIE_VOLUME)
        self._mvol_label.configure(text=f"Default Movie Volume: {_DEFAULT_MOVIE_VOLUME}%")
        self._autoplay_var.set(True)
        self._lyrics_var.set(True)
        self._remember_var.set(False)

    def destroy(self) -> None:
        self._load_token += 1
        super().destroy()


def _as_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return default
