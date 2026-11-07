"""Input validation. Each function returns an error message, or "" if valid."""
import re
from typing import Dict

from config.constants import (
    FULL_NAME_MAX, FULL_NAME_MIN, PASSWORD_MIN, USERNAME_MAX, USERNAME_MIN,
)

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

REQUIRED_MESSAGE = "This field is required."


def validate_full_name(value: str) -> str:
    value = value.strip()
    if not value:
        return REQUIRED_MESSAGE
    if not FULL_NAME_MIN <= len(value) <= FULL_NAME_MAX:
        return f"Full name must be {FULL_NAME_MIN}-{FULL_NAME_MAX} characters."
    return ""


def validate_email(value: str) -> str:
    value = value.strip()
    if not value:
        return REQUIRED_MESSAGE
    if not _EMAIL_PATTERN.match(value):
        return "Enter a valid email address."
    return ""


def validate_username(value: str) -> str:
    value = value.strip()
    if not value:
        return REQUIRED_MESSAGE
    if not USERNAME_MIN <= len(value) <= USERNAME_MAX:
        return f"Username must be {USERNAME_MIN}-{USERNAME_MAX} characters."
    if not _USERNAME_PATTERN.match(value):
        return "Use only letters, numbers and underscore."
    return ""


def validate_password(value: str) -> str:
    if not value:
        return REQUIRED_MESSAGE
    if len(value) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        return "Password needs at least one letter and one number."
    return ""


def validate_password_match(password: str, confirm: str) -> str:
    if not confirm:
        return REQUIRED_MESSAGE
    if password != confirm:
        return "Passwords do not match."
    return ""


def collect_registration_errors(
    full_name: str, email: str, username: str, password: str, confirm: str
) -> Dict[str, str]:
    checks = {
        "full_name": validate_full_name(full_name),
        "email": validate_email(email),
        "username": validate_username(username),
        "password": validate_password(password),
        "confirm": validate_password_match(password, confirm),
    }
    return {field: message for field, message in checks.items() if message}


def collect_profile_errors(full_name: str, username: str, email: str) -> Dict[str, str]:
    checks = {
        "full_name": validate_full_name(full_name),
        "username": validate_username(username),
        "email": validate_email(email),
    }
    return {field: message for field, message in checks.items() if message}
