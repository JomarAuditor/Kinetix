"""Fixed left navigation: logo, page links, and Logout pinned at the bottom."""
from typing import Callable, Dict

import customtkinter as ctk

from app.navigation import NAV_GROUPS, NavItem
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing


class _NavButton(ctk.CTkButton):
    def __init__(self, parent, item: NavItem, command: Callable[[], None]):
        self._normal_icon = icons.icon(item.icon, Colors.TEXT_SECONDARY)
        self._active_icon = icons.icon(item.icon, Colors.ACCENT)
        super().__init__(parent, text=f"  {item.label}", image=self._normal_icon, compound="left",
                         anchor="w", height=Sizes.NAV_ITEM_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
                         fg_color="transparent", hover_color=Colors.HOVER, text_color=Colors.TEXT_SECONDARY,
                         font=typography.body(), command=command)

    def set_active(self, active: bool) -> None:
        if active:
            self.configure(fg_color=Colors.ACCENT_TINT, hover_color=Colors.ACCENT_TINT,
                           text_color=Colors.ACCENT, image=self._active_icon,
                           font=typography.body_bold())
        else:
            self.configure(fg_color="transparent", hover_color=Colors.HOVER,
                           text_color=Colors.TEXT_SECONDARY, image=self._normal_icon,
                           font=typography.body())


class Sidebar(ctk.CTkFrame):
    """Sidebar(parent, on_navigate(route), on_logout()). Use set_active(route)."""

    def __init__(self, parent, on_navigate: Callable[[str], None], on_logout: Callable[[], None]):
        super().__init__(parent, width=Sizes.SIDEBAR_WIDTH, fg_color=Colors.SIDEBAR, corner_radius=0)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._active_route = ""
        self._buttons: Dict[str, _NavButton] = {}

        ctk.CTkFrame(self, width=1, fg_color=Colors.BORDER, corner_radius=0).pack(side="right", fill="y")
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        ctk.CTkLabel(inner, text="", image=icons.logo_image(124), anchor="w").pack(
            fill="x", padx=Spacing.SM, pady=(Spacing.XS, Spacing.MD))

        for group in NAV_GROUPS:
            for item in group:
                button = _NavButton(inner, item, lambda route=item.route: self._click(route))
                button.pack(fill="x", pady=2)
                self._buttons[item.route] = button

        logout = ctk.CTkButton(
            inner, text="  Logout", image=icons.icon("logout", Colors.TEXT_SECONDARY), compound="left",
            anchor="w", height=Sizes.NAV_ITEM_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
            fg_color="transparent", hover_color=Colors.HOVER, text_color=Colors.TEXT_SECONDARY,
            font=typography.body(), command=on_logout)
        logout.pack(side="bottom", fill="x")
        ctk.CTkFrame(inner, height=1, fg_color=Colors.BORDER).pack(side="bottom", fill="x", pady=Spacing.SM)

    def set_active(self, route: str) -> None:
        self._active_route = route
        for key, button in self._buttons.items():
            button.set_active(key == route)

    def _click(self, route: str) -> None:
        if route != self._active_route:
            self._on_navigate(route)
