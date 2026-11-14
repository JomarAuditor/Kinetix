"""Top bar: page title, search and the signed-in user."""
from typing import Callable, Optional

import customtkinter as ctk

from models.user import User
from presentation.components.inputs import SearchBar
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing


class TopBar(ctk.CTkFrame):
    """TopBar(parent, on_search(query), on_account()). Use set_title, set_search_visible, set_user."""

    def __init__(self, parent, on_search: Callable[[str], None], on_account: Callable[[], None]):
        super().__init__(parent, height=Sizes.TOPBAR_HEIGHT, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.pack_propagate(False)
        self._on_account = on_account

        ctk.CTkFrame(self, height=1, fg_color=Colors.BORDER, corner_radius=0).pack(side="bottom", fill="x")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=Spacing.XL)

        self._title = ctk.CTkLabel(row, text="", font=typography.section(), text_color=Colors.TEXT, anchor="w")
        self._title.pack(side="left")

        self._user_area = ctk.CTkFrame(row, fg_color="transparent", cursor="hand2")
        self._user_area.pack(side="right")
        self._name = ctk.CTkLabel(self._user_area, text="", font=typography.body_bold(),
                                  text_color=Colors.TEXT, cursor="hand2")
        self._name.pack(side="right", padx=(Spacing.SM, 0))
        self._avatar = ctk.CTkLabel(
            self._user_area, text="", width=Sizes.AVATAR_SIZE, height=Sizes.AVATAR_SIZE,
            corner_radius=Sizes.AVATAR_SIZE // 2, fg_color=Colors.ACCENT_TINT, text_color=Colors.ACCENT,
            font=typography.body_bold(), cursor="hand2")
        self._avatar.pack(side="right")
        for widget in (self._user_area, self._name, self._avatar):
            widget.bind("<Button-1>", lambda _e: self._on_account())

        self._search = SearchBar(row, "Search Kinetix...", on_search, width=360)
        self._search_visible = False

    def set_title(self, title: str) -> None:
        self._title.configure(text=title)

    def set_search_visible(self, visible: bool, placeholder: Optional[str] = None) -> None:
        if placeholder:
            self._search.set_placeholder(placeholder)
        if visible and not self._search_visible:
            self._search.pack(side="left", padx=(Spacing.XXL, 0))
        elif not visible and self._search_visible:
            self._search.pack_forget()
        self._search_visible = visible

    def clear_search(self) -> None:
        self._search.clear()

    def set_user(self, user: Optional[User]) -> None:
        if user is None:
            return
        self._avatar.configure(text=user.initials)
        self._name.configure(text=user.full_name)
