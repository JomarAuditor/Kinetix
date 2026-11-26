"""Shared HTTP helper for the API clients: timeouts, clear errors, JSON validation."""
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

from config.constants import USER_AGENT
from core.exceptions import ApiError
from utils.logger import get_logger

logger = get_logger("api")


class BaseClient:
    """Subclass this and call get_json(). Every failure becomes an ApiError with a short message."""

    def __init__(self, base_url: str, timeout: Tuple[float, float] = (5, 12)):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            with self._session.get(url, params=params, headers=headers, timeout=self._timeout) as response:
                return self._read(response)
        except requests.Timeout as exc:
            raise ApiError("The service took too long to answer.") from exc
        except requests.RequestException as exc:
            logger.warning("Request failed for %s: %s", self._base_url, type(exc).__name__)
            raise ApiError("Could not reach the service. Check your connection.") from exc

    @staticmethod
    def _read(response: requests.Response) -> Any:
        if response.status_code == 404:
            raise ApiError("Not found.")
        if response.status_code in (401, 403):
            raise ApiError("The service refused the request (check the API key).")
        if response.status_code == 429:
            raise ApiError("Too many requests. Please wait a moment.")
        if response.status_code != 200:
            raise ApiError(f"The service returned an error ({response.status_code}).")
        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError("The service sent an unreadable answer.") from exc
        if not isinstance(data, (dict, list)):
            raise ApiError("The service sent an unexpected answer.")
        return data
