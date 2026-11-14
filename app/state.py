"""Shared application state (kept in memory only) and the context given to pages."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

from models.user import User

if TYPE_CHECKING:  # only for type hints, avoids circular imports
    from app.navigation import Navigator
    from services.auth.auth_service import AuthService
    from services.auth.session_service import SessionService
    from services.featured_service import FeaturedService
    from services.library_service import LibraryService
    from services.music.music_playback_service import MusicPlaybackService
    from services.music.music_service import MusicService
    from services.movies.movie_service import MovieService
    from services.movies.movie_playback_service import MoviePlaybackService
    from services.games.game_service import GameService


@dataclass
class AppState:
    current_user: Optional[User] = None


@dataclass
class AppContext:
    """Everything a page may need. Pages receive this as `ctx`."""
    state: AppState
    auth_service: "AuthService"
    session_service: "SessionService"
    navigator: "Navigator"
    request_logout: Callable[[], None]
    # Shared services added in Phase 3 and 4 (built once in app/application.py).
    library: Optional["LibraryService"] = None
    featured: Optional["FeaturedService"] = None
    music_service: Optional["MusicService"] = None
    music_playback: Optional["MusicPlaybackService"] = None
    # Phase 5: Movie services
    movie_service: Optional["MovieService"] = None
    movie_playback: Optional["MoviePlaybackService"] = None
    # Phase 6: Games service
    game_service: Optional["GameService"] = None
