# Kinetix Backend Architecture

## Overview

Kinetix follows a layered architecture with clear separation of concerns:

1. **Presentation Layer** - UI components and pages (CustomTkinter)
2. **Service Layer** - Business logic and orchestration
3. **Integration Layer** - External API clients and media handlers
4. **Data Layer** - Database repositories and models

## Core Services

### Authentication & Session Management

- **AuthService** (`services/auth/auth_service.py`)
  - User registration and login
  - Password hashing with bcrypt
  - Session token generation
  
- **SessionService** (`services/auth/session_service.py`)
  - In-memory session state management
  - Current user tracking

### Music Services

- **MusicService** (`services/music/music_service.py`)
  - Search and featured music via iTunes API
  - Track lookup by ID
  - Lyrics fetching via LRCLIB API

- **MusicPlaybackService** (`services/music/music_playback_service.py`)
  - Persistent music player state
  - Queue management
  - VLC audio playback integration
  - yt-dlp audio stream resolution
  - Volume, seek, next/previous controls
  - Subscriber pattern for UI updates

### Movie Services (Phase 5 Complete)

- **MovieService** (`services/movies/movie_service.py`)
  - TMDB movie metadata (search, details, discover by category)
  - YouTube full-length movie discovery via yt-dlp
  - Movie-to-video matching with confidence scoring
  - Featured/popular movies (for Dashboard)
  - Supported categories: popular, 2000s, 2010s, 2020s

- **MovieMatchingService** (`services/movies/movie_matching_service.py`)
  - Matches TMDB movies to YouTube videos
  - Compares: title similarity, release year, duration
  - Returns confidence: STRONG, POSSIBLE, WEAK, REJECTED
  - Filters trailers, clips, reviews, reactions, shorts
  - Source rights verification system

- **MoviePlaybackService** (`services/movies/movie_playback_service.py`)
  - VLC video player state management
  - Stream resolution via yt-dlp for authorized sources
  - Playback controls: play, pause, stop, seek, volume
  - Event-driven architecture (STATE_CHANGED, PROGRESS, ERROR)
  - Music playback coordination (auto-pause)

### Library Services

- **LibraryService** (`services/library_service.py`)
  - User favorites management (music, movies, games)
  - Watch history tracking
  - Playback settings (volume, autoplay, lyrics visibility)

- **FeaturedService** (`services/featured_service.py`)
  - Dashboard content aggregation
  - Featured items from multiple services

## External Integrations

### API Clients

All API clients extend `BaseClient` (`integrations/api/base_client.py`) which provides:
- Timeout handling (10 seconds default)
- Error handling with custom exceptions
- JSON response parsing

#### iTunes API (`integrations/api/itunes_client.py`)
- Music search and lookup
- 30-second preview URLs
- No API key required

#### TMDB API (`integrations/api/tmdb_client.py`)
- Movie search by title, ID lookup, discover by category
- Poster and backdrop images (w342 and w780 sizes)
- Genre mapping and release year filtering (2000-2026)
- Requires `TMDB_API_KEY` in .env
- Supports both API key and read access token formats
- Methods:
  - `search_movies(query, page)` → List[Movie]
  - `get_movie_details(tmdb_id)` → Optional[Movie]
  - `discover_by_category(category, page, limit)` → List[Movie]
  - `popular_movies(page, limit)` → List[Dict] (simplified for Dashboard)

#### LRCLIB API (`integrations/api/lyrics_client.py`)
- Synced lyrics by track, artist, album, duration
- No API key required

#### RAWG API (`integrations/api/rawg_client.py`)
- Game search and discovery (Phase 6)
- Requires `RAWG_API_KEY` in .env

### Media Handlers

#### VLC Player (`integrations/media/vlc_player.py`)
- Wrapper around python-vlc
- Supports both audio and video playback
- Window embedding for video (platform-specific)
- Volume control, seek, state management
- Event callbacks for end-of-playback and errors
- Proper resource cleanup

#### yt-dlp Client (`integrations/media/ytdlp_client.py`)
- Audio stream resolution for music (Phase 4)
- YouTube movie search and video metadata extraction (Phase 5)
- Quality selection and format filtering
- Timeout and retry handling
- Methods:
  - `resolve_audio(artist, title, duration_seconds)` → ResolvedAudio (raises MediaSourceError)
  - `search_youtube_movies(title, year, min_duration_minutes)` → List[YouTubeSearchResult]
  - `resolve_video(video_id)` → ResolvedVideo (raises MediaSourceError)
- Filters trailers, teasers, clips, reviews, reactions, shorts during movie search
- Prefers combined video+audio formats for playback

## Data Layer

### Database

SQLite database managed by `data/database.py`:
- `users` - User accounts
- `favorites` - Favorited media items (music, movies, games)
- `history` - Watch/play history
- `settings` - User preferences

### Repositories

All repositories follow the repository pattern for database access:

- **UserRepository** (`data/repositories/user_repository.py`)
  - CRUD operations for users
  - Username uniqueness checks

- **FavoritesRepository** (`data/repositories/favorites_repository.py`)
  - Add/remove favorites
  - List favorites by user and media type
  - Toggle favorite state

- **HistoryRepository** (`data/repositories/history_repository.py`)
  - Record media access
  - Update last accessed timestamp
  - List recent items by user and media type

- **SettingsRepository** (`data/repositories/settings_repository.py`)
  - Save/load user preferences
  - Playback settings (volume, autoplay, lyrics)
  - Future: app-wide settings

### Models

Domain models are simple dataclasses:

- **User** (`models/user.py`) - User account with encrypted password
- **MediaItem** (`models/media.py`) - Unified media representation (music, movies, games)
- **Track** (`models/music.py`) - Music track with artist, album, duration
- **Movie** (`models/movie.py`)
  - `Movie` - TMDB movie metadata (tmdb_id, title, original_title, release_year, poster_url, backdrop_url, overview, genres, rating, runtime)
  - `YouTubeVideo` - YouTube video metadata from yt-dlp (video_id, title, channel_name, channel_id, duration_seconds, description, thumbnail_url, upload_date)
  - `MatchedMovie` - Combined TMDB movie + YouTube video with match confidence and rights status
  - `MatchConfidence` enum - STRONG, POSSIBLE, WEAK, REJECTED
  - `RightsStatus` enum - VERIFIED, UNVERIFIED, BLOCKED

## Navigation & State

### Navigation System (`app/navigation.py`)

- **Routes** - String constants for each page
- **Navigator** - Centralized page routing
  - Page factory registration
  - Route parameter support
  - Searchable page marking

### Application State (`app/state.py`)

- **AppState** - In-memory session state (current user)
- **AppContext** - Dependency injection container
  - All services available to pages
  - Session management
  - Navigation
  - Logout handler

## Movie Discovery and Playback Architecture (Phase 5)

### Movie Discovery Flow

```
User searches for movie OR browses category
    ↓
MoviesPage
    ↓
[Background Thread] MovieService.search_matched_movies(query)
    OR MovieService.discover_matched_movies(category)
    ↓
For each TMDB movie:
    ↓
YtDlpClient.search_youtube_movies(title, year, min_duration=60)
    ↓
MovieMatchingService.match_movie(movie, video)
    → Title similarity >= 75%?
    → Year within ±1 year?
    → Duration within ±20% of TMDB runtime?
    → Not a trailer/clip/review/reaction?
    ↓
MovieMatchingService.check_rights(movie, video)
    → Verified channel? (config/movie_sources.json)
    → Public domain? (config/movie_sources.json)
    → Blocked channel? (config/movie_sources.json)
    → Default: UNVERIFIED
    ↓
Return MatchedMovie with confidence and rights status
    ↓
[UI Thread] MoviesPage displays movie cards
    → Playable badge (VERIFIED + STRONG match)
    → Unverified badge (UNVERIFIED)
    → Unavailable badge (BLOCKED or REJECTED)
    → Play button enabled only for VERIFIED sources
```

### Movie Playback Flow

```
User clicks "Play Movie" on verified source
    ↓
MoviesPage navigates to MoviePlayer
    ↓
MoviePlayer.__init__()
    ↓
[Background Thread] MoviePlaybackService.play_movie(matched_movie, hwnd)
    ↓
YtDlpClient.resolve_video(video_id)
    → Extract best[ext=mp4]/best format
    → Returns stream URL + user agent
    ↓
VlcPlayer.load(url, user_agent)
VlcPlayer.set_window(hwnd)  [Windows: set_hwnd]
VlcPlayer.play()
    ↓
[VLC Events] → [Event Queue]
    → on_end(generation)
    → on_error(generation)
    ↓
[UI Thread via subscribe()] MoviePlayer updates controls
    → Play/Pause button icon
    → Progress bar
    → Time labels
    → Volume indicator
```

### Source Rights Verification System

**Configuration:** `config/movie_sources.json`

```json
{
  "accept_creative_commons": false,
  "verified_channels": [
    {
      "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
      "name": "Official Channel Name",
      "reason": "Documented authorization from rights holder",
      "source_url": "https://example.com/proof"
    }
  ],
  "blocked_channels": [
    {
      "channel_id": "UCyyyyyyyyyyyyyyyyyyyy",
      "reason": "Known unauthorized uploader"
    }
  ],
  "public_domain": [
    {
      "tmdb_id": 10331,
      "youtube_id": "xxxxxxxxxxx",
      "reason": "Public domain - copyright expired",
      "source_url": "https://example.com/proof"
    }
  ]
}
```

**Verification Rules:**
1. Blocked channels → BLOCKED (never playable)
2. Verified channels → VERIFIED (playable if strong match)
3. Public domain (by TMDB ID) → VERIFIED (playable if strong match)
4. Creative Commons (if enabled) → VERIFIED (requires YouTube license check)
5. Everything else → UNVERIFIED (shows metadata, no VLC playback)

**Important:** The default configuration is empty. Users must manually add authorization records based on documented evidence.

### Movie Matching Algorithm

**Title Similarity:**
- Normalize both titles: lowercase, remove punctuation, remove common words (the, a, an, full, movie, film)
- Calculate word-based Jaccard similarity: `len(intersection) / len(union)`
- Special case: if one title is fully contained in the other → 0.9 similarity
- Threshold for match: >= 0.75

**Year Matching:**
- Extract 4-digit year from YouTube title
- Compare to TMDB release_year
- Allow ±1 year tolerance (accounts for different release dates by region)

**Duration Matching:**
- Compare YouTube duration (seconds) to TMDB runtime (minutes)
- Allow ±20% difference
- Zero TMDB runtime → skip duration check

**Confidence Levels:**
- **STRONG:** Title >= 75% + Year match + Duration match
- **POSSIBLE:** Title >= 75% + (Year match OR Duration match)
- **WEAK:** Title >= 50%
- **REJECTED:** Title < 50%

**Trailer/Clip Filtering:**
Rejects YouTube results with these keywords in title:
- trailer, teaser, clip, review, recap, reaction
- behind the scenes, interview, explained, ending explained
- deleted scene, bloopers, soundtrack, ost, theme song, commentary

### Music Playback Coexistence

When movie playback starts:
- `MoviePlayer.__init__()` checks `ctx.music_playback.state`
- If music is playing: `ctx.music_playback.toggle_pause()`
- Music queue and position preserved
- Toast notification: "Music paused"

When movie playback ends:
- VLC resources released via `MoviePlaybackService.release()`
- Music player remains functional (does not auto-resume)
- User can manually resume music from player bar

### Movie Page Routes

**Browse Movies:** `ctx.navigator.go(Route.MOVIES)`
- Shows MoviesPage with search, featured, popular, 2020s sections
- Default page parameter: `page="browse"`

**Play Movie:** `ctx.navigator.go(Route.MOVIES, matched_movie=obj, page="player")`
- Shows MoviePlayer with embedded VLC
- Requires MatchedMovie object with verified playable source

**Movie Details (Reserved):** `ctx.navigator.go(Route.MOVIES, matched_movie=obj, page="details")`
- Future implementation: full synopsis, cast, crew, recommendations

### Configuration Options

**Environment Variables:**
```bash
# Required for movie discovery
TMDB_API_KEY=your_api_key_or_read_access_token

# Optional: minimum duration for full-length movies (default 60 minutes)
MOVIE_MIN_DURATION_MINUTES=60
```

**Constants:**
- `MOVIE_FIRST_YEAR = 2000` - Oldest movies to discover
- `MOVIE_LAST_YEAR = 2026` - Newest movies to discover
- `SETTING_MOVIE_VOLUME = "default_movie_volume"` - User setting key (future)
- `MOVIE_POSITION_KEY_PREFIX = "movie_position:"` - Playback position saving (future)

### Known Limitations (Phase 5)

1. **Windows-Only Video:** VLC window embedding uses `set_hwnd()` (Windows). Linux needs `set_xwindow()`, macOS needs `set_nsobject()`.
2. **Stream Expiration:** YouTube direct URLs expire. Streams are resolved on-demand when user presses Play (not cached).
3. **No Automatic Catalog:** Requires TMDB search or category discovery first, then attempts YouTube matching. Does not pre-build a full catalog.
4. **Performance:** YouTube matching is network-intensive. Each movie requires separate yt-dlp search.
5. **Empty Authorization:** Default `movie_sources.json` is empty. No movies are playable until user adds verified sources.
6. **No Subtitle Support:** Current VLC integration does not handle subtitles or closed captions.
7. **No Quality Selection:** Uses best available format without user preference UI.
8. **No Resume Playback:** Movie position is not saved. Users restart from beginning.
9. **No Details Page:** Movie details view is reserved for future implementation.
10. **No Recommendations:** No "Similar Movies" or "Because you watched" features yet.



## Configuration

### Environment Variables (.env)

```
# Required for TMDB features
TMDB_API_KEY=your_api_key_or_read_access_token

# Required for Games features (Phase 6)
RAWG_API_KEY=your_api_key
```

### Local Settings (storage/local_settings.json)

```json
{
  "remember_me": {
    "enabled": true,
    "username": "saved_username"
  }
}
```

## Error Handling

Custom exceptions in `core/exceptions.py`:

- **KinetixError** - Base exception
- **ValidationError** - Input validation failures
- **AuthenticationError** - Login/registration failures
- **ApiError** - External API failures
- **MissingApiKeyError** - Missing configuration
- **MediaSourceError** - Media stream resolution failures
- **PlaybackError** - VLC playback failures

All services raise these typed exceptions. UI layer catches and displays user-friendly messages.

## Background Processing

`utils/helpers.py` provides `run_in_background()`:
- Runs work function in background thread
- Calls done callback on Tkinter main thread
- Passes result or error
- Safe for all UI updates

**Usage pattern:**
```python
def work():
    return service.fetch_data()

def done(result, error):
    if error:
        show_error(error)
    else:
        show_data(result)

run_in_background(widget, work, done)
```

## Logging

`utils/logger.py` provides configured logger:
- Console output with timestamps
- Module-specific loggers
- INFO level default
- Used throughout backend for debugging

## Security

- Passwords hashed with bcrypt (cost factor 12)
- Session tokens: SHA-256 of username + timestamp
- No API keys hardcoded (environment variables only)
- Input validation before database operations
- SQL injection prevented via parameterized queries

## Testing Strategy

**Current:** Manual testing during development

**Future considerations:**
- Unit tests for services (business logic)
- Integration tests for repositories (database)
- Mock external API clients for tests
- VLC player mock for playback tests

## Dependencies

See `requirements.txt`:
- **customtkinter** - Modern UI framework
- **Pillow** - Image processing
- **requests** - HTTP client
- **python-dotenv** - Environment variables
- **yt-dlp** - Audio stream extraction
- **python-vlc** - VLC media player bindings

## Future Extensions

### Movies Service (Phase 5)
- Full movie search and playback
- Video player integration
- yt-dlp + VLC for video streaming
- Movie details page

### Games Service (Phase 6)
- RAWG API integration
- Game search and details
- Similar architecture to Movies

### Favorites & History Pages
- Dedicated pages for user library
- Filtering and sorting
- Delete from history

### Settings Page
- User preferences UI
- Playback defaults
- API key management
- Theme customization

### Account Page
- Profile editing
- Password change
- Account deletion
- Usage statistics
