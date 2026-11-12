"""Simple line icons and the logo, drawn with Pillow (no icon packs needed).

icon("home", color) -> CTkImage        (cached)
spinner_frames(color) -> list of CTkImage for a rotating arc
logo_image(width) -> CTkImage          (horizontal Kinetix logo)
"""
import math
from typing import Dict, List, Sequence, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

from config import settings
from config.theme import Colors, Sizes

_GRID = 24          # icons are designed on a 24 x 24 grid
_SUPERSAMPLE = 4    # draw big, shrink for smooth edges
_STROKE = 2.0
_Point = Tuple[float, float]


class _Canvas:
    """Draws in 24-grid units on a large image."""

    def __init__(self, pixels: int, color: str):
        self.k = pixels * _SUPERSAMPLE / _GRID
        self.color = color
        self.image = Image.new("RGBA", (pixels * _SUPERSAMPLE,) * 2, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.width = max(1, round(_STROKE * self.k))

    def _px(self, points: Sequence[_Point]) -> List[_Point]:
        return [(x * self.k, y * self.k) for x, y in points]

    def line(self, points: Sequence[_Point]) -> None:
        pts = self._px(points)
        self.draw.line(pts, fill=self.color, width=self.width, joint="curve")
        radius = self.width / 2
        for x, y in (pts[0], pts[-1]):  # round caps
            self.draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=self.color)

    def polygon(self, points: Sequence[_Point]) -> None:
        self.draw.polygon(self._px(points), fill=self.color)

    def filled_rect(self, x1: float, y1: float, x2: float, y2: float, r: float = 0) -> None:
        (a, b), (c, d) = self._px([(x1, y1), (x2, y2)])
        self.draw.rounded_rectangle((a, b, c, d), radius=r * self.k, fill=self.color)

    def circle(self, cx: float, cy: float, r: float, fill: bool = False) -> None:
        box = (self._px([(cx - r, cy - r)])[0] + self._px([(cx + r, cy + r)])[0])
        if fill:
            self.draw.ellipse(box, fill=self.color)
        else:
            self.draw.ellipse(box, outline=self.color, width=self.width)

    def arc(self, box: Tuple[float, float, float, float], start: float, end: float) -> None:
        left, top = self._px([(box[0], box[1])])[0]
        right, bottom = self._px([(box[2], box[3])])[0]
        self.draw.arc((left, top, right, bottom), start, end, fill=self.color, width=self.width)

    def rounded_rect(self, x1: float, y1: float, x2: float, y2: float, r: float) -> None:
        (a, b), (c, d) = self._px([(x1, y1), (x2, y2)])
        self.draw.rounded_rectangle((a, b, c, d), radius=r * self.k, outline=self.color, width=self.width)

    def finish(self, pixels: int) -> Image.Image:
        return self.image.resize((pixels, pixels), Image.LANCZOS)


def _draw_home(c: _Canvas) -> None:
    c.line([(3, 11), (12, 3), (21, 11)])
    c.line([(5.5, 9.5), (5.5, 20), (18.5, 20), (18.5, 9.5)])
    c.line([(10, 20), (10, 14.5), (14, 14.5), (14, 20)])


def _draw_music(c: _Canvas) -> None:
    c.circle(7, 18, 3)
    c.circle(17, 16, 3)
    c.line([(10, 18), (10, 6), (20, 4), (20, 16)])


def _draw_movie(c: _Canvas) -> None:
    c.rounded_rect(3, 4.5, 21, 19.5, 3)
    c.line([(10.5, 9), (15, 12), (10.5, 15), (10.5, 9)])


def _draw_games(c: _Canvas) -> None:
    c.rounded_rect(2.5, 7, 21.5, 17.5, 4)
    c.line([(7, 10.5), (7, 14.5)])
    c.line([(5, 12.5), (9, 12.5)])
    c.circle(15.5, 11.5, 0.9, fill=True)
    c.circle(18, 13.5, 0.9, fill=True)


def _heart_points() -> List[_Point]:
    points = []
    for step in range(0, 101):
        t = step / 100 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        points.append((12 + x * 0.6, 10.5 - y * 0.6))
    return points


def _draw_heart(c: _Canvas) -> None:
    c.line(_heart_points())


def _draw_heart_filled(c: _Canvas) -> None:
    c.polygon(_heart_points())


def _draw_play(c: _Canvas) -> None:
    c.polygon([(7, 4), (20, 12), (7, 20)])


def _draw_pause(c: _Canvas) -> None:
    c.filled_rect(6, 4.5, 10.5, 19.5, 1.2)
    c.filled_rect(13.5, 4.5, 18, 19.5, 1.2)


def _draw_skip_next(c: _Canvas) -> None:
    c.polygon([(5, 5), (16, 12), (5, 19)])
    c.filled_rect(17, 5, 20, 19, 1)


def _draw_skip_prev(c: _Canvas) -> None:
    c.polygon([(19, 5), (8, 12), (19, 19)])
    c.filled_rect(4, 5, 7, 19, 1)


def _speaker(c: _Canvas) -> None:
    c.polygon([(3.5, 9), (8, 9), (13, 5), (13, 19), (8, 15), (3.5, 15)])


def _draw_volume(c: _Canvas) -> None:
    _speaker(c)
    c.arc((8, 7.5, 18, 16.5), 305, 55)
    c.arc((6, 4.5, 22, 19.5), 305, 55)


def _draw_volume_off(c: _Canvas) -> None:
    _speaker(c)
    c.line([(16, 9), (21, 15)])
    c.line([(21, 9), (16, 15)])


def _draw_mic(c: _Canvas) -> None:
    c.rounded_rect(9, 3, 15, 14, 3)
    c.arc((5.5, 7, 18.5, 18.5), 0, 180)
    c.line([(12, 18.5), (12, 22)])
    c.line([(9, 22), (15, 22)])


def _draw_chevron_right(c: _Canvas) -> None:
    c.line([(9, 6), (15, 12), (9, 18)])


def _draw_star(c: _Canvas) -> None:
    points = []
    for index in range(10):
        radius = 9.5 if index % 2 == 0 else 4.2
        angle = -math.pi / 2 + index * math.pi / 5
        points.append((12 + radius * math.cos(angle), 12.5 + radius * math.sin(angle)))
    c.polygon(points)


def _draw_clock(c: _Canvas) -> None:
    c.circle(12, 12, 9)
    c.line([(12, 7), (12, 12), (15.5, 14)])


def _draw_settings(c: _Canvas) -> None:
    for y, knob_x in ((6, 8), (12, 16), (18, 10)):
        c.line([(3.5, y), (20.5, y)])
        c.circle(knob_x, y, 2.4, fill=False)


def _draw_user(c: _Canvas) -> None:
    c.circle(12, 8, 4)
    c.arc((4, 14, 20, 30), 180, 360)


def _draw_logout(c: _Canvas) -> None:
    c.line([(9, 4), (4.5, 4), (4.5, 20), (9, 20)])
    c.line([(10, 12), (20, 12)])
    c.line([(16, 8), (20, 12), (16, 16)])


def _eye_outline(c: _Canvas) -> None:
    upper = [(2.5 + 19 * i / 24, 12 - 6 * (1 - ((i - 12) / 12) ** 2)) for i in range(25)]
    lower = [(x, 24 - y) for x, y in reversed(upper)]
    c.line(upper + lower)
    c.circle(12, 12, 3)


def _draw_eye(c: _Canvas) -> None:
    _eye_outline(c)


def _draw_eye_off(c: _Canvas) -> None:
    _eye_outline(c)
    c.line([(4, 4), (20, 20)])


def _draw_search(c: _Canvas) -> None:
    c.circle(10.5, 10.5, 6.5)
    c.line([(15.5, 15.5), (20.5, 20.5)])


def _draw_alert(c: _Canvas) -> None:
    c.circle(12, 12, 9)
    c.line([(12, 7.5), (12, 13)])
    c.circle(12, 16.3, 0.9, fill=True)


def _draw_check(c: _Canvas) -> None:
    c.line([(4.5, 12.5), (10, 18), (19.5, 7)])


def _draw_close(c: _Canvas) -> None:
    c.line([(6, 6), (18, 18)])
    c.line([(18, 6), (6, 18)])


def _draw_arrow_left(c: _Canvas) -> None:
    c.line([(19, 12), (5, 12)])
    c.line([(11, 6), (5, 12), (11, 18)])


def _draw_stop(c: _Canvas) -> None:
    c.filled_rect(6, 6, 18, 18, 2)


def _draw_fullscreen(c: _Canvas) -> None:
    c.line([(4, 9), (4, 4), (9, 4)])
    c.line([(15, 4), (20, 4), (20, 9)])
    c.line([(20, 15), (20, 20), (15, 20)])
    c.line([(9, 20), (4, 20), (4, 15)])


def _draw_exit_fullscreen(c: _Canvas) -> None:
    c.line([(4, 9), (9, 9), (9, 4)])
    c.line([(15, 4), (15, 9), (20, 9)])
    c.line([(20, 15), (15, 15), (15, 20)])
    c.line([(9, 20), (9, 15), (4, 15)])


def _draw_link(c: _Canvas) -> None:
    c.line([(10, 14), (14, 10)])
    c.arc((4, 8, 14, 18), 45, 225)
    c.arc((10, 6, 20, 16), 225, 45)


_DRAWERS = {
    "home": _draw_home, "music": _draw_music, "movie": _draw_movie, "games": _draw_games,
    "heart": _draw_heart, "clock": _draw_clock, "settings": _draw_settings, "user": _draw_user,
    "logout": _draw_logout, "eye": _draw_eye, "eye_off": _draw_eye_off, "search": _draw_search,
    "alert": _draw_alert, "check": _draw_check, "close": _draw_close,
    "heart_filled": _draw_heart_filled, "play": _draw_play, "pause": _draw_pause,
    "skip_next": _draw_skip_next, "skip_prev": _draw_skip_prev, "volume": _draw_volume,
    "volume_off": _draw_volume_off, "mic": _draw_mic, "chevron_right": _draw_chevron_right,
    "star": _draw_star, "arrow_left": _draw_arrow_left, "stop": _draw_stop,
    "fullscreen": _draw_fullscreen, "exit_fullscreen": _draw_exit_fullscreen, "link": _draw_link,
}

_icon_cache: Dict[Tuple[str, str, int], ctk.CTkImage] = {}
_spinner_cache: Dict[Tuple[str, int], List[ctk.CTkImage]] = {}
_logo_cache: Dict[int, ctk.CTkImage] = {}


def render_icon_image(name: str, color: str, size: int) -> Image.Image:
    """Plain PIL image of an icon (rendered at 2x for sharp HiDPI display)."""
    if name not in _DRAWERS:
        raise ValueError(f"Unknown icon: {name}")
    pixels = size * 2
    canvas = _Canvas(pixels, color)
    _DRAWERS[name](canvas)
    return canvas.finish(pixels)


def _to_ctk(image: Image.Image, size: int) -> ctk.CTkImage:
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def icon(name: str, color: str = Colors.TEXT_SECONDARY, size: int = Sizes.ICON_SIZE) -> ctk.CTkImage:
    key = (name, color, size)
    if key not in _icon_cache:
        _icon_cache[key] = _to_ctk(render_icon_image(name, color, size), size)
    return _icon_cache[key]


def spinner_frames(color: str = Colors.ON_ACCENT, size: int = 18, count: int = 12) -> List[ctk.CTkImage]:
    """Frames of a rotating arc. Show them one after another with after()."""
    key = (color, size)
    if key not in _spinner_cache:
        frames = []
        pixels = size * 2
        for index in range(count):
            canvas = _Canvas(pixels, color)
            start = index * 360 / count
            canvas.arc((3.5, 3.5, 20.5, 20.5), start, start + 270)
            frames.append(_to_ctk(canvas.finish(pixels), size))
        _spinner_cache[key] = frames
    return _spinner_cache[key]


def logo_image(width: int) -> ctk.CTkImage:
    """The horizontal Kinetix logo (mark + wordmark), cropped to its content."""
    if width not in _logo_cache:
        image = Image.open(settings.LOGOS_DIR / "kinetix_logo_horizontal.png").convert("RGBA")
        image = image.crop(image.getbbox())
        height = round(width * image.height / image.width)
        _logo_cache[width] = ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
    return _logo_cache[width]
