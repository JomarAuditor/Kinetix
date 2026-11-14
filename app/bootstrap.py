"""Startup: prepare folders and the database, then open the window."""
import sys

from config import settings
from core.exceptions import KinetixError
from data.database import initialize_database
from utils.logger import get_logger

logger = get_logger("bootstrap")


def _show_fatal_error(message: str) -> None:
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Kinetix", message)
        root.destroy()
    except Exception:  # noqa: BLE001 - no GUI available
        print(message, file=sys.stderr)


def run() -> None:
    """Create storage + database automatically, then start the app."""
    try:
        settings.ensure_storage_dirs()
        initialize_database()
    except (OSError, KinetixError) as exc:
        logger.error("Startup failed: %s", exc)
        _show_fatal_error("Kinetix could not prepare its local storage.\nSee storage/logs/kinetix.log.")
        sys.exit(1)

    import customtkinter as ctk
    ctk.set_appearance_mode("dark")

    from app.application import Application  # imported here so the GUI loads after setup
    Application().run()
