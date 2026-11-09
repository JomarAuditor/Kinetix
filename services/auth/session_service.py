"""Keeps the signed-in user in app state. Remember-me stores the username only."""
import json
from typing import Optional

from app.state import AppState
from config import settings
from models.user import User
from utils.logger import get_logger

logger = get_logger("session")
_REMEMBERED_KEY = "remembered_username"


class SessionService:
    def __init__(self, app_state: AppState):
        self._state = app_state

    @property
    def current_user(self) -> Optional[User]:
        return self._state.current_user

    @property
    def is_authenticated(self) -> bool:
        return self._state.current_user is not None

    def start(self, user: User) -> None:
        self._state.current_user = user

    def update_user(self, user: User) -> None:
        """Call after the profile changes so the top bar and pages stay in sync."""
        self._state.current_user = user

    def end(self) -> None:
        self._state.current_user = None

    # ---- Remember me (username only, never the password) ----
    def remember_username(self, username: Optional[str]) -> None:
        data = self._read_file()
        if username:
            data[_REMEMBERED_KEY] = username
        else:
            data.pop(_REMEMBERED_KEY, None)
        self._write_file(data)

    def remembered_username(self) -> str:
        return str(self._read_file().get(_REMEMBERED_KEY, ""))

    def _read_file(self) -> dict:
        try:
            with open(settings.LOCAL_SETTINGS_PATH, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_file(self, data: dict) -> None:
        try:
            settings.ensure_storage_dirs()
            with open(settings.LOCAL_SETTINGS_PATH, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError as exc:
            logger.warning("Could not save local settings: %s", exc)
