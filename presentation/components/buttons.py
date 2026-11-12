"""Buttons: PrimaryButton (teal), SecondaryButton, GhostButton, DangerButton, LinkLabel."""
from typing import Callable, Optional

import customtkinter as ctk

from presentation.styles import icons, typography, widgets
from presentation.styles.colors import Colors, Sizes


class _BaseButton(ctk.CTkButton):
    """Button with an optional loading state (spinner + text, clicks disabled)."""

    _SPINNER_COLOR = Colors.TEXT

    def __init__(self, parent, text: str, command: Optional[Callable] = None, style: Optional[dict] = None,
                 width: int = 140, **extra):
        options = dict(style or {})
        options.update(extra)
        super().__init__(parent, text=text, command=command, width=width, **options)
        self._idle_text = text
        self._loading = False
        self._frames = icons.spinner_frames(self._SPINNER_COLOR, 18)
        self._frame_index = 0
        self._job: Optional[str] = None

    @property
    def is_loading(self) -> bool:
        return self._loading

    def set_loading(self, loading: bool, text: str = "Please wait...") -> None:
        if loading == self._loading:
            return
        self._loading = loading
        if loading:
            self.configure(text=f"  {text}", state="disabled", compound="left", image=self._frames[0])
            self._animate()
        else:
            self._stop_animation()
            self.configure(text=self._idle_text, state="normal", image=None)

    def _animate(self) -> None:
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.configure(image=self._frames[self._frame_index])
        self._job = self.after(80, self._animate)

    def _stop_animation(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def destroy(self) -> None:
        self._stop_animation()
        super().destroy()


class PrimaryButton(_BaseButton):
    _SPINNER_COLOR = Colors.ON_ACCENT

    def __init__(self, parent, text: str, command: Optional[Callable] = None, **extra):
        super().__init__(parent, text, command, widgets.primary_button(), **extra)


class SecondaryButton(_BaseButton):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, **extra):
        super().__init__(parent, text, command, widgets.secondary_button(), **extra)


class GhostButton(_BaseButton):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, **extra):
        super().__init__(parent, text, command, widgets.ghost_button(), **extra)


class DangerButton(_BaseButton):
    def __init__(self, parent, text: str, command: Optional[Callable] = None, **extra):
        super().__init__(parent, text, command, widgets.danger_button(), **extra)


class LinkLabel(ctk.CTkLabel):
    """Clickable teal text, e.g. 'Create Account'."""

    def __init__(self, parent, text: str, command: Callable[[], None]):
        super().__init__(parent, text=text, text_color=Colors.ACCENT, font=typography.body_bold(),
                         fg_color="transparent", cursor="hand2")
        self._command = command
        self.bind("<Button-1>", lambda _event: self._command())
        self.bind("<Enter>", lambda _event: self.configure(text_color=Colors.ACCENT_HOVER))
        self.bind("<Leave>", lambda _event: self.configure(text_color=Colors.ACCENT))


class IconButton(ctk.CTkButton):
    """Square or round button that shows only an icon.

    IconButton(parent, icon_name, command=None, size=36, style="outline"|"accent"|"ghost",
               round_=False, icon_color=None, icon_size=16)
    Methods: set_icon(name), set_enabled(bool)
    """

    def __init__(self, parent, icon_name: str, command: Optional[Callable] = None,
                 size: int = Sizes.ICON_BUTTON_SIZE, style: str = "outline", round_: bool = False,
                 icon_color: Optional[str] = None, icon_size: int = 16):
        fg, hover, border, default_color = {
            "accent": (Colors.ACCENT, Colors.ACCENT_HOVER, 0, Colors.ON_ACCENT),
            "ghost": ("transparent", Colors.HOVER, 0, Colors.TEXT_SECONDARY),
        }.get(style, (Colors.SURFACE, Colors.HOVER, 1, Colors.TEXT))
        self._color = icon_color or default_color
        self._icon_size = icon_size
        super().__init__(parent, text="", image=icons.icon(icon_name, self._color, icon_size),
                         width=size, height=size, corner_radius=size // 2 if round_ else Sizes.BUTTON_RADIUS,
                         fg_color=fg, hover_color=hover, border_width=border, border_color=Colors.BORDER,
                         command=command)

    def set_icon(self, icon_name: str) -> None:
        self.configure(image=icons.icon(icon_name, self._color, self._icon_size))

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state="normal" if enabled else "disabled")
