"""Ready-made style dictionaries for CustomTkinter widgets (all colors from the theme)."""
from typing import Dict

from presentation.styles import typography
from presentation.styles.colors import Colors, Sizes


def primary_button() -> Dict:
    return dict(fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER, text_color=Colors.ON_ACCENT,
                text_color_disabled=Colors.ON_ACCENT, border_width=0, height=Sizes.BUTTON_HEIGHT,
                corner_radius=Sizes.BUTTON_RADIUS, font=typography.body_bold())


def secondary_button() -> Dict:
    return dict(fg_color=Colors.SURFACE, hover_color=Colors.HOVER, text_color=Colors.TEXT,
                border_width=1, border_color=Colors.BORDER, height=Sizes.BUTTON_HEIGHT,
                corner_radius=Sizes.BUTTON_RADIUS, font=typography.body_bold())


def ghost_button() -> Dict:
    return dict(fg_color="transparent", hover_color=Colors.HOVER, text_color=Colors.TEXT_SECONDARY,
                border_width=0, height=Sizes.BUTTON_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
                font=typography.body())


def danger_button() -> Dict:
    return dict(fg_color=Colors.ERROR, hover_color=Colors.ERROR, text_color=Colors.TEXT,
                border_width=0, height=Sizes.BUTTON_HEIGHT, corner_radius=Sizes.BUTTON_RADIUS,
                font=typography.body_bold())


def entry() -> Dict:
    return dict(fg_color="transparent", border_width=0, text_color=Colors.TEXT,
                placeholder_text_color=Colors.TEXT_MUTED, font=typography.body())


def slider() -> Dict:
    return dict(fg_color=Colors.HOVER, progress_color=Colors.ACCENT, button_color=Colors.TEXT,
                button_hover_color=Colors.ACCENT, height=16)


def checkbox() -> Dict:
    return dict(fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER, border_color=Colors.BORDER,
                checkmark_color=Colors.ON_ACCENT, text_color=Colors.TEXT_SECONDARY,
                font=typography.body(), corner_radius=4, border_width=2)
