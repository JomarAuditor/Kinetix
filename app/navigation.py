"""Routes, sidebar items and the Navigator that swaps pages."""
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple


class Route:
    LOGIN = "login"
    SIGNUP = "signup"
    HOME = "home"
    MUSIC = "music"
    MOVIES = "movies"
    GAMES = "games"
    FAVORITES = "favorites"
    RECENT = "recent"
    SETTINGS = "settings"
    ACCOUNT = "account"

    AUTH_ROUTES = (LOGIN, SIGNUP)


@dataclass(frozen=True)
class NavItem:
    route: str
    label: str
    icon: str


# Sidebar groups, in display order. Logout is handled separately (pinned at the bottom).
NAV_GROUPS: Tuple[Tuple[NavItem, ...], ...] = (
    (
        NavItem(Route.HOME, "Home", "home"),
        NavItem(Route.MUSIC, "Music", "music"),
        NavItem(Route.MOVIES, "Movies", "movie"),
        NavItem(Route.GAMES, "Games", "games"),
    ),
    (
        NavItem(Route.FAVORITES, "Favorites", "heart"),
        NavItem(Route.RECENT, "Recently Played", "clock"),
    ),
    (
        NavItem(Route.SETTINGS, "Settings", "settings"),
        NavItem(Route.ACCOUNT, "Account", "user"),
    ),
)


@dataclass
class PageSpec:
    route: str
    title: str
    factory: Callable  # factory(parent, ctx, **params) -> widget
    searchable: bool = False


class Navigator:
    """Register pages once, then call go(route). The app decides how to show them."""

    def __init__(self) -> None:
        self._specs: Dict[str, PageSpec] = {}
        self._handler: Optional[Callable[[str, dict], None]] = None
        self.current_route: Optional[str] = None

    def register(self, route: str, title: str, factory: Callable, searchable: bool = False) -> None:
        self._specs[route] = PageSpec(route, title, factory, searchable)

    def set_handler(self, handler: Callable[[str, dict], None]) -> None:
        self._handler = handler

    def spec(self, route: str) -> PageSpec:
        return self._specs[route]

    def has(self, route: str) -> bool:
        return route in self._specs

    def go(self, route: str, **params) -> None:
        if self._handler is None or route not in self._specs:
            return
        self.current_route = route
        self._handler(route, params)
