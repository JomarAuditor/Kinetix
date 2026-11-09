"""Password hashing with PBKDF2-HMAC-SHA256 and a unique random salt per user."""
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from config.constants import PBKDF2_ITERATIONS, SALT_BYTES


@dataclass(frozen=True)
class PasswordHash:
    hash_hex: str
    salt_hex: str
    iterations: int


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> PasswordHash:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, PBKDF2_ITERATIONS)
    return PasswordHash(digest.hex(), salt.hex(), PBKDF2_ITERATIONS)


def verify_password(password: str, hash_hex: str, salt_hex: str, iterations: int) -> bool:
    """Compare in constant time. Uses the iteration count stored with the hash."""
    expected = bytes.fromhex(hash_hex)
    actual = _derive(password, bytes.fromhex(salt_hex), iterations)
    return hmac.compare_digest(actual, expected)
