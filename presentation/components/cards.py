"""Reusable media widgets for Dashboard, Music, Movies, Games, Favorites and Recently Played.

MediaCard(parent, item, *, image_size=140, tag="", rating=None, favorite=None, show_play=False,
          on_open=None, on_play=None, on_favorite=None, highlighted=False, adaptive=True)
    Vertical card. `item` is a models.media.MediaItem. favorite=None hides the heart.
    on_open(item) / on_play(item) / on_favorite(item) -> bool (new favorite state, or None to ignore).
    Methods: set_favorite(bool), set_highlighted(bool).

MediaRow(parent, item, *, tag="", detail="", time_text="", favorite=None, on_favorite=None,
         action_icon="play", action_style="outline", on_action=None, on_open=None,
         compact=False, highlighted=False)
    Horizontal row. detail = middle column (for example the album), time_text = right text
    (duration or "2h ago"). action_icon=None hides the action button; action_style is
    "outline", "accent" or "ghost". Methods: set_favorite, set_highlighted, set_playing(bool).

Chip(parent, text, accent=False, overlay=False)      small tag
SectionHeader(parent, title, right_text="", chip_text="")
HeartButton(parent, favorite=False, command=None, size=28, circle=False)
FitLabel(parent, text, font, color)                  one line that shortens itself with "..."
FavoriteTracker()                                    keeps hearts of the same item in sync
"""
from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from config.constants import MEDIA_LABELS, MEDIA_PLACEHOLDERS
from models.media import MediaItem
from presentation.components.buttons import IconButton
from presentation.components.images import ImageView
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing

_RESIZE_DELAY_MS = 95


# ---------------------------------------------------------------- helpers
def fit_text(text: str, font, max_pixels: float, scaling: float = 1.0) -> str:
    """Shorten `text` with '...' so it fits in max_pixels (real screen pixels)."""
    limit = max_pixels / max(scaling, 0.1)
    if font.measure(text) <= limit:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if font.measure(text[:middle].rstrip() + "...") <= limit:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + "..." if low else "..."


def _bind_tree(widget, sequence: str, handler: Callable, skip_buttons: bool) -> None:
    if skip_buttons and isinstance(widget, ctk.CTkButton):
        return
    widget.bind(sequence, handler, add="+")
    for child in widget.winfo_children():
        _bind_tree(child, sequence, handler, skip_buttons)


def _is_inside(widget, container) -> bool:
    while widget is not None:
        if widget is container:
            return True
        widget = getattr(widget, "master", None)
    return False


def _wire_interaction(frame, on_click: Optional[Callable[[], None]],
                      on_enter: Callable[[], None], on_leave: Callable[[], None]) -> None:
    """Hover on the whole widget tree; clicks on everything except buttons."""
    def entered(_event) -> None:
        on_enter()

    def left(_event) -> None:
        try:
            x, y = frame.winfo_pointerxy()
            if _is_inside(frame.winfo_containing(x, y), frame):
                return
        except Exception:  # noqa: BLE001 - pointer outside the app
            pass
        on_leave()

    _bind_tree(frame, "<Enter>", entered, skip_buttons=False)
    _bind_tree(frame, "<Leave>", left, skip_buttons=False)
    if on_click is not None:
        _bind_tree(frame, "<Button-1>", lambda _e: on_click(), skip_buttons=True)
        frame.configure(cursor="hand2")


# ---------------------------------------------------------------- small widgets
class FitLabel(ctk.CTkFrame):
    """One line of text that cuts itself with '...' to the width it is given."""

    def __init__(self, parent, text: str = "", font=None, color: str = Colors.TEXT):
        font = font or typography.body()
        super().__init__(parent, width=1, height=font.metrics("linespace") + 4, fg_color="transparent")
        self.pack_propagate(False)
        self._font, self._full, self._shown = font, text, None
        self._last_width = 0
        self._label = ctk.CTkLabel(self, text=text, font=font, text_color=color, anchor="w")
        self._label.pack(fill="both", expand=True)
        self.bind("<Configure>", self._refit)

    def set_text(self, text: str) -> None:
        if text == self._full:
            return
        self._full, self._shown, self._last_width = text, None, 0
        self._refit()

    def set_color(self, color: str) -> None:
        self._label.configure(text_color=color)

    def _refit(self, event=None) -> None:
        width = event.width if event is not None else self.winfo_width()
        if width <= 8 or width == self._last_width:
            return
        self._last_width = width
        if not self._full:
            if self._shown != "":
                self._shown = ""
                self._label.configure(text="")
            return
        shown = fit_text(self._full, self._font, width - 2, self._get_widget_scaling())
        if shown != self._shown:
            self._shown = shown
            self._label.configure(text=shown)


class Chip(ctk.CTkLabel):
    """Small rounded tag such as 'Music' or '24 tracks found'."""

    def __init__(self, parent, text: str, accent: bool = False, overlay: bool = False):
        if accent:
            fg, color = Colors.ACCENT_TINT_CARD, Colors.ACCENT
        else:
            fg, color = (Colors.BACKGROUND if overlay else Colors.SURFACE), Colors.TEXT_SECONDARY
        super().__init__(parent, text=f" {text} ", font=typography.tiny(), text_color=color, fg_color=fg,
                         corner_radius=6, height=Sizes.CHIP_HEIGHT)


class HeartButton(ctk.CTkButton):
    """Heart toggle. `command()` should return the new favorite state (bool) or None to ignore."""

    def __init__(self, parent, favorite: bool = False, command: Optional[Callable[[], Optional[bool]]] = None,
                 size: int = Sizes.HEART_SIZE, circle: bool = False):
        self._toggle_command = command
        self._favorite = favorite
        super().__init__(parent, text="", width=size, height=size, corner_radius=size // 2 if circle else 6,
                         fg_color=Colors.SURFACE if circle else "transparent", hover_color=Colors.HOVER,
                         image=self._icon(favorite), command=self._clicked)

    @property
    def is_favorite(self) -> bool:
        return self._favorite

    def set_favorite(self, favorite: bool) -> None:
        self._favorite = favorite
        try:
            if self.winfo_exists():
                self.configure(image=self._icon(favorite))
        except Exception:  # noqa: BLE001 - destroyed widget
            pass

    @staticmethod
    def _icon(favorite: bool):
        if favorite:
            return icons.icon("heart_filled", Colors.ACCENT, 16)
        return icons.icon("heart", Colors.TEXT_SECONDARY, 16)

    def _clicked(self) -> None:
        if self._toggle_command is None:
            return
        state = self._toggle_command()
        if state is not None:
            self.set_favorite(bool(state))


class SectionHeader(ctk.CTkFrame):
    """Section title with an optional count chip (after the title) and a muted text on the right."""

    def __init__(self, parent, title: str, right_text: str = "", chip_text: str = ""):
        super().__init__(parent, fg_color="transparent")
        self._title = ctk.CTkLabel(self, text=title, font=typography.section(), text_color=Colors.TEXT, anchor="w")
        self._title.pack(side="left")
        self._chip: Optional[Chip] = None
        self._right = ctk.CTkLabel(self, text=right_text, font=typography.small(), text_color=Colors.TEXT_MUTED)
        self._right.pack(side="right")
        if chip_text:
            self.set_chip(chip_text)

    def set_chip(self, text: str) -> None:
        if self._chip is not None:
            self._chip.destroy()
            self._chip = None
        if text:
            self._chip = Chip(self, text)
            self._chip.pack(side="left", padx=(Spacing.MD, 0))

    def set_title(self, title: str) -> None:
        self._title.configure(text=title)

    def set_right_text(self, text: str) -> None:
        self._right.configure(text=text)


class FavoriteTracker:
    """Keeps all hearts of the same item in sync on one page. Call track(widget) for each card/row."""

    def __init__(self) -> None:
        self._widgets: Dict[Tuple[str, str], List] = {}

    def track(self, widget) -> None:
        key = (widget.item.media_type, widget.item.external_id)
        self._widgets.setdefault(key, []).append(widget)

    def update(self, media_type: str, external_id: str, favorite: bool) -> None:
        alive = []
        for widget in self._widgets.get((media_type, external_id), []):
            try:
                if widget.winfo_exists():
                    widget.set_favorite(favorite)
                    alive.append(widget)
            except Exception:  # noqa: BLE001 - destroyed widget
                continue
        self._widgets[(media_type, external_id)] = alive

    def clear(self) -> None:
        self._widgets.clear()


# ---------------------------------------------------------------- vertical card
class MediaCard(ctk.CTkFrame):
    def __init__(self, parent, item: MediaItem, *, image_size: int = Sizes.CARD_IMAGE_DEFAULT, tag: str = "",
                 rating: Optional[float] = None, favorite: Optional[bool] = None, show_play: bool = False,
                 on_open: Optional[Callable[[MediaItem], None]] = None,
                 on_play: Optional[Callable[[MediaItem], None]] = None,
                 on_favorite: Optional[Callable[[MediaItem], Optional[bool]]] = None,
                 highlighted: bool = False, adaptive: bool = True, aspect_ratio: float = 1.0,
                 footer: str = ""):
        super().__init__(parent, fg_color=Colors.CARD, border_width=1, border_color=Colors.BORDER,
                         corner_radius=Sizes.CARD_RADIUS)
        self.item = item
        self._pad = Spacing.SM
        self._side = image_size
        self._aspect = aspect_ratio if aspect_ratio is not None else 1.0
        self._adaptive = adaptive
        self._highlighted = highlighted
        self._hover = False
        self._resize_job: Optional[str] = None
        self._pending_side = image_size
        self.heart: Optional[HeartButton] = None

        pad = self._pad
        self.image = ImageView(self, (image_size, round(image_size * self._aspect)),
                               placeholder=MEDIA_PLACEHOLDERS.get(item.media_type, "music"))
        self.image.pack(padx=pad, pady=(pad, 0))
        self.image.load(item.image_url)

        has_actions = bool(tag or rating or favorite is not None or show_play)

        self.title_label = FitLabel(self, item.title, typography.body_bold(), Colors.TEXT)
        self.title_label.pack(fill="x", padx=pad + 2, pady=(Spacing.SM, 0))
        self.subtitle_label = FitLabel(self, item.subtitle, typography.small(), Colors.TEXT_SECONDARY)
        self.subtitle_label.pack(fill="x", padx=pad + 2, pady=(0, 0 if (has_actions or footer) else pad + 2))
        if has_actions:
            self._build_actions(tag=tag, rating=rating, favorite=favorite, show_play=show_play,
                                on_play=on_play, on_favorite=on_favorite, has_footer=bool(footer))
        if footer:
            self.footer_label = FitLabel(self, footer, typography.tiny(), Colors.TEXT_MUTED)
            self.footer_label.pack(fill="x", padx=pad + 2, pady=(Spacing.XS, pad + 2))

        self._refresh_style()
        _wire_interaction(self, (lambda: on_open(item)) if on_open else None, self._enter, self._leave)
        if adaptive:
            self.bind("<Configure>", self._on_configure, add="+")

    def _build_actions(self, *, tag: str, rating: Optional[float], favorite: Optional[bool],
                       show_play: bool, on_play: Optional[Callable[[MediaItem], None]],
                       on_favorite: Optional[Callable[[MediaItem], Optional[bool]]],
                       has_footer: bool) -> None:
        pad = self._pad
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=pad + 2, pady=(Spacing.SM, 0 if has_footer else pad + 2))

        if tag:
            Chip(row, tag).pack(side="left", padx=(0, Spacing.XS if rating else 0))
        if rating:
            ctk.CTkLabel(row, text="", image=icons.icon("star", Colors.WARNING, 12)).pack(side="left")
            ctk.CTkLabel(row, text=f" {rating:.1f}", font=typography.small(),
                         text_color=Colors.TEXT_SECONDARY).pack(side="left")

        if show_play:
            IconButton(row, "play", lambda: on_play(self.item) if on_play else None,
                       size=Sizes.PLAY_BUTTON_SIZE, style="accent", round_=True).pack(side="right")
        if favorite is not None:
            self.heart = HeartButton(row, favorite, lambda: on_favorite(self.item) if on_favorite else None,
                                     circle=True)
            self.heart.pack(side="right", padx=(0, Spacing.XS if show_play else 0))

    # ---- public ----
    def set_favorite(self, favorite: bool) -> None:
        if self.heart is not None:
            self.heart.set_favorite(favorite)

    def set_highlighted(self, highlighted: bool) -> None:
        self._highlighted = highlighted
        self._refresh_style()

    # ---- look ----
    def _enter(self) -> None:
        if self._hover:
            return
        self._hover = True
        self._refresh_style()

    def _leave(self) -> None:
        if not self._hover:
            return
        self._hover = False
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.configure(fg_color=Colors.HOVER if self._hover else Colors.CARD,
                       border_color=Colors.ACCENT if self._highlighted else Colors.BORDER)

    # ---- the image follows the card width ----
    def _on_configure(self, event) -> None:
        if event.width <= 20:
            return
        width = event.width / self._get_widget_scaling()
        side = int(max(Sizes.CARD_IMAGE_MIN, min(Sizes.CARD_IMAGE_MAX, width - 2 * self._pad - 2)))
        if abs(side - self._pending_side) < 8 and self._resize_job is not None:
            return
        if abs(side - self._side) < 8:
            return
        self._pending_side = side
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:  # noqa: BLE001
                pass
        self._resize_job = self.after(140, self._apply_resize)

    def _apply_resize(self) -> None:
        self._resize_job = None
        try:
            if not self.winfo_exists():
                return
            if abs(self._pending_side - self._side) < 6:
                return
            self._side = self._pending_side
            self.image.set_size((self._side, round(self._side * self._aspect)))
        except Exception:  # noqa: BLE001 - destroyed meanwhile
            pass

    def destroy(self) -> None:
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:  # noqa: BLE001
                pass
            self._resize_job = None
        super().destroy()


# ---------------------------------------------------------------- horizontal row
class MediaRow(ctk.CTkFrame):
    def __init__(self, parent, item: MediaItem, *, tag: str = "", detail: str = "", time_text: str = "",
                 favorite: Optional[bool] = None, on_favorite: Optional[Callable[[MediaItem], Optional[bool]]] = None,
                 action_icon: Optional[str] = "play", action_style: str = "outline",
                 on_action: Optional[Callable[[MediaItem], None]] = None,
                 on_open: Optional[Callable[[MediaItem], None]] = None,
                 compact: bool = False, highlighted: bool = False):
        super().__init__(parent, fg_color=Colors.CARD, border_width=1, border_color=Colors.BORDER,
                         corner_radius=Sizes.ROW_RADIUS)
        self.item = item
        self._highlighted = highlighted
        self._playing = False
        self._hover = False
        self._action_icon = action_icon
        self.heart: Optional[HeartButton] = None
        self.action: Optional[IconButton] = None

        thumb = Sizes.ROW_THUMB_COMPACT if compact else Sizes.ROW_THUMB_SIZE
        column = 0
        self.thumb = ImageView(self, (thumb, thumb), placeholder=MEDIA_PLACEHOLDERS.get(item.media_type, "music"))
        self.thumb.grid(row=0, column=column, padx=(Spacing.MD, Spacing.MD), pady=Spacing.SM)
        self.thumb.load(item.image_url)

        column += 1
        self._build_text_block(column, item, tag, compact)
        self.grid_columnconfigure(column, weight=3, minsize=60)
        if detail:
            column += 1
            self.detail_label = FitLabel(self, detail, typography.body(), Colors.TEXT_SECONDARY)
            self.detail_label.grid(row=0, column=column, sticky="ew", padx=(Spacing.SM, Spacing.SM))
            self.grid_columnconfigure(column, weight=2, minsize=40)
        if time_text:
            column += 1
            ctk.CTkLabel(self, text=time_text, font=typography.small(), text_color=Colors.TEXT_SECONDARY,
                         width=52, anchor="e").grid(row=0, column=column, padx=(Spacing.SM, Spacing.XS))
        if favorite is not None:
            column += 1
            self.heart = HeartButton(self, favorite, lambda: on_favorite(item) if on_favorite else None)
            self.heart.grid(row=0, column=column, padx=(Spacing.XS, Spacing.XS))
        if action_icon:
            column += 1
            self.action = IconButton(self, action_icon, lambda: on_action(item) if on_action else None,
                                     size=Sizes.ICON_BUTTON_SIZE, style=action_style,
                                     round_=action_style == "accent")
            self.action.grid(row=0, column=column, padx=(Spacing.XS, Spacing.MD))
        else:
            self.grid_columnconfigure(column + 1, minsize=Spacing.SM)

        self._action_style = action_style
        self._refresh_style()
        _wire_interaction(self, (lambda: on_open(item)) if on_open else None, self._enter, self._leave)

    def _build_text_block(self, column: int, item: MediaItem, tag: str, compact: bool) -> None:
        block = ctk.CTkFrame(self, fg_color="transparent")
        block.grid(row=0, column=column, sticky="ew")
        self.title_label = FitLabel(block, item.title, typography.body_bold(), Colors.TEXT)
        self.title_label.pack(fill="x")
        line = ctk.CTkFrame(block, fg_color="transparent")
        line.pack(fill="x")
        if tag:
            Chip(line, tag).pack(side="left", padx=(0, Spacing.SM))
        subtitle = item.subtitle
        if compact and not tag:
            subtitle = f"{MEDIA_LABELS.get(item.media_type, '')} \u2022 {item.subtitle}".strip(" \u2022")
        self.subtitle_label = FitLabel(line, subtitle, typography.small(), Colors.TEXT_SECONDARY)
        self.subtitle_label.pack(side="left", fill="x", expand=True)

    # ---- public ----
    def set_favorite(self, favorite: bool) -> None:
        if self.heart is not None:
            self.heart.set_favorite(favorite)

    def set_highlighted(self, highlighted: bool) -> None:
        self._highlighted = highlighted
        self._refresh_style()

    def set_playing(self, playing: bool) -> None:
        """Teal border and title, and the action button shows pause while this row plays."""
        self._playing = playing
        self._highlighted = playing or self._highlighted
        if self.action is not None and self._action_icon:
            self.action.set_icon("pause" if playing else self._action_icon)
        self._refresh_style()

    def clear_playing(self) -> None:
        self._playing = False
        self._highlighted = False
        if self.action is not None and self._action_icon:
            self.action.set_icon(self._action_icon)
        self._refresh_style()

    # ---- look ----
    def _enter(self) -> None:
        if self._hover:
            return
        self._hover = True
        self._refresh_style()

    def _leave(self) -> None:
        if not self._hover:
            return
        self._hover = False
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.configure(fg_color=Colors.HOVER if self._hover else Colors.CARD,
                       border_color=Colors.ACCENT if self._highlighted else Colors.BORDER)
        self.title_label.set_color(Colors.ACCENT if self._highlighted else Colors.TEXT)
