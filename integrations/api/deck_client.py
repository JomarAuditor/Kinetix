"""Deck of Cards API client (https://deckofcardsapi.com) — free, no API key required."""
from typing import List, Tuple

from core.exceptions import ApiError
from integrations.api.base_client import BaseClient
from models.game import PlayingCard


class DeckOfCardsClient(BaseClient):
    """Shuffles virtual decks and draws cards with real card artwork PNGs."""

    def __init__(self) -> None:
        super().__init__("https://deckofcardsapi.com/api")

    def new_deck(self, deck_count: int = 1) -> str:
        data = self.get_json("deck/new/shuffle/", {"deck_count": max(1, min(deck_count, 6))})
        if not isinstance(data, dict) or not data.get("success") or not data.get("deck_id"):
            raise ApiError("Could not shuffle a new card deck.")
        return str(data["deck_id"])

    def draw_cards(self, deck_id: str, count: int = 2) -> Tuple[List[PlayingCard], int]:
        data = self.get_json(f"deck/{deck_id}/draw/", {"count": max(1, min(count, 10))})
        if not isinstance(data, dict) or not data.get("success"):
            raise ApiError("Could not draw cards from the deck.")
        raw_cards = data.get("cards") or []
        cards: List[PlayingCard] = []
        for row in raw_cards:
            if not isinstance(row, dict):
                continue
            cards.append(PlayingCard(
                code=str(row.get("code") or ""),
                value=str(row.get("value") or "").upper(),
                suit=str(row.get("suit") or "").upper(),
                image_url=str(row.get("image") or ""),
            ))
        remaining = int(data.get("remaining") or 0)
        return cards, remaining
