"""Word puzzle API client using Datamuse (words + definitions) and Dictionary API."""
import random
from typing import List

from core.exceptions import ApiError
from integrations.api.base_client import BaseClient
from models.game import WordPuzzle


class WordApiClient(BaseClient):
    """Fetches real English words and definitions for Word Guess and Word Scramble."""

    def __init__(self) -> None:
        super().__init__("https://api.datamuse.com")

    def fetch_word_puzzle(self, length: int = 5) -> WordPuzzle:
        pattern = "?" * max(4, min(length, 8))
        data = self.get_json("words", {"sp": pattern, "md": "df", "max": 100})
        if not isinstance(data, list) or not data:
            raise ApiError("Word service returned no words.")

        candidates: List[WordPuzzle] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            word = str(row.get("word") or "").strip().lower()
            if len(word) != length or not word.isalpha():
                continue
            defs = row.get("defs") if isinstance(row.get("defs"), list) else []
            if not defs:
                continue
            # Datamuse defs look like "n\tA short explanation"
            raw_def = str(defs[0])
            parts = raw_def.split("\t", 1)
            pos = parts[0].strip() if len(parts) == 2 else ""
            definition = parts[-1].strip()
            if not definition:
                continue
            candidates.append(WordPuzzle(word=word.upper(), definition=definition, part_of_speech=pos))

        if not candidates:
            raise ApiError("Could not find a valid word puzzle right now.")
        return random.choice(candidates)
