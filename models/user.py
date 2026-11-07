"""User models. `User` is safe to show; `StoredUser` also holds the hash data."""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    full_name: str
    username: str
    email: str
    created_at: str = ""

    @property
    def first_name(self) -> str:
        parts = self.full_name.strip().split()
        return parts[0] if parts else self.username

    @property
    def initials(self) -> str:
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return (self.full_name.strip() or self.username)[:2].upper()


@dataclass
class StoredUser:
    user: User
    password_hash: str
    salt: str
    iterations: int
