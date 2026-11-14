"""Pieces shared by the Login and Sign Up pages."""
from typing import Callable, Optional

import customtkinter as ctk

from presentation.components.buttons import LinkLabel
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing

_CARD_PADDING = Spacing.XL + Spacing.SM  # 32


class AuthPage(ctk.CTkFrame):
    """Full-window dark background with a centered card. Put widgets into `self.body`."""

    def __init__(self, parent, heading: str, subtitle: str):
        super().__init__(parent, fg_color=Colors.BACKGROUND, corner_radius=0)
        self.card = ctk.CTkFrame(self, fg_color=Colors.CARD, border_width=1, border_color=Colors.BORDER,
                                 corner_radius=Sizes.CARD_RADIUS)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        self.body = ctk.CTkFrame(self.card, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=_CARD_PADDING, pady=Spacing.XL)
        # CustomTkinter does not allow width in place(), so a fixed-width spacer sets the card width.
        ctk.CTkFrame(self.body, width=Sizes.AUTH_CARD_WIDTH - 2 * _CARD_PADDING, height=1,
                     fg_color="transparent").pack(fill="x")

        ctk.CTkLabel(self.body, text="", image=icons.logo_image(128)).pack(pady=(0, Spacing.LG))
        ctk.CTkLabel(self.body, text=heading, font=typography.title(), text_color=Colors.TEXT).pack()
        ctk.CTkLabel(self.body, text=subtitle, font=typography.body(),
                     text_color=Colors.TEXT_SECONDARY).pack(pady=(Spacing.XS, Spacing.XL))


class InlineBanner(ctk.CTkFrame):
    """Message box (error or success). Hidden until show(). Packs itself before `before`."""

    _STYLES = {
        "error": ("alert", Colors.ERROR, Colors.ERROR_TINT),
        "success": ("check", Colors.SUCCESS, Colors.SUCCESS_TINT),
    }

    def __init__(self, parent, before: ctk.CTkBaseClass):
        super().__init__(parent, corner_radius=Sizes.INPUT_RADIUS, border_width=1)
        self._before = before
        self._label = ctk.CTkLabel(self, text="", compound="left", anchor="w", justify="left",
                                   font=typography.body(),
                                   wraplength=Sizes.AUTH_CARD_WIDTH - 2 * _CARD_PADDING - 48)
        self._label.pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

    def show(self, message: str, kind: str = "error") -> None:
        icon_name, color, tint = self._STYLES[kind]
        self.configure(fg_color=tint, border_color=color)
        self._label.configure(text=f" {message}", text_color=color, image=icons.icon(icon_name, color, 16))
        self.pack(fill="x", pady=(0, Spacing.MD), before=self._before)

    def hide(self) -> None:
        self.pack_forget()


def build_switch_row(parent, question: str, link_text: str, command: Callable[[], None]) -> None:
    """'Don't have an account?  Create Account' row."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(pady=(Spacing.LG, 0))
    ctk.CTkLabel(row, text=question, font=typography.body(), text_color=Colors.TEXT_SECONDARY).pack(
        side="left", padx=(0, Spacing.SM))
    LinkLabel(row, link_text, command).pack(side="left")
