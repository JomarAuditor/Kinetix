"""Loading indicators."""
from typing import Optional

import customtkinter as ctk

from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing


class Spinner(ctk.CTkLabel):
    """A small rotating arc. Call start() / stop()."""

    def __init__(self, parent, color: str = Colors.ACCENT, size: int = 18):
        self._frames = icons.spinner_frames(color, size)
        super().__init__(parent, text="", image=self._frames[0], fg_color="transparent")
        self._index = 0
        self._job: Optional[str] = None

    def start(self) -> None:
        if self._job is None:
            self._tick()

    def stop(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def _tick(self) -> None:
        self._index = (self._index + 1) % len(self._frames)
        self.configure(image=self._frames[self._index])
        self._job = self.after(80, self._tick)

    def destroy(self) -> None:
        self.stop()
        super().destroy()


class StateMessage(ctk.CTkFrame):
    """A one-line box for section states.

    StateMessage(parent, kind="loading"|"empty"|"error", text="", on_retry=None)
    loading = teal spinner, empty = search icon, error = red border + Retry link.
    """

    def __init__(self, parent, kind: str = "empty", text: str = "", on_retry=None):
        is_error = kind == "error"
        super().__init__(parent, fg_color=Colors.ERROR_TINT if is_error else Colors.CARD,
                         border_width=1, border_color=Colors.ERROR if is_error else Colors.BORDER,
                         corner_radius=Sizes.CARD_RADIUS, height=Sizes.STATE_BOX_HEIGHT)
        self.pack_propagate(False)
        self._spinner: Optional[Spinner] = None
        color = Colors.ERROR if is_error else Colors.TEXT_SECONDARY
        if kind == "loading":
            self._spinner = Spinner(self, Colors.ACCENT, 18)
            self._spinner.pack(side="left", padx=(Spacing.LG, Spacing.SM))
            self._spinner.start()
        else:
            name = "alert" if is_error else "search"
            ctk.CTkLabel(self, text="", image=icons.icon(name, color, 16)).pack(
                side="left", padx=(Spacing.LG, Spacing.SM))
        ctk.CTkLabel(self, text=text, font=typography.body(), text_color=color,
                     anchor="w").pack(side="left")
        if is_error and on_retry is not None:
            retry = ctk.CTkLabel(self, text="Retry", font=typography.body_bold(), text_color=Colors.ACCENT,
                                 cursor="hand2")
            retry.pack(side="right", padx=Spacing.LG)
            retry.bind("<Button-1>", lambda _e: on_retry())

    def destroy(self) -> None:
        if self._spinner is not None:
            self._spinner.stop()
        super().destroy()
