"""RAWG Video Games Database API client for searching latest and popular games."""
import html
import re
from typing import Any, Dict, List, Optional

from config import settings
from core.exceptions import MissingApiKeyError
from integrations.api.base_client import BaseClient

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    text = _TAG_RE.sub("", raw or "")
    return html.unescape(text).strip()


class RawgClient(BaseClient):
    """Client for https://api.rawg.io/api (metadata & search; games are not playable in-app)."""

    def __init__(self) -> None:
        super().__init__("https://api.rawg.io/api", timeout=(5, 10))

    @staticmethod
    def has_api_key() -> bool:
        return bool(settings.get_rawg_api_key())

    @staticmethod
    def _require_key() -> str:
        key = settings.get_rawg_api_key()
        if not key:
            raise MissingApiKeyError("RAWG_API_KEY is not set in .env.")
        return key

    def search_games(self, query: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Search RAWG for games matching *query*."""
        key = self._require_key()
        data = self.get_json(
            "games",
            params={
                "key": key,
                "search": query.strip(),
                "page_size": max(1, min(20, limit)),
                "search_precise": "true",
            },
        )
        results = data.get("results") or []
        return [self._normalize_summary(item) for item in results if item.get("id") and item.get("name")]

    def get_game_details(self, rawg_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full details (including description) for a single RAWG game."""
        key = self._require_key()
        data = self.get_json(f"games/{rawg_id}", params={"key": key})
        if not isinstance(data, dict) or not data.get("id"):
            return None
        summary = self._normalize_summary(data)
        desc = (data.get("description_raw") or _clean_text(data.get("description") or "")).strip()
        devs = ", ".join(d.get("name", "") for d in (data.get("developers") or []) if d.get("name"))
        summary["description"] = desc
        summary["developers"] = devs
        return summary

    @staticmethod
    def _normalize_summary(item: Dict[str, Any]) -> Dict[str, Any]:
        genres = [g.get("name", "") for g in (item.get("genres") or []) if g.get("name")]
        platforms = [
            p["platform"]["name"]
            for p in (item.get("platforms") or [])
            if isinstance(p, dict) and isinstance(p.get("platform"), dict) and p["platform"].get("name")
        ]
        return {
            "id": int(item["id"]),
            "name": str(item.get("name") or ""),
            "released": str(item.get("released") or ""),
            "rating": float(item.get("rating") or 0.0),
            "metacritic": item.get("metacritic"),
            "image_url": str(item.get("background_image") or ""),
            "genres": ", ".join(genres[:4]),
            "category": genres[0] if genres else "Game",
            "platforms": ", ".join(platforms[:5]),
            "description": "",
            "developers": "",
        }
