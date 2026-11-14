"""Sign Up page: full name, email, username, password, confirm password."""
from app.navigation import Route
from config.constants import PASSWORD_MIN
from core.exceptions import ValidationError
from core.validators import collect_registration_errors
from presentation.components.buttons import PrimaryButton
from presentation.components.dialogs import show_toast
from presentation.components.inputs import TextField
from presentation.pages.auth.auth_components import AuthPage, InlineBanner, build_switch_row
from presentation.styles.colors import Spacing
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("signup_page")
_GENERIC_ERROR = "Something went wrong. Please try again."


class SignUpPage(AuthPage):
    def __init__(self, parent, ctx):
        super().__init__(parent, "Create your account", "Join Kinetix to save favorites and track what you play.")
        self.ctx = ctx
        body = self.body
        gap = (0, Spacing.MD)

        self.fields = {
            "full_name": TextField(body, "Full name", on_submit=self._submit),
            "email": TextField(body, "Email", on_submit=self._submit),
            "username": TextField(body, "Username", on_submit=self._submit),
            "password": TextField(body, "Password", password=True, on_submit=self._submit,
                                  hint=f"At least {PASSWORD_MIN} characters, with a letter and a number."),
            "confirm": TextField(body, "Confirm password", password=True, on_submit=self._submit),
        }
        for field in self.fields.values():
            field.pack(fill="x", pady=gap)
            field.entry.bind("<Key>", lambda _e, f=field: self._on_typing(f), add="+")

        self.submit_button = PrimaryButton(body, "Create Account", self._submit)
        self.submit_button.pack(fill="x", pady=(Spacing.SM, 0))
        self.banner = InlineBanner(body, before=self.submit_button)
        build_switch_row(body, "Already have an account?", "Sign In",
                         lambda: ctx.navigator.go(Route.LOGIN))
        self.fields["full_name"].focus()

    def _values(self) -> dict:
        return {name: field.get() for name, field in self.fields.items()}

    def _on_typing(self, field: TextField) -> None:
        field.clear_error()
        self.banner.hide()

    def _show_errors(self, errors: dict) -> None:
        for name, message in errors.items():
            if name in self.fields:
                self.fields[name].set_error(message)

    def _submit(self) -> None:
        if self.submit_button.is_loading:
            return
        self.banner.hide()
        for field in self.fields.values():
            field.clear_error()

        values = self._values()
        errors = collect_registration_errors(
            values["full_name"], values["email"], values["username"], values["password"], values["confirm"])
        if errors:
            self._show_errors(errors)
            return

        self.submit_button.set_loading(True, "Creating account...")
        auth = self.ctx.auth_service
        run_in_background(
            self,
            lambda: auth.register(values["full_name"], values["email"], values["username"],
                                  values["password"], values["confirm"]),
            self._on_register_done)

    def _on_register_done(self, user, error) -> None:
        self.submit_button.set_loading(False)
        if error is None:
            show_toast(self, "Account created. You can sign in now.", "success")
            self.ctx.navigator.go(Route.LOGIN, prefill_username=user.username)
        elif isinstance(error, ValidationError):
            self._show_errors(error.errors)
        else:
            logger.error("Registration failed unexpectedly: %s", type(error).__name__)
            self.banner.show(_GENERIC_ERROR)
