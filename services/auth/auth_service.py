"""Registration, login, profile edits and password changes."""
from core.exceptions import (
    AuthenticationError, DuplicateRecordError, ValidationError,
)
from core.validators import (
    REQUIRED_MESSAGE, collect_profile_errors, collect_registration_errors,
    validate_password, validate_password_match,
)
from data.repositories.user_repository import UserRepository
from models.user import User
from services.auth import password_service
from utils.logger import get_logger

logger = get_logger("auth")

LOGIN_FAILED_MESSAGE = "Incorrect username or password."
_DUMMY_HASH = password_service.hash_password("kinetix-dummy-password-1")


def _duplicate_message(field: str) -> str:
    return "Username is already taken." if field == "username" else "Email is already in use."


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self._users = user_repository

    def register(self, full_name: str, email: str, username: str,
                 password: str, confirm: str) -> User:
        errors = collect_registration_errors(full_name, email, username, password, confirm)
        if errors:
            raise ValidationError(errors)

        full_name, username, email = full_name.strip(), username.strip(), email.strip().lower()
        if self._users.username_exists(username):
            errors["username"] = _duplicate_message("username")
        if self._users.email_exists(email):
            errors["email"] = _duplicate_message("email")
        if errors:
            raise ValidationError(errors)

        hashed = password_service.hash_password(password)
        try:
            user = self._users.create_user(
                full_name, username, email,
                hashed.hash_hex, hashed.salt_hex, hashed.iterations,
            )
        except DuplicateRecordError as exc:  # another account was created at the same moment
            raise ValidationError({exc.field: _duplicate_message(exc.field)}) from exc
        logger.info("New account created (user id %s)", user.id)
        return user

    def login(self, identifier: str, password: str) -> User:
        errors = {}
        if not identifier.strip():
            errors["identifier"] = REQUIRED_MESSAGE
        if not password:
            errors["password"] = REQUIRED_MESSAGE
        if errors:
            raise ValidationError(errors)

        stored = self._users.get_stored_by_login(identifier.strip())
        if stored is None:
            # Hash anyway so a wrong username takes about as long as a wrong password.
            password_service.verify_password(
                password, _DUMMY_HASH.hash_hex, _DUMMY_HASH.salt_hex, _DUMMY_HASH.iterations
            )
            raise AuthenticationError(LOGIN_FAILED_MESSAGE)

        if not password_service.verify_password(
            password, stored.password_hash, stored.salt, stored.iterations
        ):
            raise AuthenticationError(LOGIN_FAILED_MESSAGE)
        logger.info("User %s signed in", stored.user.id)
        return stored.user

    def update_profile(self, user_id: int, full_name: str, username: str, email: str) -> User:
        errors = collect_profile_errors(full_name, username, email)
        if errors:
            raise ValidationError(errors)

        full_name, username, email = full_name.strip(), username.strip(), email.strip().lower()
        if self._users.username_exists(username, exclude_user_id=user_id):
            errors["username"] = _duplicate_message("username")
        if self._users.email_exists(email, exclude_user_id=user_id):
            errors["email"] = _duplicate_message("email")
        if errors:
            raise ValidationError(errors)

        try:
            return self._users.update_profile(user_id, full_name, username, email)
        except DuplicateRecordError as exc:
            raise ValidationError({exc.field: _duplicate_message(exc.field)}) from exc

    def change_password(self, user_id: int, old_password: str,
                        new_password: str, confirm: str) -> None:
        stored = self._users.get_stored_by_id(user_id)
        if stored is None:
            raise AuthenticationError("Account not found.")

        errors = {}
        if not old_password:
            errors["old_password"] = REQUIRED_MESSAGE
        elif not password_service.verify_password(
            old_password, stored.password_hash, stored.salt, stored.iterations
        ):
            errors["old_password"] = "Current password is incorrect."

        new_error = validate_password(new_password)
        if new_error:
            errors["new_password"] = new_error
        confirm_error = validate_password_match(new_password, confirm)
        if confirm_error:
            errors["confirm"] = confirm_error
        if errors:
            raise ValidationError(errors)

        hashed = password_service.hash_password(new_password)
        self._users.update_password(user_id, hashed.hash_hex, hashed.salt_hex, hashed.iterations)
        logger.info("Password changed for user %s", user_id)
