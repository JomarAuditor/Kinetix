"""Fonts. Uses Inter if installed, otherwise Segoe UI, otherwise Arial.

Call these only after the main window exists (CTkFont needs a Tk root).
"""
import tkinter.font as tkfont
from typing import Dict, Optional, Tuple

import customtkinter as ctk

from config.theme import Fonts

_family: Optional[str] = None
_cache: Dict[Tuple[int, str], ctk.CTkFont] = {}


def font_family() -> str:
    global _family
    if _family is None:
        installed = set(tkfont.families())
        _family = next((name for name in Fonts.FAMILIES if name in installed), Fonts.FAMILIES[-1])
    return _family


def font(size: int, weight: str = "normal") -> ctk.CTkFont:
    key = (size, weight)
    if key not in _cache:
        _cache[key] = ctk.CTkFont(family=font_family(), size=size, weight=weight)
    return _cache[key]


def title() -> ctk.CTkFont:
    return font(Fonts.SIZE_TITLE, "bold")


def section() -> ctk.CTkFont:
    return font(Fonts.SIZE_SECTION, "bold")


def card() -> ctk.CTkFont:
    return font(Fonts.SIZE_CARD, "bold")


def body() -> ctk.CTkFont:
    return font(Fonts.SIZE_BODY)


def body_bold() -> ctk.CTkFont:
    return font(Fonts.SIZE_BODY, "bold")


def small() -> ctk.CTkFont:
    return font(Fonts.SIZE_SMALL)


def tiny() -> ctk.CTkFont:
    return font(Fonts.SIZE_TINY)
