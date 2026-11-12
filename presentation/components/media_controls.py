"""Reusable media playback controls: TimeSlider and VolumeControl."""
from typing import Callable, Optional

import customtkinter as ctk

from presentation.components.buttons import IconButton
from presentation.components.inputs import Slider
from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes, Spacing
from utils.helpers import format_duration

_TIME_LABEL_WIDTH = 58


def format_media_time(milliseconds: int) -> str:
    """Format milliseconds as H:MM:SS when >= 1 hour, otherwise M:SS."""
    total_seconds = max(0, int(milliseconds or 0)) // 1000
    hours, rem = divmod(total_seconds, 3600)
    if hours > 0:
        minutes, seconds = divmod(rem, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return format_duration(milliseconds)


class TimeSlider(ctk.CTkFrame):
    """Progress slider with elapsed and total time labels."""

    def __init__(self, parent, on_seek: Optional[Callable[[float], None]] = None,
                 width: int = Sizes.PROGRESS_SLIDER_WIDTH) -> None:
        super().__init__(parent, fg_color="transparent")
        self._on_seek = on_seek
        self._dragging = False
        self._duration_ms = 0

        self._elapsed = ctk.CTkLabel(
            self, text="0:00", width=_TIME_LABEL_WIDTH, anchor="e",
            font=typography.small(), text_color=Colors.TEXT_SECONDARY,
        )
        self._elapsed.pack(side="left")

        self._slider = Slider(self, from_=0, to=1, value=0, command=self._on_drag, width=width)
        self._slider.pack(side="left", fill="x", expand=True, padx=Spacing.SM)
        self._slider.bind("<ButtonPress-1>", self._on_press, add="+")
        self._slider.bind("<ButtonRelease-1>", self._on_release, add="+")

        self._total = ctk.CTkLabel(
            self, text="0:00", width=_TIME_LABEL_WIDTH, anchor="w",
            font=typography.small(), text_color=Colors.TEXT_SECONDARY,
        )
        self._total.pack(side="right")

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    def set_progress(self, position_ms: int, duration_ms: int) -> None:
        self._duration_ms = max(0, int(duration_ms or 0))
        if self._dragging:
            return
        fraction = min(1.0, max(0.0, position_ms / self._duration_ms)) if self._duration_ms > 0 else 0.0
        self._slider.set(fraction)
        self._elapsed.configure(text=format_media_time(position_ms))
        self._total.configure(text=format_media_time(self._duration_ms))

    def reset(self) -> None:
        self._dragging = False
        self._duration_ms = 0
        self._slider.set(0.0)
        self._elapsed.configure(text="0:00")
        self._total.configure(text="0:00")

    def _on_press(self, _event) -> None:
        self._dragging = True

    def _on_drag(self, value: float) -> None:
        if self._dragging and self._duration_ms > 0:
            self._elapsed.configure(text=format_media_time(int(value * self._duration_ms)))

    def _on_release(self, _event) -> None:
        if not self._dragging:
            return
        self._dragging = False
        if self._on_seek is not None:
            self._on_seek(float(self._slider.get()))


class VolumeControl(ctk.CTkFrame):
    """Mute button paired with a volume slider (0-100)."""

    def __init__(self, parent, initial_volume: int = 70,
                 on_change: Optional[Callable[[int], None]] = None,
                 slider_width: int = Sizes.VOLUME_SLIDER_WIDTH) -> None:
        super().__init__(parent, fg_color="transparent")
        self._on_change = on_change
        self._volume = max(0, min(100, int(initial_volume)))
        self._last_nonzero = self._volume if self._volume > 0 else 70

        self._button = IconButton(self, "volume", self._toggle_mute, style="ghost", size=32)
        self._button.pack(side="left", padx=(0, Spacing.XS))

        self._slider = Slider(self, from_=0, to=100, value=self._volume,
                              command=self._on_slide, width=slider_width)
        self._slider.pack(side="left")
        self._refresh_icon()

    @property
    def volume(self) -> int:
        return self._volume

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))
        if self._volume > 0:
            self._last_nonzero = self._volume
        self._slider.set(self._volume)
        self._refresh_icon()

    def _on_slide(self, value: float) -> None:
        self._volume = max(0, min(100, int(round(value))))
        if self._volume > 0:
            self._last_nonzero = self._volume
        self._refresh_icon()
        if self._on_change is not None:
            self._on_change(self._volume)

    def _toggle_mute(self) -> None:
        target = 0 if self._volume > 0 else (self._last_nonzero or 70)
        self.set_volume(target)
        if self._on_change is not None:
            self._on_change(self._volume)

    def _refresh_icon(self) -> None:
        self._button.set_icon("volume_off" if self._volume == 0 else "volume")
