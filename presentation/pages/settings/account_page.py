"""Account page – profile card, edit profile, change password, activity counts, logout."""
import threading
from typing import Optional

import customtkinter as ctk

from core.exceptions import AuthenticationError, ValidationError
from models.user import User
from presentation.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from presentation.components.dialogs import ConfirmDialog, show_toast
from presentation.components.inputs import TextField
from presentation.pages.base_page import BasePage
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("account_page")

_AVATAR_SIZE = 72
_AVATAR_RADIUS = 36


class AccountPage(BasePage):
    """Profile card with edit, change-password, activity counts, and logout."""

    def __init__(self, parent, ctx, **_params) -> None:
        super().__init__(parent, ctx)
        self._auth = ctx.auth_service
        self._library = ctx.library
        self._load_token = 0
        self._build_ui()
        self._refresh_profile()
        self._load_activity()

    # ------------------------------------------------------------------ layout

    def _build_ui(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._scroll.pack(fill="both", expand=True)

        content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        ctk.CTkLabel(
            content, text="Account",
            font=typography.title(), text_color=Colors.TEXT, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.XL))

        self._profile_card(content)
        self._edit_profile_section(content)
        self._change_password_section(content)
        self._activity_section(content)
        self._danger_section(content)

    # ---------------------------------------------------------------- Profile card

    def _profile_card(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=Colors.CARD,
                            border_width=1, border_color=Colors.BORDER,
                            corner_radius=Sizes.CARD_RADIUS)
        card.pack(fill="x", pady=(0, Spacing.LG))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)

        # Avatar circle with initials
        self._avatar_label = ctk.CTkLabel(
            inner, text="?",
            width=_AVATAR_SIZE, height=_AVATAR_SIZE,
            corner_radius=_AVATAR_RADIUS,
            fg_color=Colors.ACCENT_TINT, text_color=Colors.ACCENT,
            font=typography.section(),
        )
        self._avatar_label.pack(side="left", padx=(0, Spacing.LG))

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        self._name_label = ctk.CTkLabel(
            info, text="", font=typography.section(), text_color=Colors.TEXT, anchor="w",
        )
        self._name_label.pack(fill="x")
        self._username_label = ctk.CTkLabel(
            info, text="", font=typography.body(), text_color=Colors.TEXT_SECONDARY, anchor="w",
        )
        self._username_label.pack(fill="x")
        self._email_label = ctk.CTkLabel(
            info, text="", font=typography.body(), text_color=Colors.TEXT_SECONDARY, anchor="w",
        )
        self._email_label.pack(fill="x")
        self._since_label = ctk.CTkLabel(
            info, text="", font=typography.small(), text_color=Colors.TEXT_MUTED, anchor="w",
        )
        self._since_label.pack(fill="x", pady=(Spacing.XS, 0))

    # ---------------------------------------------------------------- Edit profile

    def _edit_profile_section(self, parent) -> None:
        frame = self._section_card(parent, "Edit Profile")

        self._edit_name = TextField(frame, "Full Name", placeholder="Your full name")
        self._edit_name.pack(fill="x", pady=(0, Spacing.SM))

        self._edit_username = TextField(frame, "Username", placeholder="username")
        self._edit_username.pack(fill="x", pady=(0, Spacing.SM))

        self._edit_email = TextField(frame, "Email", placeholder="you@email.com")
        self._edit_email.pack(fill="x", pady=(0, Spacing.MD))

        self._save_profile_btn = PrimaryButton(frame, "Save Profile", self._save_profile, width=160)
        self._save_profile_btn.pack(anchor="w")

    # ---------------------------------------------------------------- Change password

    def _change_password_section(self, parent) -> None:
        frame = self._section_card(parent, "Change Password")

        self._old_pass = TextField(frame, "Current Password", placeholder="", password=True)
        self._old_pass.pack(fill="x", pady=(0, Spacing.SM))

        self._new_pass = TextField(frame, "New Password", placeholder="", password=True)
        self._new_pass.pack(fill="x", pady=(0, Spacing.SM))

        self._confirm_pass = TextField(frame, "Confirm New Password", placeholder="", password=True)
        self._confirm_pass.pack(fill="x", pady=(0, Spacing.MD))

        self._change_pass_btn = PrimaryButton(frame, "Change Password", self._save_password, width=180)
        self._change_pass_btn.pack(anchor="w")

    # ---------------------------------------------------------------- Activity

    def _activity_section(self, parent) -> None:
        frame = self._section_card(parent, "Activity")
        counts_row = ctk.CTkFrame(frame, fg_color="transparent")
        counts_row.pack(fill="x")
        for col in range(3):
            counts_row.grid_columnconfigure(col, weight=1)

        self._fav_count = self._stat_tile(counts_row, "0", "Favorites", 0)
        self._songs_count = self._stat_tile(counts_row, "0", "Songs Played", 1)
        self._movies_count = self._stat_tile(counts_row, "0", "Movies Watched", 2)

    def _stat_tile(self, parent, value: str, label: str, col: int) -> ctk.CTkLabel:
        tile = ctk.CTkFrame(parent, fg_color=Colors.SURFACE,
                            border_width=1, border_color=Colors.BORDER,
                            corner_radius=Sizes.CARD_RADIUS)
        tile.grid(row=0, column=col, sticky="nsew",
                  padx=(0, Spacing.MD if col < 2 else 0))
        num = ctk.CTkLabel(tile, text=value, font=typography.section(),
                           text_color=Colors.ACCENT)
        num.pack(pady=(Spacing.LG, Spacing.XS))
        ctk.CTkLabel(tile, text=label, font=typography.small(),
                     text_color=Colors.TEXT_SECONDARY).pack(pady=(0, Spacing.LG))
        return num

    # ---------------------------------------------------------------- Danger zone

    def _danger_section(self, parent) -> None:
        frame = self._section_card(parent, "Session")
        ctk.CTkLabel(
            frame, text="Signing out will end your session. Your data stays saved.",
            font=typography.body(), text_color=Colors.TEXT_SECONDARY, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.MD))
        DangerButton(frame, "Log Out", self._confirm_logout, width=120).pack(anchor="w")

    # ---------------------------------------------------------------- helpers

    def _section_card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=Colors.CARD,
                            border_width=1, border_color=Colors.BORDER,
                            corner_radius=Sizes.CARD_RADIUS)
        card.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(card, text=title, font=typography.section(),
                     text_color=Colors.TEXT, anchor="w").pack(
            fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.MD),
        )
        ctk.CTkFrame(card, height=1, fg_color=Colors.BORDER, corner_radius=0).pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
        return inner

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    # ---------------------------------------------------------------- refresh profile

    def _refresh_profile(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None:
            return
        self._avatar_label.configure(text=user.initials)
        self._name_label.configure(text=user.full_name)
        self._username_label.configure(text=f"@{user.username}")
        self._email_label.configure(text=user.email)
        created = user.created_at[:10] if user.created_at else "Unknown"
        self._since_label.configure(text=f"Member since {created}")
        # Pre-fill edit fields
        self._edit_name.set(user.full_name)
        self._edit_username.set(user.username)
        self._edit_email.set(user.email)
        # Clear errors
        self._edit_name.clear_error()
        self._edit_username.clear_error()
        self._edit_email.clear_error()

    # ---------------------------------------------------------------- activity

    def _load_activity(self) -> None:
        self._load_token += 1
        token = self._load_token
        user = self.ctx.session_service.current_user
        library = self._library

        def work():
            if user is None or library is None:
                return 0, 0, 0
            from data.repositories.favorites_repository import FavoritesRepository
            from data.repositories.history_repository import HistoryRepository
            fav_repo = FavoritesRepository()
            hist_repo = HistoryRepository()
            fav_counts = fav_repo.count_by_type(user.id)
            hist_counts = hist_repo.count_by_type(user.id)
            total_favs = sum(fav_counts.values())
            songs = hist_counts.get("music", 0)
            movies = hist_counts.get("movie", 0)
            return total_favs, songs, movies

        def done(result, error) -> None:
            if token != self._load_token or not self._alive():
                return
            if error is not None or result is None:
                return
            total_favs, songs, movies = result
            self._fav_count.configure(text=str(total_favs))
            self._songs_count.configure(text=str(songs))
            self._movies_count.configure(text=str(movies))

        run_in_background(self, work, done)

    # ---------------------------------------------------------------- save profile

    def _save_profile(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None:
            return
        full_name = self._edit_name.get().strip()
        username = self._edit_username.get().strip()
        email = self._edit_email.get().strip()

        # Clear previous errors
        self._edit_name.clear_error()
        self._edit_username.clear_error()
        self._edit_email.clear_error()

        self._save_profile_btn.set_loading(True)

        def work():
            return self._auth.update_profile(user.id, full_name, username, email)

        def done(updated_user: User, error) -> None:
            if not self._alive():
                return
            self._save_profile_btn.set_loading(False)
            if error is not None:
                if isinstance(error, ValidationError):
                    errs = error.errors
                    if "full_name" in errs:
                        self._edit_name.set_error(errs["full_name"])
                    if "username" in errs:
                        self._edit_username.set_error(errs["username"])
                    if "email" in errs:
                        self._edit_email.set_error(errs["email"])
                    show_toast(self, "Please fix the highlighted errors.", "error")
                else:
                    show_toast(self, "Could not update profile.", "error")
                return
            # Update session user
            self.ctx.session_service.update_user(updated_user)
            self._refresh_profile()
            # Update topbar name
            try:
                root = self.winfo_toplevel()
                content = getattr(root, "_content", None)
                if content is not None and hasattr(content, "topbar"):
                    content.topbar.set_user(updated_user)
            except Exception:
                pass
            show_toast(self, "Profile updated.", "success")
        run_in_background(self, work, done)

    # ---------------------------------------------------------------- change password

    def _save_password(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None:
            return
        old = self._old_pass.get()
        new = self._new_pass.get()
        confirm = self._confirm_pass.get()

        self._old_pass.clear_error()
        self._new_pass.clear_error()
        self._confirm_pass.clear_error()

        self._change_pass_btn.set_loading(True)

        def work():
            self._auth.change_password(user.id, old, new, confirm)

        def done(_result, error) -> None:
            if not self._alive():
                return
            self._change_pass_btn.set_loading(False)
            if error is not None:
                if isinstance(error, ValidationError):
                    errs = error.errors
                    if "old_password" in errs:
                        self._old_pass.set_error(errs["old_password"])
                    if "new_password" in errs:
                        self._new_pass.set_error(errs["new_password"])
                    if "confirm" in errs:
                        self._confirm_pass.set_error(errs["confirm"])
                    show_toast(self, "Please fix the highlighted errors.", "error")
                elif isinstance(error, AuthenticationError):
                    self._old_pass.set_error(str(error))
                    show_toast(self, str(error), "error")
                else:
                    show_toast(self, "Could not change password.", "error")
                return
            self._old_pass.set("")
            self._new_pass.set("")
            self._confirm_pass.set("")
            show_toast(self, "Password changed.", "success")

        run_in_background(self, work, done)

    # ---------------------------------------------------------------- logout

    def _confirm_logout(self) -> None:
        ConfirmDialog(
            self,
            "Log out?",
            "You will need to sign in again to use Kinetix.",
            confirm_text="Log out",
            danger=True,
            on_confirm=self.ctx.request_logout,
        )

    def destroy(self) -> None:
        self._load_token += 1
        super().destroy()
