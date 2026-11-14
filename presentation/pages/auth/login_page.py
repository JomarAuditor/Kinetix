"""Login page: username or email + password, remember me (username only)."""
import customtkinter as ctk

from app.navigation import Route
from core.exceptions import AuthenticationError, ValidationError
from core.validators import REQUIRED_MESSAGE
from presentation.components.buttons import PrimaryButton
from presentation.components.inputs import TextField
from presentation.pages.auth.auth_components import AuthPage, InlineBanner, build_switch_row
from presentation.styles import widgets
from presentation.styles.colors import Spacing
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("login_page")
_GENERIC_ERROR = "Something went wrong. Please try again."


class LoginPage(AuthPage):
    def __init__(self, parent, ctx, prefill_username: str = ""):
        super().__init__(parent, "Welcome back", "Music, movies and games in one place.")
        self.ctx = ctx
        body = self.body

        self.identifier = TextField(body, "Username or email", on_submit=self._submit)
        self.identifier.pack(fill="x", pady=(0, Spacing.LG))
        self.password = TextField(body, "Password", password=True, on_submit=self._submit)
        self.password.pack(fill="x", pady=(0, Spacing.MD))

        self.remember = ctk.CTkCheckBox(body, text="Remember me", **widgets.checkbox())
        self.remember.pack(anchor="w", pady=(0, Spacing.LG))

        self.submit_button = PrimaryButton(body, "Sign In", self._submit)
        self.submit_button.pack(fill="x")
        self.banner = InlineBanner(body, before=self.submit_button)
        build_switch_row(body, "Don't have an account?", "Create Account",
                         lambda: ctx.navigator.go(Route.SIGNUP))

        for field in (self.identifier, self.password):
            field.entry.bind("<Key>", lambda _e: self._clear_errors(), add="+")
        self._prefill(prefill_username)

    def _prefill(self, prefill_username: str) -> None:
        remembered = self.ctx.session_service.remembered_username()
        name = prefill_username or remembered
        if name:
            self.identifier.set(name)
            self.password.focus()
        else:
            self.identifier.focus()
        if remembered:
            self.remember.select()

    def _clear_errors(self) -> None:
        self.identifier.clear_error()
        self.password.clear_error()
        self.banner.hide()

    def _submit(self) -> None:
        if self.submit_button.is_loading:
            return
        self._clear_errors()
        identifier, password = self.identifier.get(), self.password.get()
        missing = False
        if not identifier.strip():
            self.identifier.set_error(REQUIRED_MESSAGE)
            missing = True
        if not password:
            self.password.set_error(REQUIRED_MESSAGE)
            missing = True
        if missing:
            return

        self.submit_button.set_loading(True, "Signing in...")
        auth = self.ctx.auth_service
        run_in_background(self, lambda: auth.login(identifier, password), self._on_login_done)

    def _on_login_done(self, user, error) -> None:
        self.submit_button.set_loading(False)
        if error is None:
            self._finish_login(user)
        elif isinstance(error, ValidationError):
            self._show_field_errors(error.errors)
        elif isinstance(error, AuthenticationError):
            self.banner.show(str(error))
        else:
            logger.error("Login failed unexpectedly: %s", type(error).__name__)
            self.banner.show(_GENERIC_ERROR)

    def _show_field_errors(self, errors: dict) -> None:
        if "identifier" in errors:
            self.identifier.set_error(errors["identifier"])
        if "password" in errors:
            self.password.set_error(errors["password"])

    def _finish_login(self, user) -> None:
        session = self.ctx.session_service
        session.start(user)
        session.remember_username(user.username if self.remember.get() else None)
        self.ctx.navigator.go(Route.HOME)
