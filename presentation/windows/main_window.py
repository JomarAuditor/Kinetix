"""MainWindow (the CTk root) and AppShell (sidebar + top bar + content for signed-in pages)."""
import traceback
from typing import Optional

import customtkinter as ctk

from app.navigation import Route
from config.constants import APP_NAME
from config.theme import Colors, Sizes
from presentation.components.dialogs import apply_window_icon, show_toast
from presentation.components.sidebar import Sidebar
from presentation.components.topbar import TopBar
from presentation.styles.smooth_scroll import enable_smooth_scrolling
from utils.logger import get_logger

logger = get_logger("window")
_SEARCH_HINTS = {
    Route.HOME: "Search Kinetix...",
    Route.MUSIC: "Search music...",
    Route.MOVIES: "Search movies...",
    Route.GAMES: "Search games...",
    Route.FAVORITES: "Search favorites...",
    Route.RECENT: "Search history...",
}


class MainWindow(ctk.CTk):
    """The one application window. Shows either an auth page or the AppShell."""

    def __init__(self) -> None:
        super().__init__(fg_color=Colors.BACKGROUND)
        self.title(APP_NAME)
        self.minsize(Sizes.WINDOW_MIN_WIDTH, Sizes.WINDOW_MIN_HEIGHT)
        self._place_on_screen()
        apply_window_icon(self)
        enable_smooth_scrolling()
        self._content: Optional[ctk.CTkBaseClass] = None

    def _place_on_screen(self) -> None:
        try:
            scaling = self._get_window_scaling()  # CustomTkinter DPI factor (1.0 on normal screens)
        except Exception:  # noqa: BLE001
            scaling = 1.0
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        # Default 1440x900, but never bigger than the screen (and never below the minimum).
        width = max(Sizes.WINDOW_MIN_WIDTH, min(Sizes.WINDOW_WIDTH, int(screen_w / scaling) - 40))
        height = max(Sizes.WINDOW_MIN_HEIGHT, min(Sizes.WINDOW_HEIGHT, int(screen_h / scaling) - 90))
        x = max(0, int((screen_w - width * scaling) / 2))
        y = max(0, int((screen_h - height * scaling) / 2) - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def set_content(self, widget: ctk.CTkBaseClass) -> None:
        """Show `widget` (already created with this window as parent) and remove the old one."""
        widget.pack(fill="both", expand=True)
        old, self._content = self._content, widget
        if old is not None and old is not widget:
            old.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:
        """Log errors raised inside Tk callbacks and tell the user, instead of failing silently."""
        logger.error("Unhandled GUI error: %s", "".join(traceback.format_exception(exc, val, tb)))
        show_toast(self, "Something went wrong. Please try again.", "error")


class AppShell(ctk.CTkFrame):
    """Shared layout for every signed-in page. Only the content area changes."""

    def __init__(self, parent, ctx) -> None:
        super().__init__(parent, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.ctx = ctx
        self._page: Optional[ctk.CTkBaseClass] = None

        # Bottom slot for the persistent music player bar. It is packed first so it spans the
        # full window width, and it has no height until the bar appears (first song played).
        self.player_slot = ctk.CTkFrame(self, height=0, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.player_slot.pack(side="bottom", fill="x")

        self.sidebar = Sidebar(self, ctx.navigator.go, ctx.request_logout)
        self.sidebar.pack(side="left", fill="y")
        self._right = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._right.pack(side="left", fill="both", expand=True)
        self.topbar = TopBar(self._right, self._on_search, lambda: ctx.navigator.go(Route.ACCOUNT))
        self.topbar.pack(side="top", fill="x")
        self.content = ctk.CTkFrame(self._right, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.content.pack(side="top", fill="both", expand=True)
        self._fullscreen = False
        self.topbar.set_user(ctx.session_service.current_user)
        self.player_bar = None
        if ctx.music_playback is not None:
            from presentation.pages.music.music_player import PlayerBar  # imported here: it needs the shell first
            self.player_bar = PlayerBar(self.player_slot, ctx)

    def set_fullscreen_mode(self, enabled: bool) -> None:
        """Hide/restore shell chrome and toggle window fullscreen for embedded video."""
        if enabled == self._fullscreen:
            return
        self._fullscreen = enabled
        root = self.winfo_toplevel()
        if enabled:
            self.player_slot.pack_forget()
            self.sidebar.pack_forget()
            self.topbar.pack_forget()
            try:
                root.attributes("-fullscreen", True)
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                root.attributes("-fullscreen", False)
            except Exception:  # noqa: BLE001
                pass
            self.player_slot.pack(side="bottom", fill="x", before=self._right)
            self.sidebar.pack(side="left", fill="y", before=self._right)
            self.topbar.pack(side="top", fill="x", before=self.content)

    def show_page(self, route: str, params: dict) -> None:
        self.set_fullscreen_mode(False)
        spec = self.ctx.navigator.spec(route)
        old = self._page
        self._page = spec.factory(self.content, self.ctx, **params)
        self._page.pack(fill="both", expand=True)
        if old is not None:
            old.destroy()
        self.sidebar.set_active(route)
        self.topbar.set_title(spec.title)
        self.topbar.clear_search()
        self.topbar.set_search_visible(spec.searchable, _SEARCH_HINTS.get(route))
        self.topbar.set_user(self.ctx.session_service.current_user)

    def _on_search(self, query: str) -> None:
        if not query:
            return
        handler = getattr(self._page, "handle_search", None)
        if handler is None or not handler(query):
            show_toast(self, "Search is not available on this page yet.", "info")
