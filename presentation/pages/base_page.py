"""BasePage (parent of every page) and PlaceholderPage (used until a page is built)."""
import customtkinter as ctk

from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Spacing


class BasePage(ctk.CTkFrame):
    """All authenticated pages extend this. `self.ctx` is the AppContext."""

    def __init__(self, parent, ctx):
        super().__init__(parent, fg_color="transparent")
        self.ctx = ctx

    def handle_search(self, query: str) -> bool:
        """Called when the user presses Enter in the top bar search. Return True if handled."""
        return False


class PlaceholderPage(BasePage):
    """Centered 'Coming in a later phase' message. PlaceholderPage(parent, ctx, heading, icon_name)."""

    def __init__(self, parent, ctx, heading: str, icon_name: str, message: str = "Coming in a later phase"):
        super().__init__(parent, ctx)
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        tile = ctk.CTkFrame(center, width=72, height=72, corner_radius=16, fg_color=Colors.ACCENT_TINT)
        tile.pack()
        tile.pack_propagate(False)
        ctk.CTkLabel(tile, text="", image=icons.icon(icon_name, Colors.ACCENT, 32)).pack(expand=True)
        ctk.CTkLabel(center, text=heading, font=typography.section(), text_color=Colors.TEXT).pack(
            pady=(Spacing.LG, Spacing.XS))
        ctk.CTkLabel(center, text=message, font=typography.body(), text_color=Colors.TEXT_SECONDARY).pack()
