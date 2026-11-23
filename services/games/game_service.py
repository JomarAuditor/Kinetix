"""Playable Games service backed by Open Trivia DB, Deck of Cards API, and Datamuse Word API."""
import threading
import time
from typing import Dict, List, Optional, Tuple

from config.constants import MEDIA_GAME
from core.exceptions import ApiError, MissingApiKeyError
from integrations.api.deck_client import DeckOfCardsClient
from integrations.api.opentdb_client import OpenTdbClient
from integrations.api.rawg_client import RawgClient
from integrations.api.word_api_client import WordApiClient
from models.game import GameItem, PlayingCard, TriviaQuestion, WordPuzzle
from models.media import MediaItem
from utils.game_art import ensure_all, game_image_path
from utils.logger import get_logger

logger = get_logger("game_service")


def _img(game_id: str, title: str = "", category_id: int = 0) -> str:
    """Return local game art path, generated on first call."""
    return game_image_path(game_id, title, category_id)


_ARCADE_GAMES: Tuple[GameItem, ...] = (
    GameItem(
        game_id="arcade:snake",
        title="Neon Snake",
        category="Arcade",
        kind="snake",
        api_source="Built-in",
        description="Classic snake: eat food, grow longer, don't bite yourself or the walls.",
        image_url=_img("arcade:snake"),
    ),
    GameItem(
        game_id="arcade:pong",
        title="Pong Duel",
        category="Arcade",
        kind="pong",
        api_source="Built-in",
        description="Classic two-paddle Pong. Use the keyboard to beat the AI before it beats you.",
        image_url=_img("arcade:pong"),
    ),
    GameItem(
        game_id="arcade:breakout",
        title="Brick Breaker",
        category="Arcade",
        kind="breakout",
        api_source="Built-in",
        description="Break every brick with the bouncing ball. Speed increases with each level.",
        image_url=_img("arcade:breakout"),
    ),
    GameItem(
        game_id="arcade:flappy",
        title="Flappy Rocket",
        category="Arcade",
        kind="flappy",
        api_source="Built-in",
        description="Tap to thrust. Squeeze your rocket through columns of asteroids.",
        image_url=_img("arcade:flappy"),
    ),
    GameItem(
        game_id="arcade:tictactoe",
        title="Tic-Tac-Toe",
        category="Arcade",
        kind="tictactoe",
        api_source="Built-in",
        description="Classic 3x3 Tic-Tac-Toe against the computer with smart AI.",
        image_url=_img("arcade:tictactoe"),
    ),
)

_CORE_GAMES: Tuple[GameItem, ...] = (
    GameItem(
        game_id="cards:blackjack",
        title="Blackjack 21",
        category="Cards",
        kind="blackjack",
        api_source="Deck of Cards API",
        description="Beat the dealer to 21 using live shuffled decks and card artwork.",
        image_url=_img("cards:blackjack"),
    ),
    GameItem(
        game_id="cards:highlow",
        title="High-Low Cards",
        category="Cards",
        kind="highlow",
        api_source="Deck of Cards API",
        description="Predict whether the next card drawn from the deck is higher or lower.",
        image_url=_img("cards:highlow"),
    ),
    GameItem(
        game_id="word:guess5",
        title="5-Letter Word Guess",
        category="Words",
        kind="word_guess",
        api_source="Datamuse Word API",
        description="Crack the secret 5-letter word in 6 tries using live dictionary clues.",
        image_url=_img("word:guess5"),
    ),
    GameItem(
        game_id="word:scramble",
        title="Word Scramble",
        category="Words",
        kind="word_scramble",
        api_source="Datamuse Word API",
        description="Unscramble words from their dictionary definitions to build your streak.",
        image_url=_img("word:scramble"),
    ),
)

_DEFAULT_TRIVIA: Tuple[GameItem, ...] = (
    GameItem(
        game_id="trivia:15",
        title="Video Games Trivia",
        category="Trivia",
        kind="trivia",
        api_source="Open Trivia DB",
        description="Test your gaming knowledge with live 10-question rounds.",
        category_id=15,
        image_url=_img("trivia:15", "Video Games Trivia", 15),
    ),
    GameItem(
        game_id="trivia:18",
        title="Computers & Tech Trivia",
        category="Trivia",
        kind="trivia",
        api_source="Open Trivia DB",
        description="Programming, hardware, and computing trivia powered by OpenTDB.",
        category_id=18,
        image_url=_img("trivia:18", "Computers & Tech", 18),
    ),
    GameItem(
        game_id="trivia:11",
        title="Movies & Film Trivia",
        category="Trivia",
        kind="trivia",
        api_source="Open Trivia DB",
        description="Cinema classics, directors, and box office trivia questions.",
        category_id=11,
        image_url=_img("trivia:11", "Movies & Film", 11),
    ),
    GameItem(
        game_id="trivia:12",
        title="Music Trivia",
        category="Trivia",
        kind="trivia",
        api_source="Open Trivia DB",
        description="Artists, albums, and music history challenges.",
        category_id=12,
        image_url=_img("trivia:12", "Music Trivia", 12),
    ),
)


class GameService:
    """Provides playable in-app games backed by free public REST APIs (no API keys)."""

    def __init__(
        self,
        trivia: Optional[OpenTdbClient] = None,
        deck: Optional[DeckOfCardsClient] = None,
        words: Optional[WordApiClient] = None,
        rawg: Optional[RawgClient] = None,
    ) -> None:
        self._trivia = trivia or OpenTdbClient()
        self._deck = deck or DeckOfCardsClient()
        self._words = words or WordApiClient()
        self._rawg = rawg or RawgClient()
        self._lock = threading.Lock()
        self._cached_catalog: Optional[List[GameItem]] = None
        self._rawg_search_cache: Dict[str, Tuple[float, List[GameItem]]] = {}
        self._rawg_details_cache: Dict[int, Tuple[float, GameItem]] = {}
        # Pre-generate game art in the background on first use
        try:
            ensure_all()
        except Exception:
            pass

    @property
    def is_catalog_cached(self) -> bool:
        return self._cached_catalog is not None

    # ------------------------------------------------------------------
    # Catalog & Discovery
    # ------------------------------------------------------------------

    def featured(self, limit: int = 5) -> List[MediaItem]:
        """Return featured playable games for the Dashboard."""
        return [g.to_media_item() for g in self.featured_games(limit)]

    def featured_games(self, limit: int = 4) -> List[GameItem]:
        picks = [
            _ARCADE_GAMES[0],      # Neon Snake
            _CORE_GAMES[0],        # Blackjack 21
            _DEFAULT_TRIVIA[0],    # Video Games Trivia
            _CORE_GAMES[2],        # 5-Letter Word Guess
        ]
        return picks[:limit]

    def discover_games(self, category: str = "all") -> List[GameItem]:
        catalog = self._load_catalog()
        if category.lower() == "all":
            return catalog
        wanted = category.lower()
        return [g for g in catalog if g.category.lower() == wanted]

    def search(self, query: str) -> List[GameItem]:
        q = query.strip().lower()
        if not q:
            return self.discover_games()
        catalog = self._load_catalog()
        local_hits = [
            g for g in catalog
            if q in g.title.lower() or q in g.category.lower() or q in g.description.lower()
        ]
        rawg_hits: List[GameItem] = []
        if self._rawg.has_api_key():
            rawg_key = query.strip().lower()
            with self._lock:
                cached = self._rawg_search_cache.get(rawg_key)
                if cached and time.monotonic() - cached[0] < 300:
                    rawg_hits = list(cached[1])
                    cached_hit = True
                else:
                    cached_hit = False
            if not cached_hit:
                try:
                    for row in self._rawg.search_games(query.strip(), limit=12):
                        rawg_hits.append(self._rawg_dict_to_item(row))
                    with self._lock:
                        self._rawg_search_cache[rawg_key] = (time.monotonic(), list(rawg_hits))
                except (ApiError, MissingApiKeyError) as exc:
                    logger.warning("RAWG search failed: %s", exc)
        return local_hits + rawg_hits

    def get_game(self, game_id: str) -> Optional[GameItem]:
        if game_id.startswith("rawg:"):
            try:
                rawg_id = int(game_id.split(":", 1)[1])
            except ValueError:
                return None
            return self.get_rawg_details(rawg_id)
        for g in self._load_catalog():
            if g.game_id == game_id:
                return g
        return None

    def get_rawg_details(self, rawg_id: int) -> Optional[GameItem]:
        with self._lock:
            cached = self._rawg_details_cache.get(rawg_id)
            if cached and time.monotonic() - cached[0] < 300:
                return cached[1]
        try:
            row = self._rawg.get_game_details(rawg_id)
        except (ApiError, MissingApiKeyError) as exc:
            logger.warning("RAWG details failed for %s: %s", rawg_id, exc)
            return None
        if not row:
            return None
        item = self._rawg_dict_to_item(row)
        with self._lock:
            self._rawg_details_cache[rawg_id] = (time.monotonic(), item)
        return item

    @staticmethod
    def _rawg_dict_to_item(row: dict) -> GameItem:
        return GameItem(
            game_id=f"rawg:{row['id']}",
            title=row["name"],
            category=row.get("category") or "Game",
            kind="rawg",
            api_source="RAWG.io",
            description=row.get("description") or "",
            image_url=row.get("image_url") or "",
            playable=False,
            released=row.get("released") or "",
            rating=float(row.get("rating") or 0.0),
            metacritic=row.get("metacritic"),
            platforms=row.get("platforms") or "",
            genres=row.get("genres") or "",
            developers=row.get("developers") or "",
        )

    def _load_catalog(self) -> List[GameItem]:
        if self._cached_catalog is not None:
            return self._cached_catalog

        trivia_items: List[GameItem] = []
        try:
            categories = self._trivia.fetch_categories()
            # Put popular geek/entertainment categories first
            priority = {15: 0, 18: 1, 11: 2, 12: 3, 31: 4, 17: 5, 9: 6}
            categories.sort(key=lambda c: (priority.get(c["id"], 99), c["name"]))
            for cat in categories:
                cat_id = cat["id"]
                cat_name = cat["name"]
                trivia_items.append(GameItem(
                    game_id=f"trivia:{cat_id}",
                    title=f"{cat_name} Trivia",
                    category="Trivia",
                    kind="trivia",
                    api_source="Open Trivia DB",
                    description=f"Play a 10-question {cat_name} quiz live from Open Trivia DB.",
                    category_id=cat_id,
                    image_url=_img(f"trivia:{cat_id}", cat_name, cat_id),
                ))
        except ApiError as exc:
            logger.warning("Could not fetch OpenTDB categories, using defaults: %s", exc)
            trivia_items = list(_DEFAULT_TRIVIA)

        # Arcade first, then card/word games, then trivia
        catalog = list(_ARCADE_GAMES) + list(_CORE_GAMES) + trivia_items
        self._cached_catalog = catalog
        return catalog

    # ------------------------------------------------------------------
    # Live Gameplay APIs
    # ------------------------------------------------------------------

    def load_trivia_round(
        self,
        category_id: Optional[int],
        difficulty: str = "medium",
        amount: int = 10,
    ) -> List[TriviaQuestion]:
        return self._trivia.fetch_questions(category_id=category_id, difficulty=difficulty, amount=amount)

    def new_deck(self, deck_count: int = 1) -> str:
        return self._deck.new_deck(deck_count=deck_count)

    def draw_cards(self, deck_id: str, count: int = 2) -> Tuple[List[PlayingCard], int]:
        return self._deck.draw_cards(deck_id, count=count)

    def load_word_puzzle(self, length: int = 5) -> WordPuzzle:
        return self._words.fetch_word_puzzle(length=length)
