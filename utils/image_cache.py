"""Background image downloads with a disk cache, plus the placeholder PNGs.

Nothing here touches widgets. request_image(url) returns a Future; the GUI
checks future.done() with after(), so the window never waits for the network.
"""
import hashlib
import io
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from PIL import Image, ImageDraw

from config import settings
from config.constants import USER_AGENT
from config.theme import Colors
from utils.logger import get_logger

logger = get_logger("image_cache")

PLACEHOLDER_KINDS = ("music", "movie", "game", "avatar")
_PLACEHOLDER_SIZE = 300
_MAX_BYTES = 8 * 1024 * 1024
_RETRY_AFTER_SECONDS = 120

_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="kinetix-img")
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})
_session.mount("https://", HTTPAdapter(pool_connections=10, pool_maxsize=10))
_session.mount("http://", HTTPAdapter(pool_connections=10, pool_maxsize=10))
_lock = threading.Lock()
_inflight: Dict[str, Future] = {}
_failed: Dict[str, float] = {}


# ---- disk cache ----
def _cache_file(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return settings.CACHE_DIR / f"{digest}.img"


def is_valid_url(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith(("http://", "https://"))


def cached_path(url: str) -> Optional[Path]:
    """The cached file for this URL, or None if it is not downloaded yet."""
    if not is_valid_url(url):
        return None
    path = _cache_file(url)
    try:
        return path if path.is_file() and path.stat().st_size > 0 else None
    except OSError:
        return None


def request_image(url: str) -> Optional["Future[Optional[Path]]"]:
    """Start (or join) a background download. The Future gives a Path, or None on failure."""
    if not is_valid_url(url):
        return None
    with _lock:
        if url in _inflight:
            return _inflight[url]
        failed_at = _failed.get(url)
        if failed_at and time.monotonic() - failed_at < _RETRY_AFTER_SECONDS:
            done: "Future[Optional[Path]]" = Future()
            done.set_result(None)
            return done
        future = _executor.submit(_download, url)
        _inflight[url] = future
    return future


def _download(url: str) -> Optional[Path]:
    try:
        return _download_and_store(url)
    except Exception as exc:  # noqa: BLE001 - any failure means "show the placeholder"
        logger.warning("Image download failed: %s", exc)
        with _lock:
            _failed[url] = time.monotonic()
        return None
    finally:
        with _lock:
            _inflight.pop(url, None)


def _download_and_store(url: str) -> Path:
    path = _cache_file(url)
    if cached_path(url):
        return path
    response = _session.get(url, timeout=(5, 10), stream=True)
    try:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            data.extend(chunk)
            if len(data) > _MAX_BYTES:
                raise ValueError("image is too large")
    finally:
        response.close()
    Image.open(io.BytesIO(bytes(data))).verify()  # raises if this is not a real image
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(bytes(data))
    temp.replace(path)
    return path


def shutdown() -> None:
    """Release background image workers and HTTP session on application exit."""
    try:
        _executor.shutdown(wait=False, cancel_futures=True)
    except Exception:  # noqa: BLE001
        pass
    try:
        _session.close()
    except Exception:  # noqa: BLE001
        pass


# ---- placeholders ----
def placeholder_path(kind: str) -> Path:
    """Path of the placeholder PNG for 'music', 'movie', 'game' or 'avatar' (created if missing)."""
    if kind not in PLACEHOLDER_KINDS:
        kind = "music"
    path = settings.PLACEHOLDERS_DIR / f"{kind}.png"
    if not path.is_file():
        ensure_placeholders()
    return path


def ensure_placeholders() -> None:
    """Draw any missing placeholder PNG: a flat surface block with a simple muted glyph."""
    settings.PLACEHOLDERS_DIR.mkdir(parents=True, exist_ok=True)
    for kind in PLACEHOLDER_KINDS:
        path = settings.PLACEHOLDERS_DIR / f"{kind}.png"
        if not path.is_file():
            _draw_placeholder(kind).save(path)


def _draw_placeholder(kind: str) -> Image.Image:
    scale = 2
    size = _PLACEHOLDER_SIZE * scale
    image = Image.new("RGB", (size, size), Colors.SURFACE)
    draw = ImageDraw.Draw(image)
    color, mid, width = Colors.TEXT_MUTED, size // 2, size // 30
    unit = size / 300
    if kind == "music":
        draw.ellipse((mid - 60 * unit, mid - 60 * unit, mid + 60 * unit, mid + 60 * unit), outline=color, width=width)
        draw.ellipse((mid - 14 * unit, mid - 14 * unit, mid + 14 * unit, mid + 14 * unit), outline=color, width=width)
    elif kind == "movie":
        draw.polygon([(mid - 28 * unit, mid - 44 * unit), (mid + 48 * unit, mid), (mid - 28 * unit, mid + 44 * unit)],
                     outline=color, width=width)
    elif kind == "game":
        draw.rounded_rectangle((mid - 64 * unit, mid - 34 * unit, mid + 64 * unit, mid + 34 * unit),
                               radius=30 * unit, outline=color, width=width)
        draw.line((mid - 36 * unit, mid - 12 * unit, mid - 36 * unit, mid + 12 * unit), fill=color, width=width)
        draw.line((mid - 48 * unit, mid, mid - 24 * unit, mid), fill=color, width=width)
        draw.ellipse((mid + 26 * unit, mid - 4 * unit, mid + 36 * unit, mid + 6 * unit), fill=color)
        draw.ellipse((mid + 42 * unit, mid + 6 * unit, mid + 52 * unit, mid + 16 * unit), fill=color)
    else:  # avatar
        draw.ellipse((mid - 34 * unit, mid - 66 * unit, mid + 34 * unit, mid + 2 * unit), outline=color, width=width)
        draw.arc((mid - 66 * unit, mid + 20 * unit, mid + 66 * unit, mid + 150 * unit), 180, 360,
                 fill=color, width=width)
    return image.resize((_PLACEHOLDER_SIZE, _PLACEHOLDER_SIZE), Image.LANCZOS)
