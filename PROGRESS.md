# Kinetix - Progress

## Phases finished
- Phase 1: config, models, SQLite, repositories, auth + password + session services, validators, logger.
- Phase 2: startup, window, styles, shared components, authenticated shell, Login and Sign Up.
- Phase 3: image loader, shared cards/rows, Dashboard.
- Phase 4: Music backend, persistent player bar, Music page.
- Phase 5: Movies — free official-channel discovery, TMDB metadata enrichment, search, details view, and embedded VLC video player.
- Phase 6: Games — Playable in-app games backed by free public REST APIs (Open Trivia DB, Deck of Cards API, Datamuse Word API), search, favorites, and history (RAWG removed).

## Run
    pip install -r requirements.txt
    py main.py

## Phase 5 — Movies (completed)

### Features & Architecture
- **Browse & Discovery (`movies_page.py`, `movie_service.py`)**:
  - Featured movie banner at the top with backdrop, title, year, genre, runtime, star rating, short description, Play Now, Details, and Favorite buttons.
  - Interactive category filter chips (`Popular`, `Action`, `Horror`, `Classics`, `Western`, `Family`, `Asian`, `Bollywood`) that load one category on demand and cache results in SQLite (`movie_cache`) for 2 hours.
  - 2:3 poster grid using `MediaCard` (`aspect_ratio=Sizes.POSTER_ASPECT`) with poster image, title, subtitle, rating, heart toggle, and play button.
  - Clear loading, empty, and error states (`StateMessage`), showing `"Add your TMDB key in .env"` if `TMDB_API_KEY` is missing while keeping the rest of the app functional.
- **Search (`movie_search.py`)**:
  - TopBar search routes to `MoviesPage.handle_search(query)` and displays results in `MovieSearchSection` with verified vs unverified status tags.
- **Movie Details & Embedded Player (`movie_details.py`, `video_player.py`)**:
  - Details view displays Back button, 2:3 poster, title, year, runtime, rating, genre chips (`Chip`), rights status chip, description, Favorite toggle, Play button, and `"Play from URL"` input for authorized links (`"TMDB provides movie information only. Playback depends on sources supported by yt-dlp."`).
  - Embedded 16:9 VLC video player (`Colors.VIDEO_BACKGROUND` black stage) with clear `"Press Play to start"` state, loading/error overlays, `TimeSlider`, `VolumeControl`, play/pause, stop, and fullscreen toggle (`Escape` to exit).
  - Cross-platform VLC window handle embedding (`set_hwnd` on Windows, `set_xwindow` on Linux, `set_nsobject` on macOS).
- **Coexistence, Favorites, History & Settings**:
  - Starting a movie pauses the music player if playing (without clearing its queue) and shows `"Music paused"` toast. Leaving details or Movies stops and releases the movie VLC player cleanly.
  - Heart buttons toggle `favorites_repository` (`media_type='movie'`) and stay synced via `FavoriteTracker`.
  - Opening or playing a movie logs to `history_repository`.
  - Reads `default_movie_volume` (fallback `default_volume` / `70`) and `remember_movie_position` from `settings_repository` via `LibraryService`, saving and resuming playback position when enabled.
- **Dashboard / Library Route Parameters**:
  - `Route.MOVIES` accepts `item: MediaItem` and `autoplay: bool = False` (plus optional `matched_movie: MatchedMovie`). Clicking a movie from Dashboard, Favorites, or Recently Played resolves its TMDB/YouTube details and opens `MovieDetailsView` (and auto-starts playback when `autoplay=True` and a verified source exists).

### Added & Modified Files (Phase 5)
| File | Role |
|---|---|
| `presentation/pages/movies/movies_page.py` | Main Movies page (featured banner, category chips, 2:3 poster grid, route param handling) |
| `presentation/pages/movies/movie_search.py` | `MovieSearchSection` for TopBar search results |
| `presentation/pages/movies/movie_details.py` | `MovieDetailsView` (poster, genres, overview, favorites, Play from URL, embedded player) |
| `presentation/pages/movies/video_player.py` | `VideoPlayer` (16:9 VLC embed, fullscreen + Escape, music pause, position resume) |
| `presentation/components/media_controls.py` | Reusable `TimeSlider`, `VolumeControl`, and `format_media_time` |
| `presentation/components/cards.py` | Added `aspect_ratio` support on `MediaCard` for 2:3 movie posters |
| `presentation/windows/main_window.py` | Added `AppShell.set_fullscreen_mode()` |
| `presentation/styles/icons.py` | Added `arrow_left`, `stop`, `fullscreen`, `exit_fullscreen`, `link` icons |
| `config/theme.py` | Added poster, banner, and 16:9 video size constants to `Sizes` |
| `config/movie_channels.py` | Cleaned up verified official YouTube movie channel list and categories |
| `data/repositories/settings_repository.py` | Added `get(user_id, key)` helper |
| `services/library_service.py` | Added `MovieSettings`, `movie_settings()`, `get_movie_position()`, `save_movie_position()` |
| `services/movies/movie_service.py` | Parallel TMDB enrichment, key validation, `resolve_media_item()` for Dashboard/History/Favorites |
| `services/movies/movie_matching_service.py` | Recognizes `OFFICIAL_MOVIE_CHANNELS` as `RightsStatus.VERIFIED` |
| `services/movies/movie_playback_service.py` | Added `play_url()`, initial `volume`, and `seek_ms()` |
| `integrations/api/tmdb_client.py` | Allowed pre-2000 classic films in `search_movies()` |
| `integrations/media/vlc_player.py` | Cross-platform `set_window()` (`set_hwnd`, `set_xwindow`, `set_nsobject`) and `set_time_ms()` |
| `integrations/media/ytdlp_client.py` | Safe thumbnail parsing, `get_video_info()`, and URL support in `resolve_video()` |
| `models/movie.py` | Added `external_key` and `yt:` fallback ID in `to_media_item()` |
| `app/application.py` | Routed `Route.MOVIES` directly to `MoviesPage` (removed obsolete `movie_player.py`) |

### Reusable Components & Symbols
- `presentation.components.media_controls`: `TimeSlider`, `VolumeControl`, `format_media_time`
- `presentation.components.cards`: `MediaCard(..., aspect_ratio=Sizes.POSTER_ASPECT)`
- `presentation.pages.movies.video_player`: `VideoPlayer`
- `presentation.pages.movies.movie_details`: `MovieDetailsView`
- `presentation.pages.movies.movie_search`: `MovieSearchSection`
- `services.library_service`: `MovieSettings`, `LibraryService.movie_settings`, `get_movie_position`, `save_movie_position`

## Phase 6 — Games (completed)

### Features & Architecture
- **RAWG Removed**: Deleted `integrations/api/rawg_client.py`, removed `RAWG_API_KEY` from `.env.example` / `config/settings.py`, and cleaned legacy RAWG rows from `favorites`/`history` in `initialize_database()`.
- **Playable In-App API Games (`games_page.py`, `game_search.py`, `game_details.py`, `game_service.py`)**:
  - **Open Trivia DB (`opentdb_client.py`)**: Live categories (`api_category.php`) and 10-question multiple-choice rounds (`api.php`) with Easy/Medium/Hard difficulty, 20s countdown timer, streak bonus, and instant feedback.
  - **Deck of Cards API (`deck_client.py`)**: Live shuffled decks and real card PNG artwork (`ImageView`) for **Blackjack 21** and **High-Low Cards**.
  - **Datamuse Word API (`word_api_client.py`)**: Live dictionary words and clues for **5-Letter Word Guess** and **Word Scramble**.
  - **Browse, Search, Favorites, History & High Scores**: Featured row, category filter chips (`All Games`, `Trivia`, `Cards`, `Words`), TopBar search (`GameSearchSection`), Favorite hearts (`media_type='game'`), played history logging (`history_repository`), per-user best scores saved via `LibraryService`, and Dashboard `item` routing — all running 100% inside Kinetix with zero API keys and zero browser redirects.

### Added & Modified Files (Phase 6)
| File | Role |
|---|---|
| `integrations/api/opentdb_client.py` | `OpenTdbClient` for live trivia categories and questions (no key required) |
| `integrations/api/deck_client.py` | `DeckOfCardsClient` for live card decks and card PNGs (no key required) |
| `integrations/api/word_api_client.py` | `WordApiClient` (Datamuse) for word puzzles and definitions |
| `models/game.py` | `GameItem`, `TriviaQuestion`, `PlayingCard`, `WordPuzzle` |
| `services/games/game_service.py` | Orchestrates live game catalog, search, trivia rounds, decks, and word puzzles |
| `presentation/pages/games/games_page.py` | `GamesPage` (featured row, category filters, grid, TopBar search, route `item` handling) |
| `presentation/pages/games/game_search.py` | `GameSearchSection` for Games search results |
| `presentation/pages/games/game_details.py` | `GamePlayView` (in-app interactive arenas for Trivia, Blackjack, High-Low, Word Guess, Word Scramble) |
| `presentation/pages/games/__init__.py` | Exports `GamesPage`, `GamePlayView`, `GameDetailsView`, `GameSearchSection` |
| `services/library_service.py` | Added `get_game_high_score()` and `save_game_high_score()` |
| `data/database.py` | Cleaned legacy numeric RAWG entries from `favorites` and `history` |
| `presentation/pages/dashboard/dashboard_page.py` | Removed RAWG key text from empty Featured state |
| `config/settings.py`, `.env.example` | Removed `RAWG_API_KEY` |
| `app/state.py`, `app/application.py` | Wired shared `GameService` into `AppContext` and `Route.GAMES` to `GamesPage` |

### Reusable Components & Symbols (Phase 6)
- `models.game`: `GameItem`, `TriviaQuestion`, `PlayingCard`, `WordPuzzle`
- `services.games.game_service`: `GameService`
- `presentation.pages.games`: `GamesPage`, `GamePlayView`, `GameDetailsView`, `GameSearchSection`
- `services.library_service`: `LibraryService.get_game_high_score`, `LibraryService.save_game_high_score`

## Next
- Phase 7: Dedicated Favorites page, Recently Played page, Settings page, and Account page.

## Navigation API (app/navigation.py)
- `Route.HOME, MUSIC, MOVIES, GAMES, FAVORITES, RECENT, SETTINGS, ACCOUNT, LOGIN, SIGNUP`
- `ctx.navigator.go(Route.MOVIES, item=media_item, autoplay=False)`
- `navigator.register(route, title, factory, searchable=False)`

## State / context API (app/state.py)
- `AppState.current_user: Optional[User]`
- `AppContext` (pages receive it as `ctx`): `ctx.state`, `ctx.auth_service`, `ctx.session_service`, `ctx.navigator`, `ctx.request_logout()`, `ctx.library`, `ctx.featured`, `ctx.music_service`, `ctx.music_playback`, `ctx.movie_service`, `ctx.movie_playback`.
