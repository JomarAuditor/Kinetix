"""Builds the services, window and navigation, and decides which view to show."""
from typing import Optional

from app.navigation import Navigator, Route
from app.state import AppContext, AppState
from data.repositories.user_repository import UserRepository
from presentation.components.dialogs import ConfirmDialog
from presentation.pages.auth.login_page import LoginPage
from presentation.pages.auth.signup_page import SignUpPage
from presentation.pages.base_page import PlaceholderPage
from presentation.pages.dashboard.dashboard_page import DashboardPage
from presentation.pages.favorites.favorites_page import FavoritesPage
from presentation.pages.games.games_page import GamesPage
from presentation.pages.movies.movies_page import MoviesPage
from presentation.pages.music.music_page import MusicPage
from presentation.pages.recent.recent_page import RecentPage
from presentation.pages.settings.account_page import AccountPage
from presentation.pages.settings.settings_page import SettingsPage
from presentation.windows.main_window import AppShell, MainWindow
from services.auth.auth_service import AuthService
from services.auth.session_service import SessionService
from services.featured_service import FeaturedService
from services.games.game_service import GameService
from services.library_service import LibraryService
from services.movies.movie_playback_service import MoviePlaybackService
from services.movies.movie_service import MovieService
from services.music.music_playback_service import MusicPlaybackService
from services.music.music_service import MusicService
from utils.logger import get_logger

logger = get_logger("application")

# (route, page title, sidebar icon, shown in the top bar with search?)
_PLACEHOLDER_PAGES = ()


class Application:
    def __init__(self) -> None:
        self.state = AppState()
        self.navigator = Navigator()
        self.session = SessionService(self.state)
        self.auth = AuthService(UserRepository())
        self.window = MainWindow()
        music_service = MusicService()
        movie_service = MovieService()
        game_service = GameService()
        self.ctx = AppContext(
            self.state, self.auth, self.session, self.navigator, self.request_logout,
            library=LibraryService(), featured=FeaturedService(music_service, movie_service, game_service),
            music_service=music_service, music_playback=MusicPlaybackService(),
            movie_service=movie_service, movie_playback=MoviePlaybackService(),
            game_service=game_service,
        )
        self._shell: Optional[AppShell] = None
        self._register_pages()
        self.navigator.set_handler(self._schedule_route)

    def _register_pages(self) -> None:
        nav = self.navigator
        nav.register(Route.LOGIN, "Sign in", LoginPage)
        nav.register(Route.SIGNUP, "Create account", SignUpPage)
        nav.register(Route.HOME, "Home", DashboardPage, searchable=True)
        nav.register(Route.MUSIC, "Music", MusicPage, searchable=True)
        nav.register(Route.MOVIES, "Movies", MoviesPage, searchable=True)
        nav.register(Route.GAMES, "Games", GamesPage, searchable=True)
        nav.register(Route.FAVORITES, "Favorites", FavoritesPage, searchable=True)
        nav.register(Route.RECENT, "Recently Played", RecentPage, searchable=True)
        nav.register(Route.SETTINGS, "Settings", SettingsPage, searchable=False)
        nav.register(Route.ACCOUNT, "Account", AccountPage, searchable=False)

    @staticmethod
    def _placeholder_factory(title: str, icon_name: str):
        return lambda parent, ctx, **_params: PlaceholderPage(parent, ctx, title, icon_name)

    def run(self) -> None:
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self.navigator.go(Route.LOGIN)
        self.window.mainloop()

    def _close(self) -> None:
        """Release VLC and background workers before the window closes."""
        self.ctx.music_playback.shutdown()
        if self.ctx.movie_playback:
            self.ctx.movie_playback.release()
        from utils import image_cache
        image_cache.shutdown()
        self.window.destroy()

    # ---- showing views ----
    def _schedule_route(self, route: str, params: dict) -> None:
        """Switch pages after the current click handler finishes (safe to destroy the old page)."""
        self.window.after(1, lambda: self._show_route(route, params))

    def _show_route(self, route: str, params: dict) -> None:
        if route in Route.AUTH_ROUTES:
            self._show_auth_page(route, params)
        elif not self.session.is_authenticated:
            self.navigator.go(Route.LOGIN)
        else:
            self._show_shell_page(route, params)

    def _show_auth_page(self, route: str, params: dict) -> None:
        if self.session.is_authenticated:
            self.navigator.go(Route.HOME)
            return
        page = self.navigator.spec(route).factory(self.window, self.ctx, **params)
        self.window.set_content(page)  # also removes the shell, if there was one
        self._shell = None

    def _show_shell_page(self, route: str, params: dict) -> None:
        if self._shell is None:
            self._apply_playback_settings()
            self._shell = AppShell(self.window, self.ctx)
            self.window.set_content(self._shell)
        self._shell.show_page(route, params)

    def _apply_playback_settings(self) -> None:
        """Volume, autoplay-next and lyrics-by-default come from the user's saved settings (or defaults)."""
        user = self.session.current_user
        if user is None:
            return
        saved = self.ctx.library.playback_settings(user.id)
        self.ctx.music_playback.configure(saved.volume, saved.autoplay_next, saved.show_lyrics)

    # ---- logout ----
    def request_logout(self) -> None:
        ConfirmDialog(self.window, "Log out?", "You will need to sign in again to use Kinetix.",
                      confirm_text="Log out", danger=True, on_confirm=self._logout)

    def _logout(self) -> None:
        self.ctx.music_playback.stop()
        if self.ctx.movie_playback:
            self.ctx.movie_playback.stop()
        self.session.end()
        logger.info("User signed out")
        self.navigator.go(Route.LOGIN)
