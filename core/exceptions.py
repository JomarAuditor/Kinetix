"""Custom errors so the GUI can show clear messages."""
from typing import Dict


class KinetixError(Exception):
    """Base class for all Kinetix errors."""


class ValidationError(KinetixError):
    """Input is not valid. `errors` maps a field name to a message."""

    def __init__(self, errors: Dict[str, str]):
        self.errors = dict(errors)
        super().__init__("; ".join(self.errors.values()))


class AuthenticationError(KinetixError):
    """Wrong username/email or password."""


class DuplicateRecordError(KinetixError):
    """A UNIQUE rule was broken. `field` is 'username' or 'email'."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"{field} already exists")


class DatabaseError(KinetixError):
    """An unexpected SQLite problem."""


class ApiError(KinetixError):
    """An external API failed, timed out or returned bad data."""


class MissingApiKeyError(ApiError):
    """A required API key is not set in .env."""


class MediaSourceError(KinetixError):
    """yt-dlp could not find or extract a playable source."""


class PlaybackError(KinetixError):
    """VLC is missing or could not play the media."""
