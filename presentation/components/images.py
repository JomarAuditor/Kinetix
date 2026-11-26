"""ImageView: a rounded image that loads in the background.

Shows a flat #202329 block while loading, and a placeholder PNG if the URL is
empty or the download fails. Never blocks the UI and never touches a destroyed widget.
"""
from collections import OrderedDict
from concurrent.futures import Future
from pathlib import Path
from typing import Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

from config.theme import Colors, Sizes
from utils import image_cache

_POLL_MS = 40
_MEMORY_LIMIT = 300
_SCALE = 2  # render at 2x so images stay sharp on HiDPI screens
_memory: "OrderedDict[tuple, ctk.CTkImage]" = OrderedDict()


def _remember(key: tuple, image: ctk.CTkImage) -> ctk.CTkImage:
    _memory[key] = image
    if len(_memory) > _MEMORY_LIMIT:
        _memory.popitem(last=False)
    return image


def _round_corners(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1),
                                           radius=radius * _SCALE, fill=255)
    rounded = image.convert("RGBA")
    rounded.putalpha(mask)
    return rounded


def _cover_crop(image: Image.Image, width: int, height: int) -> Image.Image:
    """Fill width x height completely, cropping the overflow from the center."""
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(1, round(image.width * ratio)), max(1, round(image.height * ratio))), Image.BILINEAR)
    left, top = (resized.width - width) // 2, (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _make_image(path: Optional[Path], size: Tuple[int, int], radius: int) -> ctk.CTkImage:
    width, height = size[0] * _SCALE, size[1] * _SCALE
    if path is None:
        base = Image.new("RGB", (width, height), Colors.SURFACE)  # flat loading block
    else:
        with Image.open(path) as source:
            base = _cover_crop(source.convert("RGB"), width, height)
    rounded = _round_corners(base, radius)
    return ctk.CTkImage(light_image=rounded, dark_image=rounded, size=size)


class ImageView(ctk.CTkLabel):
    """ImageView(parent, size=(120, 120), placeholder="music", radius=8). Call load(url).

    Methods: load(url), show_placeholder(), set_size((w, h)).
    """

    def __init__(self, parent, size: Tuple[int, int] = (120, 120), placeholder: str = "music",
                 radius: int = Sizes.IMAGE_RADIUS):
        super().__init__(parent, text="", width=size[0], height=size[1], fg_color="transparent")
        self._size = size
        self._kind = placeholder
        self._radius = radius
        self._url = ""
        self._path: Optional[Path] = None   # image file currently shown (None = block or placeholder)
        self._mode = "placeholder"          # "placeholder", "loading" or "image"
        self._token = 0
        self._job: Optional[str] = None
        self._rendered_key: Optional[tuple] = None
        self._show_placeholder()

    # ---- public API ----
    def load(self, url: str) -> None:
        self._token += 1
        self._cancel_poll()
        self._url = url or ""
        if not image_cache.is_valid_url(self._url):
            if self._url:
                local_path = Path(self._url)
                if local_path.is_file() and self._show_file(local_path):
                    return
            self._show_placeholder()
            return
        cached = image_cache.cached_path(self._url)
        if cached is not None and self._show_file(cached):
            return
        self._show_loading()
        future = image_cache.request_image(self._url)
        if future is None:
            self._show_placeholder()
            return
        self._poll(self._token, future)

    def show_placeholder(self) -> None:
        self._token += 1
        self._cancel_poll()
        self._url = ""
        self._show_placeholder()

    def set_size(self, size: Tuple[int, int]) -> None:
        if size == self._size or not self._alive():
            return
        self._size = size
        self._render()

    # ---- loading ----
    def _poll(self, token: int, future: "Future[Optional[Path]]") -> None:
        if token != self._token or not self._alive():
            return
        if not future.done():
            self._job = self.after(_POLL_MS, lambda: self._poll(token, future))
            return
        self._job = None
        path = None
        try:
            path = future.result()
        except Exception:  # noqa: BLE001 - the cache already logged it
            path = None
        if path is None or not self._show_file(path):
            self._show_placeholder()

    def _cancel_poll(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:  # noqa: BLE001
                pass
            self._job = None

    # ---- drawing ----
    def _show_file(self, path: Path) -> bool:
        self._path, self._mode = path, "image"
        return self._render()

    def _show_loading(self) -> None:
        self._path, self._mode = None, "loading"
        self._render()

    def _show_placeholder(self) -> None:
        self._path, self._mode = None, "placeholder"
        self._render()

    def _render(self) -> bool:
        """Draw the current mode. Returns False if an image file could not be read."""
        if not self._alive():
            return False
        try:
            if self._mode == "image" and self._path is not None:
                render_key = ("image", str(self._path), self._size, self._radius)
                if render_key == self._rendered_key:
                    return True
                image = self._cached(str(self._path), self._path)
            elif self._mode == "loading":
                render_key = ("loading", self._size, self._radius)
                if render_key == self._rendered_key:
                    return True
                image = self._cached("loading", None)
            else:
                render_key = ("placeholder", self._kind, self._size, self._radius)
                if render_key == self._rendered_key:
                    return True
                path = image_cache.placeholder_path(self._kind)
                image = self._cached(f"placeholder:{self._kind}", path)
            self._rendered_key = render_key
            self.configure(width=self._size[0], height=self._size[1], image=image)
            return True
        except Exception:  # noqa: BLE001 - corrupt file: caller falls back to the placeholder
            if self._mode == "image":
                self._mode = "placeholder"
                self._render()
            return False

    def _cached(self, name: str, path: Optional[Path]) -> ctk.CTkImage:
        key = (name, self._size, self._radius)
        image = _memory.get(key)
        if image is None:
            image = _remember(key, _make_image(path, self._size, self._radius))
        return image

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:  # noqa: BLE001
            return False

    def destroy(self) -> None:
        self._token += 1
        self._cancel_poll()
        super().destroy()
