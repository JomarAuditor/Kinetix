"""Fixed values shared across Kinetix. Nothing here depends on the GUI."""

APP_NAME = "Kinetix"
APP_VERSION = "1.0.0"

# Media types used by favorites, history and the filter tabs.
MEDIA_MUSIC = "music"
MEDIA_MOVIE = "movie"
MEDIA_GAME = "game"
MEDIA_TYPES = (MEDIA_MUSIC, MEDIA_MOVIE, MEDIA_GAME)

# Password hashing (PBKDF2-HMAC-SHA256).
PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16

# Validation rules.
FULL_NAME_MIN = 2
FULL_NAME_MAX = 60
USERNAME_MIN = 3
USERNAME_MAX = 20
PASSWORD_MIN = 8

# History keeps only the newest items per user.
HISTORY_LIMIT = 50

# Default values for per-user settings (stored as text in user_settings).
SETTING_THEME = "theme"
SETTING_VOLUME = "default_volume"
SETTING_AUTOPLAY = "autoplay_next"
SETTING_SHOW_LYRICS = "show_lyrics_default"
SETTING_REMEMBER_POSITION = "remember_movie_position"

DEFAULT_USER_SETTINGS = {
    SETTING_THEME: "dark",
    SETTING_VOLUME: "70",
    SETTING_AUTOPLAY: "true",
    SETTING_SHOW_LYRICS: "true",
    SETTING_REMEMBER_POSITION: "false",
}

# Labels and icon names per media type (chips, tiles, placeholders).
MEDIA_LABELS = {MEDIA_MUSIC: "Music", MEDIA_MOVIE: "Movies", MEDIA_GAME: "Games"}
MEDIA_ICONS = {MEDIA_MUSIC: "music", MEDIA_MOVIE: "movie", MEDIA_GAME: "games"}
MEDIA_PLACEHOLDERS = {MEDIA_MUSIC: "music", MEDIA_MOVIE: "movie", MEDIA_GAME: "game"}

# Music defaults.
DEFAULT_MUSIC_QUERY = "pop hits"
SEARCH_RESULT_LIMIT = 25
FEATURED_TRACK_LIMIT = 8
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (student desktop project)"

# Dashboard.
DASHBOARD_FEATURED_COUNT = 5
DASHBOARD_LIST_COUNT = 4
DASHBOARD_FAVORITES_COUNT = 8
FEATURED_CACHE_SECONDS = 600

# Movies (Phase 5).
SETTING_MOVIE_VOLUME = "default_movie_volume"
DEFAULT_USER_SETTINGS[SETTING_MOVIE_VOLUME] = "70"
MOVIE_POSITION_KEY_PREFIX = "movie_position:"  # user_settings key = prefix + TMDB id, value = milliseconds
MOVIE_FIRST_YEAR = 2000
MOVIE_LAST_YEAR = 2026
