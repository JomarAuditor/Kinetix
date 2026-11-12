"""Inputs: TextField (label, show/hide password, error), SearchBar, Slider."""
from typing import Callable, Optional

import customtkinter as ctk

from presentation.styles import icons, typography, widgets
from presentation.styles.colors import Colors, Sizes, Spacing


class TextField(ctk.CTkFrame):
    """Label + entry + message line.

    TextField(parent, label, placeholder="", password=False, hint="", on_submit=None)
    Methods: get(), set(text), set_error(message), clear_error(), focus(), set_enabled(bool)
    """

    def __init__(self, parent, label: str, placeholder: str = "", password: bool = False,
                 hint: str = "", on_submit: Optional[Callable[[], None]] = None):
        super().__init__(parent, fg_color="transparent")
        self._password = password
        self._hint = hint
        self._has_error = False
        self._focused = False
        self._revealed = False

        ctk.CTkLabel(self, text=label, font=typography.small(), text_color=Colors.TEXT_SECONDARY,
                     anchor="w").pack(fill="x", pady=(0, Spacing.XS))

        self._box = ctk.CTkFrame(self, fg_color=Colors.SURFACE, border_width=1, border_color=Colors.BORDER,
                                 corner_radius=Sizes.INPUT_RADIUS, height=Sizes.INPUT_HEIGHT)
        self._box.pack(fill="x")
        self._box.pack_propagate(False)

        self.entry = ctk.CTkEntry(self._box, placeholder_text=placeholder,
                                  show="\u2022" if password else "", **widgets.entry())
        self.entry.pack(side="left", fill="both", expand=True, padx=(Spacing.MD, 0), pady=2)

        if password:
            self._toggle = ctk.CTkButton(self._box, text="", image=icons.icon("eye", Colors.TEXT_SECONDARY),
                                         width=32, height=32, fg_color="transparent",
                                         hover_color=Colors.HOVER, corner_radius=6,
                                         command=self._toggle_password)
            self._toggle.pack(side="right", padx=(0, Spacing.SM))

        self._message = ctk.CTkLabel(self, text="", anchor="w", justify="left", font=typography.small(),
                                     text_color=Colors.TEXT_MUTED, compound="left")
        if hint:
            self._show_hint()

        self.entry.bind("<FocusIn>", lambda _e: self._set_focus(True), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self._set_focus(False), add="+")
        if on_submit:
            self.entry.bind("<Return>", lambda _e: on_submit(), add="+")

    # ---- public API ----
    def get(self) -> str:
        return self.entry.get()

    def set(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def focus(self) -> None:
        self.entry.focus_set()

    def set_enabled(self, enabled: bool) -> None:
        self.entry.configure(state="normal" if enabled else "disabled")

    def set_error(self, message: str) -> None:
        if not message:
            self.clear_error()
            return
        self._has_error = True
        self._message.configure(text=f" {message}", text_color=Colors.ERROR,
                                image=icons.icon("alert", Colors.ERROR, 14))
        self._message.pack(fill="x", pady=(Spacing.XS, 0))
        self._refresh_border()

    def clear_error(self) -> None:
        if not self._has_error:
            return
        self._has_error = False
        self._message.pack_forget()
        if self._hint:
            self._show_hint()
        self._refresh_border()

    # ---- internals ----
    def _show_hint(self) -> None:
        self._message.configure(text=self._hint, text_color=Colors.TEXT_MUTED, image=None)
        self._message.pack(fill="x", pady=(Spacing.XS, 0))

    def _set_focus(self, focused: bool) -> None:
        self._focused = focused
        self._refresh_border()

    def _refresh_border(self) -> None:
        if self._has_error:
            color = Colors.ERROR
        elif self._focused:
            color = Colors.ACCENT
        else:
            color = Colors.BORDER
        self._box.configure(border_color=color)

    def _toggle_password(self) -> None:
        self._revealed = not self._revealed
        self.entry.configure(show="" if self._revealed else "\u2022")
        name = "eye_off" if self._revealed else "eye"
        self._toggle.configure(image=icons.icon(name, Colors.TEXT_SECONDARY))


class SearchBar(ctk.CTkFrame):
    """Search field with a magnifier. SearchBar(parent, placeholder, on_submit(query))."""

    def __init__(self, parent, placeholder: str = "Search...",
                 on_submit: Optional[Callable[[str], None]] = None, width: int = 360):
        super().__init__(parent, fg_color=Colors.SURFACE, border_width=1, border_color=Colors.BORDER,
                         corner_radius=Sizes.INPUT_RADIUS, width=width, height=40)
        self.pack_propagate(False)
        self._on_submit = on_submit
        ctk.CTkLabel(self, text="", image=icons.icon("search", Colors.TEXT_MUTED, 16),
                     fg_color="transparent").pack(side="left", padx=(Spacing.MD, Spacing.XS))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, **widgets.entry())
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, Spacing.SM), pady=2)
        self.entry.bind("<FocusIn>", lambda _e: self.configure(border_color=Colors.ACCENT), add="+")
        self.entry.bind("<FocusOut>", lambda _e: self.configure(border_color=Colors.BORDER), add="+")
        self.entry.bind("<Return>", lambda _e: self._submit(), add="+")

    def get(self) -> str:
        return self.entry.get().strip()

    def clear(self) -> None:
        self.entry.delete(0, "end")

    def set_placeholder(self, text: str) -> None:
        self.entry.configure(placeholder_text=text)

    def _submit(self) -> None:
        if self._on_submit:
            self._on_submit(self.get())


class Slider(ctk.CTkSlider):
    """Teal slider for volume and progress. Slider(parent, from_=0, to=100, value=70, command=None)."""

    def __init__(self, parent, from_: float = 0, to: float = 100, value: float = 0,
                 command: Optional[Callable[[float], None]] = None, width: int = 140):
        super().__init__(parent, from_=from_, to=to, command=command, width=width, **widgets.slider())
        self.set(value)
