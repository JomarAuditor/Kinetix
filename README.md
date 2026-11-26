# Kinetix

**Kinetix** is a dark-themed desktop multimedia hub built with Python and CustomTkinter. It brings **Music**, **Free Official Movies**, and **Playable In-App Games** together into a single native desktop application with user accounts, persistent favorites, playback history, and embedded VLC media playback.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features and Functionalities](#2-features-and-functionalities)
3. [Technology Stack](#3-technology-stack)
4. [Complete Project Directory Structure](#4-complete-project-directory-structure)
5. [Installation Guide](#5-installation-guide)
6. [How to Run Kinetix Locally](#6-how-to-run-kinetix-locally)
7. [Application Architecture](#7-application-architecture)
8. [Database Documentation](#8-database-documentation)
9. [API and External Services](#9-api-and-external-services)
10. [Troubleshooting Guide](#10-troubleshooting-guide)
11. [Developer Guide](#11-developer-guide)
12. [Performance and Technical Notes](#12-performance-and-technical-notes)
13. [Project Limitations and Future Improvements](#13-project-limitations-and-future-improvements)

---

## 1. Project Overview

### What Kinetix Is
Kinetix is a cross-media desktop application written in Python using CustomTkinter. Rather than switching between separate browser tabs, music apps, and casual game websites, Kinetix unifies music streaming, curated free full-length movies, and interactive games inside one cohesive desktop interface.

### Problem It Addresses
- **Fragmented entertainment:** Users often jump between multiple web apps for music, free movies, and quick casual games.
- **Browser clutter & redirects:** Many free movie and game portals rely on pop-ups, heavy browser tabs, or external redirects. Kinetix plays music, video, and games directly inside the desktop window.
- **Unified personal library:** Favorites and recently played history across music, movies, and games are stored locally in one per-user SQLite database.

### Intended Users
- **Everyday desktop users** who want a lightweight, ad-free desktop hub for music, free official movies, and casual games.
- **Python / desktop UI students and developers** looking for a clean, layered CustomTkinter reference architecture separating `presentation/`, `services/`, `integrations/`, `data/`, and `models/`.

### How Features Work Together
When a user signs in, `Application` (`app/application.py`) initializes the `AppShell` (`presentation/windows/main_window.py`) with a persistent left `Sidebar`, a context-aware `TopBar` (with per-page search), and a persistent bottom `PlayerBar` for music. The `DashboardPage` aggregates featured picks from Music, Movies, and Games alongside the user's `Recently Played` and `Favorites` lists. Clicking any item routes directly to its dedicated page (`MusicPage`, `MoviesPage`, or `GamesPage`) with optional autoplay.

---

## 2. Features and Functionalities

### 2.1 Authentication & Account Management
- **What it does:** Local user registration, login, profile editing (full name, username, email), password changing, activity statistics (favorites count, songs played, movies watched), and logout.
- **How users interact:** On launch, users see `LoginPage` or switch to `SignUpPage`. Once signed in, clicking the user avatar/name in the `TopBar` or `Account` in the `Sidebar` opens `AccountPage`.
- **Implementing files:** `presentation/pages/auth/login_page.py`, `presentation/pages/auth/signup_page.py`, `presentation/pages/auth/auth_components.py`, `presentation/pages/settings/account_page.py`, `services/auth/auth_service.py`, `services/auth/password_service.py`, `services/auth/session_service.py`, `data/repositories/user_repository.py`, `core/validators.py`.
- **Internet required:** No (100% local SQLite with PBKDF2-HMAC-SHA256 password hashing).

### 2.2 Home Dashboard
- **What it does:** Displays a personalized welcome header, quick-launch `ServiceSelector` cards (Music, Movies, Games), a 5-item interleaved `Featured` strip, `Recently Played` list, and `Favorites` quick-access grid.
- **How users interact:** Click any service card to jump to that section, click a featured/recent/favorite item to open it, or click the heart/play buttons directly on cards and rows.
- **Implementing files:** `presentation/pages/dashboard/dashboard_page.py`, `presentation/pages/dashboard/service_selector.py`, `services/featured_service.py`, `services/library_service.py`.
- **Internet required:** Yes for `Featured` metadata and artwork; `Recently Played` and `Favorites` load from local SQLite.

### 2.3 Music Discovery, Playback & Synced Lyrics
- **What it does:** Searches tracks via iTunes Search API, displays featured tracks, resolves full audio streams via `yt-dlp` (with automatic fallback to 30-second iTunes previews if unavailable), plays audio via embedded VLC (`VlcPlayer`), manages a playback queue (`PlayerBar`), and displays live time-synced or plain lyrics (`LyricsPanel`) via LRCLIB.
- **How users interact:** Search from the `TopBar` on the Music page, click any track row to play/pause, use the persistent bottom `PlayerBar` (previous, play/pause, next, seek slider, volume/mute, favorite heart, lyrics toggle) across any page in the app.
- **Implementing files:** `presentation/pages/music/music_page.py`, `presentation/pages/music/music_library.py`, `presentation/pages/music/music_search.py`, `presentation/pages/music/music_player.py`, `presentation/pages/music/lyrics_panel.py`, `services/music/music_service.py`, `services/music/music_playback_service.py`, `integrations/api/itunes_client.py`, `integrations/api/lyrics_client.py`, `integrations/media/ytdlp_client.py`, `integrations/media/vlc_player.py`.
- **Internet required:** Yes.
- **Dependencies/Limitations:** Full-track audio requires `yt-dlp` and VLC Media Player installed; otherwise falls back to 30-second iTunes preview if VLC is present.

### 2.4 Free Official Movies & Embedded Video Player
- **What it does:** Discovers full-length free movies from curated official YouTube movie channels (defined in `config/movie_channels.py`), enriches metadata (2:3 posters, backdrops, ratings, genres, overviews, runtimes) via TMDB, verifies match confidence and rights status (`MovieMatchingService`), and plays video directly inside Kinetix using an embedded 16:9 VLC player (`VideoPlayer`) with fullscreen mode, seek, volume, and optional resume-position memory. Users can also paste an authorized `http://` or `https://` video URL on a movie's details page.
- **How users interact:** Browse the featured carousel banner and 8 category chips (`Popular`, `Action`, `Horror`, `Classics`, `Western`, `Family`, `Asian`, `Bollywood`), search via the `TopBar`, click a poster to open `MovieDetailsView`, and press Play.
- **Implementing files:** `presentation/pages/movies/movies_page.py`, `presentation/pages/movies/movie_search.py`, `presentation/pages/movies/movie_details.py`, `presentation/pages/movies/video_player.py`, `services/movies/movie_service.py`, `services/movies/movie_matching_service.py`, `services/movies/movie_playback_service.py`, `integrations/api/tmdb_client.py`, `integrations/media/ytdlp_client.py`, `integrations/media/vlc_player.py`, `data/repositories/movie_cache_repository.py`, `config/movie_channels.py`.
- **Internet required:** Yes, plus a `TMDB_API_KEY` in `.env` and VLC Media Player installed locally.

### 2.5 Playable In-App Games
- **What it does:** Provides built-in Arcade games (Neon Snake, Pong Duel, Brick Breaker, Flappy Rocket, Tic-Tac-Toe on `tk.Canvas`), Card games (Blackjack 21, High-Low Cards via Deck of Cards API), Word games (5-Letter Word Guess, Word Scramble via Datamuse Word API), and live Trivia quizzes across 24+ categories via Open Trivia DB. If `RAWG_API_KEY` is configured in `.env`, searching also returns RAWG game metadata (info-only).
- **How users interact:** Filter by `All Games`, `Arcade`, `Trivia`, `Cards`, or `Words`, search via `TopBar`, and click any game card to launch `GamePlayView` directly inside Kinetix.
- **Implementing files:** `presentation/pages/games/games_page.py`, `presentation/pages/games/game_search.py`, `presentation/pages/games/game_details.py`, `presentation/pages/games/arcade_games.py`, `services/games/game_service.py`, `integrations/api/opentdb_client.py`, `integrations/api/deck_client.py`, `integrations/api/word_api_client.py`, `integrations/api/rawg_client.py`, `utils/game_art.py`.
- **Internet required:** No for Arcade games; Yes for Trivia, Cards, Words, and optional RAWG search.

### 2.6 Favorites & Recently Played
- **What it does:** Displays all user-favorited items (`FavoritesPage`) with media-type filter tabs, search, and undoable removal toast; displays chronological play/watch/game history (`RecentPage`) grouped into `Today`, `Yesterday`, and `Earlier` with filter tabs, search, and `Clear History`.
- **Implementing files:** `presentation/pages/favorites/favorites_page.py`, `presentation/pages/recent/recent_page.py`, `services/library_service.py`, `data/repositories/favorites_repository.py`, `data/repositories/history_repository.py`.
- **Internet required:** No (stored in SQLite).

### 2.7 Settings & Preferences
- **What it does:** Per-user preferences for default music volume, default movie volume, autoplay next track, show lyrics by default, and remember movie playback position, plus an About Kinetix summary.
- **Implementing files:** `presentation/pages/settings/settings_page.py`, `data/repositories/settings_repository.py`, `services/library_service.py`.
- **Internet required:** No.

---

## 3. Technology Stack & Course Component Mapping (ITL313-18 / SIA 2 LAB)

### Core Architecture Components
1. **GUI (Graphical User Interface):**
   - **Tkinter & CustomTkinter (`customtkinter>=5.2.2`):** Kinetix is built on Python's standard `tkinter` event loop and `tk.Canvas` (used for smooth scrolling and built-in Arcade games) combined with **CustomTkinter** for modern dark-mode widgets, rounded cards, responsive grids, sliders, and dialogs. *(Note: Kinetix uses Tkinter/CustomTkinter rather than PyQt/PySide.)*
2. **Login System & User Authentication:**
   - **a. SQLite for User Data Storage (`sqlite3`):** Local database (`storage/kinetix.db`) storing user profiles (`id`, `full_name`, `username`, `email`), `password_hash`, `salt`, `iterations`, and `created_at` in the `users` table (`data/database.py`, `data/repositories/user_repository.py`).
   - **b. Password Hashing & Salting (`hashlib`, `secrets`, `hmac`):** Passwords are **never** stored in plain text. Kinetix uses **PBKDF2-HMAC-SHA256** (`services/auth/password_service.py`):
     - Generates a unique 16-byte (`SALT_BYTES = 16`) cryptographically random salt per user via `secrets.token_bytes(16)`.
     - Derives a 256-bit key using `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)` (`PBKDF2_ITERATIONS = 260_000`, configured in `config/constants.py`).
     - Stores the hex-encoded `password_hash`, `salt`, and `iterations` count in SQLite so older accounts remain verifiable even if the iteration count is increased later.
   - **c. Login & Verification Logic (`services/auth/auth_service.py`, `presentation/pages/auth/login_page.py`):**
     - The GUI provides input fields for **Username or Email** and **Password** (plus **Create Account** registration on `SignUpPage`).
     - On login, `AuthService.login()` looks up the user record by username or email (`UserRepository.get_stored_by_login()`).
     - `password_service.verify_password()` re-derives the hash from the entered password using the user's stored `salt` and `iterations`, then compares it against the stored `password_hash` in constant time using `hmac.compare_digest()` to prevent timing attacks.
     - If no matching user exists, `AuthService.login()` still runs `verify_password()` against a dummy hash (`_DUMMY_HASH`) so failed username lookups take the same time as wrong-password attempts, and displays a generic `"Incorrect username or password."` error.

### Full Technology Stack

| Technology | Version / Declaration | Role in Kinetix |
|---|---|---|
| **Python** | 3.10+ (verified on 3.14) | Core language and standard library (`sqlite3`, `hashlib`, `hmac`, `secrets`, `threading`, `concurrent.futures`, `queue`, `pathlib`) |
| **CustomTkinter** | `>=5.2.2` (6.0.0) | Modern dark-mode UI widgets (`CTk`, `CTkFrame`, `CTkScrollableFrame`, `CTkButton`, `CTkLabel`, `CTkSlider`, etc.) |
| **Tkinter** | Built into Python | Underlying GUI event loop, `tk.Canvas` (used by `arcade_games.py` and `CTkScrollableFrame`), native `winfo_id()` window handle for VLC |
| **SQLite** | Built into Python (`sqlite3`) | Local persistence for users, favorites, history, user settings, and movie metadata cache (`storage/kinetix.db`) |
| **Pillow (`PIL`)** | `>=10.0.0` | Image decoding, aspect-ratio cover cropping, rounded-corner masking, HiDPI icon rendering, and procedural game thumbnail generation |
| **requests** | `>=2.31.0` | HTTP client with persistent `Session` connection pooling for REST APIs and background image downloads |
| **python-dotenv** | `>=1.0.0` | Loads API keys and optional configuration from `.env` |
| **yt-dlp** | `>=2024.8.6` | Discovers recent uploads from official YouTube movie channels and resolves direct audio/video stream URLs |
| **python-vlc** + **VLC** | `>=3.0.18122` | Python bindings for `libvlc` powering audio playback (`MusicPlaybackService`) and embedded 16:9 video (`MoviePlaybackService`) |

---

## 4. Complete Project Directory Structure

```text
Kinetix/
├── main.py                              # Application entry point (calls app.bootstrap.run)
├── requirements.txt                     # Python package dependencies
├── .env.example                         # Template for API keys and optional settings
├── .gitignore                           # Git ignore rules (.env, __pycache__, .venv, storage runtime files)
├── README.md                            # Complete project documentation
│
├── app/                                 # Application lifecycle, routing, and shared state
│   ├── __init__.py
│   ├── application.py                   # Application class: wires services, MainWindow, Navigator, AppShell, shutdown
│   ├── bootstrap.py                     # Startup: creates storage dirs, initializes SQLite DB, launches Application
│   ├── navigation.py                    # Route constants, NAV_GROUPS sidebar spec, PageSpec, Navigator
│   └── state.py                         # AppState (current_user) and AppContext dataclass passed to all pages
│
├── assets/                              # Static visual assets and generated game thumbnails
│   ├── logos/                           # Kinetix window icon (.ico) and SVG/PNG brand logos
│   └── placeholders/                    # Fallback PNGs (music, movie, game, avatar) and games/ thumbnails
│
├── config/                              # Configuration, constants, theme, and channel registry
│   ├── __init__.py
│   ├── constants.py                     # App metadata, media types, PBKDF2/validation rules, default settings, limits
│   ├── movie_channels.py                # Curated list of official free YouTube movie channels & category mappings
│   ├── settings.py                      # Filesystem paths and .env getters (TMDB, YouTube, RAWG, min movie duration)
│   └── theme.py                         # Colors, Spacing, Sizes, and Fonts (single source of truth for UI styling)
│
├── core/                                # Domain-agnostic exceptions and input validators
│   ├── __init__.py
│   ├── exceptions.py                    # KinetixError, ValidationError, AuthenticationError, DatabaseError, ApiError, etc.
│   └── validators.py                    # Registration, login, profile update, and password change validation
│
├── data/                                # SQLite database layer and repositories
│   ├── __init__.py
│   ├── connection.py                    # open_connection() and connection_scope() context manager (PRAGMA foreign_keys=ON)
│   ├── database.py                      # SQLite SCHEMA definition and initialize_database()
│   └── repositories/
│       ├── __init__.py
│       ├── favorites_repository.py      # CRUD & counts for user favorites
│       ├── history_repository.py        # Upsert, list, clear, and counts for recently played history
│       ├── movie_cache_repository.py    # TTL-backed JSON cache in SQLite movie_cache table
│       ├── settings_repository.py       # Per-user key/value settings in user_settings table
│       └── user_repository.py           # User lookup, creation, profile update, password update
│
├── integrations/                        # External APIs and media engine wrappers
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── base_client.py               # Shared BaseClient with pooled requests.Session and error mapping
│   │   ├── deck_client.py               # Deck of Cards API client (Blackjack, High-Low)
│   │   ├── itunes_client.py             # iTunes Search API client (tracks, artwork, 30s previews)
│   │   ├── lyrics_client.py             # LRCLIB API client & LRC timestamp parser
│   │   ├── opentdb_client.py            # Open Trivia DB API client (categories & questions)
│   │   ├── rawg_client.py               # Optional RAWG.io API client (game metadata search)
│   │   ├── tmdb_client.py               # TMDB API client (movie search, details, posters/backdrops)
│   │   ├── word_api_client.py           # Datamuse Word API client (5-letter words, scrambles, definitions)
│   │   └── youtube_client.py            # YouTube Data API v3 client (optional helper)
│   └── media/
│       ├── __init__.py
│       ├── vlc_player.py                # python-vlc wrapper for audio & embedded video playback
│       └── ytdlp_client.py              # yt-dlp channel/search/stream resolver with in-memory TTL caches
│
├── models/                              # Plain Python dataclasses representing domain objects
│   ├── __init__.py
│   ├── game.py                          # GameItem, TriviaQuestion, PlayingCard, WordPuzzle
│   ├── media.py                         # Unified MediaItem used by Dashboard, Favorites, History, and Cards
│   ├── movie.py                         # Movie, YouTubeVideo, MatchedMovie, MatchConfidence, RightsStatus
│   ├── music.py                         # Track and Lyrics (synced LRC + plain text)
│   └── user.py                          # User dataclass (id, full_name, username, email, initials)
│
├── presentation/                        # CustomTkinter GUI layer
│   ├── __init__.py
│   ├── components/                      # Reusable UI widgets
│   │   ├── __init__.py
│   │   ├── buttons.py                   # PrimaryButton, SecondaryButton, GhostButton, DangerButton, LinkLabel, IconButton
│   │   ├── cards.py                     # MediaCard, MediaRow, FitLabel, Chip, HeartButton, SectionHeader, FavoriteTracker
│   │   ├── dialogs.py                   # ConfirmDialog, Toast, show_toast(), apply_window_icon()
│   │   ├── images.py                    # ImageView (async disk-cached rounded image loader with 2x HiDPI memory cache)
│   │   ├── inputs.py                    # TextField, SearchBar, Slider
│   │   ├── loaders.py                   # Spinner and StateMessage (loading / empty / error with Retry)
│   │   ├── media_controls.py            # TimeSlider, VolumeControl, format_media_time()
│   │   ├── sidebar.py                   # Fixed left navigation Sidebar
│   │   └── topbar.py                    # TopBar (page title, contextual SearchBar, user profile pill)
│   ├── pages/                           # Application screens
│   │   ├── __init__.py
│   │   ├── base_page.py                 # BasePage and PlaceholderPage
│   │   ├── auth/                        # LoginPage, SignUpPage, AuthShell
│   │   ├── dashboard/                   # DashboardPage, ServiceSelector
│   │   ├── favorites/                   # FavoritesPage with filter tabs & Undo toast
│   │   ├── games/                       # GamesPage, GameSearchSection, GamePlayView, ArcadeGame canvas games
│   │   ├── movies/                      # MoviesPage, MovieSearchSection, MovieDetailsView, VideoPlayer
│   │   ├── music/                       # MusicPage, FeaturedTracksSection, SearchResultsSection, PlayerBar, LyricsPanel
│   │   ├── recent/                      # RecentPage grouped by Today/Yesterday/Earlier
│   │   └── settings/                    # SettingsPage and AccountPage
│   ├── styles/                          # Styling helpers and scroll patching
│   │   ├── __init__.py
│   │   ├── colors.py                    # Re-exports Colors, Spacing, Sizes from config/theme.py
│   │   ├── icons.py                     # Pillow-drawn HiDPI vector-like icons and logo loader
│   │   ├── smooth_scroll.py             # CTkScrollableFrame mouse-wheel & teardown patch + scroll_to_top()
│   │   ├── typography.py                # Font factory helpers (title, section, card, body, small, tiny)
│   │   └── widgets.py                   # Shared widget style dictionaries (buttons, inputs, sliders, checkboxes)
│   └── windows/
│       ├── __init__.py
│       └── main_window.py               # MainWindow (CTk root) and AppShell (sidebar + topbar + content + player_slot)
│
├── services/                            # Business logic & orchestration (no Tkinter code)
│   ├── __init__.py
│   ├── featured_service.py              # Concurrent Dashboard Featured loader across Music, Movies, Games
│   ├── library_service.py               # Facade over Favorites, History, and User Settings repositories
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth_service.py              # Registration, login, profile & password updates
│   │   ├── password_service.py          # PBKDF2-HMAC-SHA256 hashing & verification
│   │   └── session_service.py           # In-memory current_user session state
│   ├── games/
│   │   ├── __init__.py
│   │   └── game_service.py              # Game catalog, search, trivia/deck/word loaders, optional RAWG integration
│   ├── movies/
│   │   ├── __init__.py
│   │   ├── movie_matching_service.py    # Title similarity & official-channel rights verification
│   │   ├── movie_playback_service.py    # VLC video playback state machine & event queue
│   │   └── movie_service.py             # Official-channel movie discovery, search, TMDB enrichment, SQLite cache
│   └── music/
│       ├── __init__.py
│       ├── music_playback_service.py    # VLC audio playback queue, background yt-dlp resolution, event pump
│       └── music_service.py             # Track search, featured tracks, lookup, and lyrics with TTL caching
│
├── storage/                             # Runtime data directory (contents gitignored except .gitkeep)
│   ├── cache/                           # Downloaded image cache (*.img)
│   ├── logs/                            # Rotating application log (kinetix.log)
│   └── kinetix.db                       # SQLite database (auto-created on first run)
│
└── utils/                               # Shared non-GUI utilities
    ├── __init__.py
    ├── game_art.py                      # Procedural PNG generator for Arcade, Card, Word, and Trivia game cards
    ├── generate_game_art.py             # CLI wrapper to regenerate game thumbnails
    ├── helpers.py                       # run_in_background(), format_duration(), relative_time()
    ├── image_cache.py                   # ThreadPoolExecutor image downloader, disk cache, placeholder PNGs
    └── logger.py                        # RotatingFileHandler + console warning logger
```

### Generated vs. Manual Files
- **Automatically generated at runtime (do not commit):** `storage/kinetix.db`, `storage/cache/*.img`, `storage/logs/kinetix.log`, `assets/placeholders/*.png`, `assets/placeholders/games/*.png`, `.env` (user-created from `.env.example`), `__pycache__/`, `.venv/`.

---

## 5. Installation Guide

### Prerequisites
1. **Operating System:** Windows 10/11 (primary target), macOS, or Linux with a graphical desktop environment.
2. **Python:** Python 3.10 or newer (tested on Python 3.14).
3. **VLC Media Player:** Required for music and movie playback. Download from [videolan.org](https://www.videolan.org/vlc/).
   - **Important (Windows):** Install the **64-bit** version of VLC if your Python is 64-bit (most modern installations). Mismatched 32-bit/64-bit architectures will prevent `python-vlc` from loading `libvlc.dll`.
4. **Git** (optional, for cloning).

### Step 1: Clone or Download the Repository

```powershell
git clone <repository-url>
cd Kinetix
```

### Step 2: Create and Activate a Virtual Environment

**Windows PowerShell:**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once.)*

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` in a text editor and add your keys:
- `TMDB_API_KEY=` — **Required for Movies.** Get a free API key from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
- `YOUTUBE_API_KEY=` — Optional (YouTube Data API v3).
- `RAWG_API_KEY=` — Optional; enables searching external game metadata on RAWG.io.
- `MOVIE_MIN_DURATION_MINUTES=` — Optional (default `60`); minimum YouTube upload length in minutes to count as a full-length movie (clamped between `20` and `240`).

*(Note: Music and built-in/API Games work without any API keys.)*

---

## 6. How to Run Kinetix Locally

1. Open a terminal in the `Kinetix` project root directory.
2. Activate your virtual environment (if using one):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
3. Launch the application:
   ```powershell
   py main.py
   ```
   *(On macOS/Linux: `python3 main.py`)*

### What to Expect on Startup
- `app/bootstrap.py` automatically creates `storage/`, `storage/cache/`, and `storage/logs/` and initializes `storage/kinetix.db`.
- The Kinetix window opens centered on screen (`1440x900` default, minimum `1280x720`) showing the **Sign in** screen.
- Create a new account via **Create account** or sign in with an existing local account.
- Close the window normally (`X` button) to cleanly stop VLC players, shut down background image workers, and exit.

---

## 7. Application Architecture

Kinetix follows a clean, layered desktop architecture:

```text
User Action (Click / Search / Scroll)
    │
    ▼
Presentation Layer (Pages & Components, Main Tk Thread)
    │  └─ Calls run_in_background() for I/O
    ▼
Service Layer (MusicService, MovieService, GameService, AuthService, LibraryService)
    │  ├─ Checks In-Memory / SQLite Cache & In-Flight Locks
    │  └─ Calls Integrations / Repositories
    ▼
Integrations & Data Layer (BaseClient Session, yt-dlp, VLC, SQLite connection_scope)
    │
    ▼
Result Queue / Future (Thread-safe handoff via after() polling)
    │
    ▼
Main Tk Thread (Updates UI widgets safely if winfo_exists() is True)
```

### Key Architectural Patterns
- **Single Root Window + Swappable Shell:** `MainWindow` (`ctk.CTk`) swaps between Auth pages and `AppShell`. Inside `AppShell`, `Sidebar`, `TopBar`, and `PlayerBar` stay mounted while `show_page(route, params)` swaps only the active `BasePage` inside `AppShell.content`.
- **Thread-Safe UI Updates:** Background I/O runs via `utils.helpers.run_in_background()` (daemon thread + `queue.Queue` polled via `widget.after()`), `utils.image_cache` (`ThreadPoolExecutor` + `Future` polled by `ImageView`), or `MusicPlaybackService` / `MoviePlaybackService` event queues. Background threads **never** touch Tkinter widgets directly.
- **Stale-Response Protection:** Pages increment integer tokens (`_search_token`, `_catalog_token`, `_route_token`, `_load_token`) before launching async tasks and ignore callbacks whose token no longer matches or whose widget was destroyed (`_alive()`).

---

## 8. Database Documentation

Kinetix uses a local SQLite database at `storage/kinetix.db`, initialized automatically by `data/database.py` (`initialize_database()`). Every database operation opens a short-lived connection via `data/connection.py` (`connection_scope()`) with `PRAGMA foreign_keys = ON`, automatic commit/rollback, and guaranteed `close()`, making it safe across worker threads.

### Tables

| Table | Purpose | Key Columns & Constraints |
|---|---|---|
| `users` | Local user accounts | `id` (PK), `full_name`, `username` (UNIQUE NOCASE), `email` (UNIQUE NOCASE), `password_hash`, `salt`, `iterations`, `created_at` |
| `favorites` | Saved items across music, movies, games | `id` (PK), `user_id` (FK → `users.id` ON DELETE CASCADE), `media_type` (`music`\|`movie`\|`game`), `external_id`, `title`, `subtitle`, `image_url`, `created_at`; `UNIQUE(user_id, media_type, external_id)` |
| `history` | Recently played items per user | `id` (PK), `user_id` (FK → `users.id` ON DELETE CASCADE), `media_type`, `external_id`, `title`, `subtitle`, `image_url`, `last_accessed`; `UNIQUE(user_id, media_type, external_id)` |
| `user_settings` | Per-user preferences & saved movie resume positions | `user_id` (FK → `users.id` ON DELETE CASCADE), `key`, `value`; `PRIMARY KEY(user_id, key)` |
| `youtube_movies` | Metadata table for YouTube movie records | `id` (PK), `video_id` (UNIQUE), `tmdb_movie_id`, `title`, `channel_name`, `channel_id`, `duration_seconds`, `playback_method`, `rights_verified`, etc. |
| `movie_cache` | Cached official-channel discovery & search payloads | `id` (PK), `cache_key` (UNIQUE), `cache_data` (JSON), `expires_at`, `created_at` |

### Backup & Reset
- **Backup:** Copy `storage/kinetix.db` while Kinetix is closed.
- **Reset:** Delete `storage/kinetix.db` while Kinetix is closed; it will be recreated empty on next launch.

---

## 9. API and External Services

| Service | Feature | Auth / Key | Offline Behavior |
|---|---|---|---|
| **iTunes Search API** | Music search, featured tracks, artwork, 30s previews | None | Shows connection error with Retry |
| **LRCLIB API** | Synced (LRC) and plain song lyrics | None | Shows `"Lyrics not available"` or connection error |
| **YouTube (via `yt-dlp`)** | Audio streams for music; official free movie channels & video streams | None | Music falls back to 30s iTunes preview; Movies show error |
| **TMDB API** | Movie search, posters, backdrops, ratings, genres, overviews | `TMDB_API_KEY` in `.env` | Movies page prompts to add `TMDB_API_KEY` |
| **Open Trivia DB** | Trivia categories & 10-question rounds | None | Falls back to 4 default trivia categories in catalog |
| **Deck of Cards API** | Shuffled decks & card images for Blackjack & High-Low | None | Shows error state with Retry |
| **Datamuse Word API** | 5-letter words, scrambles, and definitions | None | Shows error state with Retry |
| **RAWG.io API** | Optional external game metadata search | `RAWG_API_KEY` in `.env` | Skipped silently if key is not set |

---

## 10. Troubleshooting Guide

- **`py` or `python` is not recognized:** Install Python 3.10+ from python.org and check **"Add Python to PATH"**, or use the full path to `python.exe`.
- **`ModuleNotFoundError` (e.g. `customtkinter`, `PIL`, `yt_dlp`, `vlc`):** Ensure your virtual environment is activated and run `pip install -r requirements.txt`.
- **"VLC Media Player was not found":** Install VLC from videolan.org matching your Python architecture (64-bit Python requires 64-bit VLC) and restart Kinetix.
- **"Add your TMDB key in .env":** Create `.env` from `.env.example` in the project root and set `TMDB_API_KEY=<your_key>`.
- **Movie or Music stream fails to play:** Check your internet connection and update `yt-dlp` (`pip install -U yt-dlp`), as YouTube extractors change periodically.
- **Database errors:** Check `storage/logs/kinetix.log`. Ensure the `storage/` folder is writable and no other process holds a lock on `storage/kinetix.db`.
- **Slow or laggy scrolling:** Ensure `presentation/styles/smooth_scroll.py` is active (enabled automatically in `MainWindow.__init__`) and avoid resizing the window rapidly while dozens of uncached images are still downloading.

---

## 11. Developer Guide

- **Adding a new page:**
  1. Create a subclass of `BasePage` (`presentation/pages/base_page.py`).
  2. Add a route constant and `NavItem` in `app/navigation.py`.
  3. Register it in `Application._register_pages()` (`app/application.py`).
- **Adding a reusable widget:** Place it in `presentation/components/` and read all colors, spacing, and sizes from `config/theme.py` (`Colors`, `Spacing`, `Sizes`) and `presentation/styles/typography.py`.
- **Modifying APIs or business logic:** Keep HTTP clients in `integrations/api/`, domain dataclasses in `models/`, and orchestration/caching in `services/`. Never import `tkinter` or `customtkinter` inside `services/`, `data/`, or `integrations/`.
- **Verifying changes:** Run `python -m compileall -q app config core data integrations models presentation services utils main.py` and launch `py main.py` to test navigation, scrolling, search, and playback.

---

## 12. Performance and Technical Notes

- **Tear-free Windows Scrolling (`presentation/styles/smooth_scroll.py`):** Patches `CTkScrollableFrame` to ignore destroyed or unmapped (`pack_forget()`) frames, safely validate `event.widget`, scroll in smooth 1px increments (`56px` per notch), and flush `canvas.update_idletasks()` synchronously so child widgets never lag behind the canvas viewport.
- **Reduced UI Redraw Overhead:** `FitLabel` caches its last measured width; `MediaCard` and `MediaRow` skip redundant `configure()` calls on repeated hover events; `ImageView` skips redundant `configure()` calls for already-rendered image keys and polls futures at 40ms; `PlayerBar` only updates time labels when `MM:SS` text changes; `MoviesPage` avoids `place_configure` animation loops inside scrollable frames.
- **HTTP Connection Pooling (`integrations/api/base_client.py`):** Uses a persistent `requests.Session` with `HTTPAdapter(pool_connections=16, pool_maxsize=16)` and context-managed responses so TCP/TLS connections are reused across API calls.
- **Multi-Layer Caching & Deduplication:**
  - `MusicService`: In-memory LRU/TTL caches for track searches, track lookups, featured tracks, and lyrics.
  - `YtDlpClient`: 4-hour in-memory TTL caches for both resolved video (`_STREAM_CACHE`) and audio (`_AUDIO_CACHE`) URLs, plus per-key in-flight locks for video resolution.
  - `MovieService`: SQLite `movie_cache` with TTL + per-key in-flight locks (`_discover_locks`, `_search_locks`) so concurrent requests (e.g. Dashboard + MoviesPage) share one network fetch, and parallelized TMDB + YouTube search execution.
  - `GameService`: Cached game catalog (`is_catalog_cached`) so category switching renders immediately without a loading flash, plus 5-minute caching for optional RAWG searches/details.
  - `utils/image_cache.py` & `ImageView`: Background `ThreadPoolExecutor(max_workers=10)`, disk cache in `storage/cache/`, and an in-memory `OrderedDict` (limit 300) of 2x HiDPI `CTkImage` objects.

---

## 13. Project Limitations and Future Improvements

### Current Working Features
- Local authentication, profile management, favorites, history, and per-user settings.
- Music search, featured tracks, queue playback, synced/plain lyrics, and 30s preview fallback.
- Official-channel free movie discovery, TMDB enrichment, details view, and embedded VLC playback.
- Built-in Arcade games, live Card/Word/Trivia API games, and optional RAWG metadata search.

### Known Limitations
- **Theme:** Only Dark theme is active; the Light theme option in `SettingsPage` is marked "Coming soon".
- **External Dependencies:** Movie discovery requires a `TMDB_API_KEY`; audio/video playback requires VLC Media Player installed locally and matching Python's bitness; YouTube stream availability depends on `yt-dlp` and network access.
- **No Automated Test Suite:** The project does not yet include a `pytest`/`unittest` suite for automated UI and integration testing.

### Possible Future Improvements
- Implement Light theme support across `config/theme.py` and `presentation/styles/`.
- Add playlist creation and management for Music.
- Add automated unit tests for services, repositories, and validators.

---

## 14. Contributors

- **Jomar Auditor** ([@JomarAuditor](https://github.com/JomarAuditor)) — `jomar.auditor@neu.edu.ph`
- **Christian Adlawan** ([@Chandara4you](https://github.com/Chandara4you)) — `christian.adlawan@neu.edu.ph`

