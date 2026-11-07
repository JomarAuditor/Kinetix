"""Game models for in-app playable API games (Open Trivia DB, Deck of Cards, Word API)."""
from dataclasses import dataclass, field
from typing import List, Optional

from config.constants import MEDIA_GAME
from models.media import MediaItem


@dataclass(frozen=True)
class GameItem:
    """A playable game or quiz mode inside Kinetix, or a RAWG catalog entry."""
    game_id: str
    title: str
    category: str       # "Arcade", "Trivia", "Cards", "Words", or genre for RAWG
    kind: str           # "trivia", "blackjack", "highlow", "word_guess", "word_scramble", "rawg", etc.
    api_source: str
    description: str
    image_url: str = ""
    category_id: Optional[int] = None
    playable: bool = True
    released: str = ""
    rating: float = 0.0
    metacritic: Optional[int] = None
    platforms: str = ""
    genres: str = ""
    developers: str = ""

    @property
    def subtitle(self) -> str:
        return f"{self.category} \u2022 {self.api_source}"

    def to_media_item(self) -> MediaItem:
        return MediaItem(
            media_type=MEDIA_GAME,
            external_id=self.game_id,
            title=self.title,
            subtitle=self.subtitle,
            image_url=self.image_url,
        )


@dataclass(frozen=True)
class TriviaQuestion:
    question: str
    correct_answer: str
    choices: List[str] = field(default_factory=list)
    category: str = ""
    difficulty: str = "medium"


@dataclass(frozen=True)
class PlayingCard:
    code: str
    value: str
    suit: str
    image_url: str

    @property
    def rank_number(self) -> int:
        mapping = {"ACE": 14, "KING": 13, "QUEEN": 12, "JACK": 11}
        if self.value in mapping:
            return mapping[self.value]
        try:
            return int(self.value)
        except ValueError:
            return 0

    @property
    def blackjack_value(self) -> int:
        if self.value == "ACE":
            return 11
        if self.value in ("KING", "QUEEN", "JACK"):
            return 10
        try:
            return int(self.value)
        except ValueError:
            return 0


@dataclass(frozen=True)
class WordPuzzle:
    word: str
    definition: str
    part_of_speech: str = ""
