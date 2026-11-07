"""Small helpers shared by the GUI. No widgets are created here."""
import queue
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from utils.logger import get_logger

logger = get_logger("helpers")
_POLL_MS = 10


def run_in_background(
    widget: Any,
    work: Callable[[], Any],
    on_done: Callable[[Any, Optional[Exception]], None],
) -> None:
    """Run `work()` in a thread, then call `on_done(result, error)` on the Tk thread.

    The worker never touches widgets. The Tk thread polls a queue with after(),
    so the window never freezes. If the widget is destroyed meanwhile, on_done is skipped.
    """
    results: "queue.Queue" = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            results.put((work(), None))
        except Exception as exc:  # noqa: BLE001 - passed to on_done
            results.put((None, exc))

    def poll() -> None:
        try:
            result, error = results.get_nowait()
        except queue.Empty:
            try:
                if widget.winfo_exists():
                    widget.after(_POLL_MS, poll)
            except Exception:  # noqa: BLE001 - window already closed
                pass
            return
        try:
            alive = bool(widget.winfo_exists())
        except Exception:  # noqa: BLE001
            alive = False
        if alive:
            on_done(result, error)

    threading.Thread(target=target, daemon=True).start()
    widget.after(_POLL_MS, poll)


def format_duration(milliseconds: int) -> str:
    """3:20 style text. Shows 0:00 for missing or negative values."""
    seconds = max(0, int(milliseconds or 0)) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def relative_time(timestamp: str) -> str:
    """Turn a UTC text from SQLite into '2h ago' / 'Yesterday'. Empty text if it cannot be read."""
    parsed = None
    for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(timestamp, pattern).replace(tzinfo=timezone.utc)
            break
        except (ValueError, TypeError):
            continue
    if parsed is None:
        return ""
    seconds = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 172800:
        return "Yesterday"
    if seconds < 7 * 86400:
        return f"{seconds // 86400}d ago"
    return parsed.astimezone().strftime("%b %d")
