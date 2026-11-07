"""Single source of truth for Kinetix colors, spacing, sizes and fonts.

Every page and widget must read its look from here (or from
presentation/styles, which builds on this file). Teal is the only accent.
"""


def blend(foreground: str, background: str, alpha: float) -> str:
    """Mix two hex colors. Used to make soft tints from the palette itself."""
    def parts(value: str):
        value = value.lstrip("#")
        return [int(value[i:i + 2], 16) for i in (0, 2, 4)]

    mixed = [
        round(f * alpha + b * (1 - alpha))
        for f, b in zip(parts(foreground), parts(background))
    ]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


class Colors:
    BACKGROUND = "#101114"
    SIDEBAR = "#14161A"
    CARD = "#191B20"
    SURFACE = "#202329"
    HOVER = "#282C33"
    BORDER = "#30343B"
    ACCENT = "#27C5A8"
    ACCENT_HOVER = "#20A98F"
    TEXT = "#F4F5F7"
    TEXT_SECONDARY = "#9297A3"
    TEXT_MUTED = "#666D78"
    SUCCESS = "#36B37E"
    WARNING = "#E5AD55"
    ERROR = "#E05B65"
    # Letterbox behind video (pure black, as required for the movie player).
    VIDEO_BACKGROUND = "#000000"

    # Text drawn on top of the teal accent (dark, as in the screenshots).
    ON_ACCENT = BACKGROUND
    # Soft teal tints built from the palette (selected nav item, synced lyric).
    ACCENT_TINT = blend(ACCENT, SIDEBAR, 0.16)
    ACCENT_TINT_CARD = blend(ACCENT, CARD, 0.14)
    ERROR_TINT = blend(ERROR, CARD, 0.14)
    SUCCESS_TINT = blend(SUCCESS, CARD, 0.14)


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Sizes:
    SIDEBAR_WIDTH = 216
    TOPBAR_HEIGHT = 64
    BUTTON_HEIGHT = 40
    INPUT_HEIGHT = 42
    CARD_RADIUS = 10
    BUTTON_RADIUS = 8
    INPUT_RADIUS = 8
    LYRICS_PANEL_WIDTH = 340
    PLAYER_BAR_HEIGHT = 88
    AUTH_CARD_WIDTH = 440
    WINDOW_WIDTH = 1440
    WINDOW_HEIGHT = 900
    WINDOW_MIN_WIDTH = 1280
    WINDOW_MIN_HEIGHT = 720
    TOAST_WIDTH = 320
    DIALOG_WIDTH = 400
    AVATAR_SIZE = 36
    NAV_ITEM_HEIGHT = 36
    ICON_SIZE = 18
    IMAGE_RADIUS = 8
    CARD_IMAGE_DEFAULT = 140
    CARD_IMAGE_MIN = 96
    CARD_IMAGE_MAX = 230
    POSTER_ASPECT = 1.5
    DETAILS_POSTER_WIDTH = 200
    DETAILS_POSTER_HEIGHT = 300
    BANNER_HEIGHT = 260
    VIDEO_WIDTH = 960
    VIDEO_HEIGHT = 620
    CHIP_BAR_HEIGHT = 30
    GAME_CARD_ASPECT = 0.5625
    GAME_GALLERY_WIDTH = 520
    GAME_GALLERY_HEIGHT = 293
    GAME_THUMB_WIDTH = 120
    GAME_THUMB_HEIGHT = 68
    ROW_THUMB_SIZE = 48
    ROW_THUMB_COMPACT = 40
    ROW_RADIUS = 10
    CHIP_HEIGHT = 20
    HEART_SIZE = 28
    ICON_BUTTON_SIZE = 36
    PLAY_BUTTON_SIZE = 36
    PLAYER_ART_SIZE = 56
    PLAYER_PLAY_SIZE = 44
    LYRICS_ART_SIZE = 64
    VOLUME_SLIDER_WIDTH = 100
    PROGRESS_SLIDER_WIDTH = 440
    SERVICE_BUTTON_WIDTH = 100
    SERVICE_ICON_TILE = 44
    STATE_BOX_HEIGHT = 56


class Fonts:
    # First installed family wins (see presentation/styles/typography.py).
    FAMILIES = ("Inter", "Segoe UI", "Arial")
    SIZE_TITLE = 28
    SIZE_SECTION = 19
    SIZE_CARD = 15
    SIZE_BODY = 13
    SIZE_SMALL = 12
    SIZE_TINY = 11
