"""Open Trivia Database API client (https://opentdb.com) — free, no API key required."""
import html
import random
from typing import Dict, List, Optional

from core.exceptions import ApiError
from integrations.api.base_client import BaseClient
from models.game import TriviaQuestion


class OpenTdbClient(BaseClient):
    """Fetches trivia categories and multiple-choice questions."""

    def __init__(self) -> None:
        super().__init__("https://opentdb.com")

    def fetch_categories(self) -> List[Dict]:
        data = self.get_json("api_category.php")
        raw = data.get("trivia_categories") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            raise ApiError("Trivia service sent an unexpected category list.")
        categories = []
        for entry in raw:
            if isinstance(entry, dict) and entry.get("id") and isinstance(entry.get("name"), str):
                name = html.unescape(entry["name"]).strip()
                # Clean long prefixes like "Entertainment: Video Games"
                short = name.split(": ", 1)[-1] if ": " in name else name
                categories.append({"id": int(entry["id"]), "name": short, "full_name": name})
        return categories

    def fetch_questions(
        self,
        category_id: Optional[int] = None,
        difficulty: str = "medium",
        amount: int = 10,
    ) -> List[TriviaQuestion]:
        params: Dict[str, object] = {"amount": max(1, min(amount, 20)), "type": "multiple"}
        if category_id is not None:
            params["category"] = category_id
        if difficulty in ("easy", "medium", "hard"):
            params["difficulty"] = difficulty

        data = self.get_json("api.php", params)
        if not isinstance(data, dict):
            raise ApiError("Trivia service sent an unexpected response.")

        code = data.get("response_code")
        if code == 1 and difficulty:
            # Not enough questions at that difficulty — retry without difficulty filter
            params.pop("difficulty", None)
            data = self.get_json("api.php", params)
            code = data.get("response_code") if isinstance(data, dict) else None

        if code == 5:
            raise ApiError("Trivia API rate limit reached. Wait 5 seconds and try again.")
        if code != 0:
            raise ApiError("No trivia questions available for this mode right now.")

        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list) or not results:
            raise ApiError("Trivia service returned no questions.")

        questions: List[TriviaQuestion] = []
        for row in results:
            if not isinstance(row, dict):
                continue
            q_text = html.unescape(str(row.get("question") or "")).strip()
            correct = html.unescape(str(row.get("correct_answer") or "")).strip()
            incorrect = [html.unescape(str(x)).strip() for x in (row.get("incorrect_answers") or []) if x]
            if not q_text or not correct or not incorrect:
                continue
            choices = incorrect + [correct]
            random.shuffle(choices)
            questions.append(TriviaQuestion(
                question=q_text,
                correct_answer=correct,
                choices=choices,
                category=html.unescape(str(row.get("category") or "")),
                difficulty=str(row.get("difficulty") or difficulty),
            ))
        return questions
