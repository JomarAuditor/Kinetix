"""Logging to storage/logs/kinetix.log. Never log passwords, tokens or keys."""
import logging
from logging.handlers import RotatingFileHandler

from config import settings

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    settings.ensure_storage_dirs()
    root = logging.getLogger("kinetix")
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(
        settings.LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(formatter)
    root.addHandler(console)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"kinetix.{name}")
