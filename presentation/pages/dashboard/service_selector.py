"""The three service cards on the Dashboard (Music, Movies, Games)."""
from typing import Callable

import customtkinter as ctk

from app.navigation import Route
from presentation.styles import icons, typography, widgets
from presentation.styles.colors import Colors, Sizes, Spacing

_SERVICES = (
    (Route.MUSIC, "Music", "Search songs and play them inside Kinetix.", "music"),
    (Route.MOVIES, "Movies", "Discover movies and watch supported videos.", "movie"),
    (Route.GAMES, "Games", "Browse games, screenshots and details.", "games"),
)
_DESCRIPTION_WRAP = 230


class ServiceCard(ctk.CTkFrame):
    """ServiceCard(parent, title, description, icon_name, on_open)"""

    def __init__(self, parent, title: str, description: str, icon_name: str, on_open: Callable[[], None]):
        super().__init__(parent, fg_color=Colors.CARD, border_width=1, border_color=Colors.BORDER,
                         corner_radius=Sizes.CARD_RADIUS)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))
        tile = ctk.CTkFrame(top, width=Sizes.SERVICE_ICON_TILE, height=Sizes.SERVICE_ICON_TILE,
                            fg_color=Colors.SURFACE, border_width=1, border_color=Colors.BORDER,
                            corner_radius=Sizes.CARD_RADIUS)
        tile.pack(side="left", anchor="n")
        tile.pack_propagate(False)
        ctk.CTkLabel(tile, text="", image=icons.icon(icon_name, Colors.ACCENT, 22)).pack(expand=True)
        text = ctk.CTkFrame(top, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(Spacing.MD, 0))
        ctk.CTkLabel(text, text=title, font=typography.card(), text_color=Colors.TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(text, text=description, font=typography.body(), text_color=Colors.TEXT_SECONDARY,
                     anchor="w", justify="left", wraplength=_DESCRIPTION_WRAP).pack(fill="x")
        ctk.CTkButton(self, text="Open  ", image=icons.icon("chevron_right", Colors.ON_ACCENT, 14),
                      compound="right", width=Sizes.SERVICE_BUTTON_WIDTH, command=on_open,
                      **widgets.primary_button()).pack(anchor="e", padx=Spacing.LG, pady=(0, Spacing.LG))


class ServiceSelector(ctk.CTkFrame):
    """ServiceSelector(parent, on_open(route)): three equal cards in one row."""

    def __init__(self, parent, on_open: Callable[[str], None]):
        super().__init__(parent, fg_color="transparent")
        for index, (route, title, description, icon_name) in enumerate(_SERVICES):
            self.grid_columnconfigure(index, weight=1, uniform="services")
            card = ServiceCard(self, title, description, icon_name, lambda r=route: on_open(r))
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else Spacing.SM,
                                                                 0 if index == len(_SERVICES) - 1 else Spacing.SM))
