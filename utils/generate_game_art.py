"""Generate game-themed placeholder images for Kinetix game cards.

Run once: python utils/generate_game_art.py
Saves PNG files to assets/placeholders/games/
"""
import os
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    raise

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "assets" / "placeholders" / "games"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 320, 180


def _hex(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


TEAL = _hex("#27C5A8")
DARK = _hex("#101114")
CARD_BG = _hex("#191B20")
SURFACE = _hex("#202329")
BORDER = _hex("#30343B")
WHITE = (244, 245, 247)
YELLOW = _hex("#E5AD55")
RED = _hex("#E05B65")
BLUE = _hex("#4A90D9")
GREEN = _hex("#36B37E")
PURPLE = _hex("#9B59B6")
ORANGE = _hex("#E67E22")


def make_base(bg=CARD_BG) -> tuple:
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    return img, d


def add_grid(d: ImageDraw.Draw, color=(40, 44, 51), step=20):
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=color, width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=color, width=1)


def add_label(d: ImageDraw.Draw, text: str, color=WHITE, size=22, y=None):
    if y is None:
        y = H - 36
    # Bold block text
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            d.text((W // 2 + dx, y + dy), text, fill=(0, 0, 0), anchor="mm",
                   font=None)
    d.text((W // 2, y), text, fill=color, anchor="mm")


def add_corner_badge(d: ImageDraw.Draw, text: str, color=TEAL):
    d.rounded_rectangle([W - 76, 8, W - 8, 28], radius=6, fill=color)
    d.text((W - 42, 18), text, fill=DARK, anchor="mm")


# ─────────────────────────── SNAKE ───────────────────────────
def gen_snake():
    img, d = make_base()
    add_grid(d, (25, 28, 34), 20)
    # Snake body segments
    segments = [(5, 4), (6, 4), (7, 4), (7, 5), (7, 6), (6, 6), (5, 6), (5, 7), (5, 8)]
    for i, (gx, gy) in enumerate(segments):
        x0, y0 = gx * 20 + 2, gy * 20 + 2
        x1, y1 = x0 + 15, y0 + 15
        shade = int(220 - i * 12)
        c = (0, min(255, shade), min(255, shade - 40))
        d.rounded_rectangle([x0, y0, x1, y1], radius=3, fill=c)
    # Head
    hx, hy = segments[0]
    x0, y0 = hx * 20 + 2, hy * 20 + 2
    d.rounded_rectangle([x0, y0, x0 + 15, y0 + 15], radius=3, fill=TEAL)
    d.ellipse([x0 + 3, y0 + 3, x0 + 6, y0 + 6], fill=WHITE)
    d.ellipse([x0 + 9, y0 + 3, x0 + 12, y0 + 6], fill=WHITE)
    # Food (apple)
    d.ellipse([11 * 20 + 4, 4 * 20 + 4, 11 * 20 + 15, 4 * 20 + 15], fill=RED)
    # Score
    d.text((12, 12), "SCORE", fill=TEAL)
    d.text((12, 24), "1240", fill=WHITE)
    add_label(d, "NEON SNAKE", TEAL)
    add_corner_badge(d, "ARCADE")
    return img


# ─────────────────────────── PONG ───────────────────────────
def gen_pong():
    img, d = make_base()
    # Center dashes
    for y in range(10, H - 10, 16):
        d.rectangle([W // 2 - 2, y, W // 2 + 2, y + 8], fill=BORDER)
    # Paddles
    d.rounded_rectangle([20, 55, 30, 125], radius=4, fill=TEAL)
    d.rounded_rectangle([W - 30, 40, W - 20, 110], radius=4, fill=RED)
    # Ball
    bx, by = 110, 72
    d.ellipse([bx, by, bx + 14, by + 14], fill=WHITE)
    # Motion trail
    for i in range(1, 5):
        alpha = int(80 - i * 15)
        shade = (alpha, alpha, alpha)
        d.ellipse([bx - i * 14, by + i * 10, bx - i * 14 + 14, by + i * 10 + 14], fill=shade)
    # Scores
    d.text((W // 2 - 40, 20), "5", fill=TEAL, anchor="mm")
    d.text((W // 2 + 40, 20), "3", fill=RED, anchor="mm")
    add_label(d, "PONG DUEL")
    add_corner_badge(d, "ARCADE")
    return img


# ─────────────────────────── BREAKOUT ───────────────────────────
def gen_breakout():
    img, d = make_base()
    colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]
    # Bricks (some already broken)
    skip = {(0, 2), (1, 2), (3, 1), (5, 0), (6, 0), (6, 1)}
    for row in range(4):
        for col in range(8):
            if (col, row) in skip:
                continue
            x0 = 10 + col * 38
            y0 = 20 + row * 24
            d.rounded_rectangle([x0, y0, x0 + 34, y0 + 18], radius=3,
                                 fill=colors[row % len(colors)])
    # Paddle
    d.rounded_rectangle([W // 2 - 36, H - 28, W // 2 + 36, H - 18], radius=4, fill=WHITE)
    # Ball
    bx, by = W // 2 + 20, H // 2 + 20
    d.ellipse([bx, by, bx + 12, by + 12], fill=WHITE)
    # Motion line
    d.line([(bx + 6, by + 6), (bx + 6 - 25, by + 6 + 30)], fill=(180, 180, 180), width=1)
    add_label(d, "BRICK BREAKER")
    add_corner_badge(d, "ARCADE")
    return img


# ─────────────────────────── FLAPPY ───────────────────────────
def gen_flappy():
    img, d = make_base(_hex("#0D1117"))
    # Stars
    import random
    rng = random.Random(42)
    for _ in range(40):
        sx, sy = rng.randint(0, W), rng.randint(0, H)
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=WHITE)
    # Columns (asteroids)
    pairs = [(100, 30, 90), (200, 50, 80), (300, 20, 100)]
    for cx, gap_top, gap_h in pairs:
        d.rectangle([cx, 0, cx + 24, gap_top], fill=BORDER)
        d.rounded_rectangle([cx - 4, gap_top - 12, cx + 28, gap_top], radius=3, fill=SURFACE)
        bot = gap_top + gap_h
        d.rectangle([cx, bot, cx + 24, H], fill=BORDER)
        d.rounded_rectangle([cx - 4, bot, cx + 28, bot + 12], radius=3, fill=SURFACE)
    # Rocket
    rx, ry = 55, 75
    d.polygon([(rx, ry), (rx + 24, ry + 12), (rx, ry + 24)], fill=TEAL)
    d.polygon([(rx - 10, ry + 8), (rx, ry + 12), (rx - 10, ry + 16)], fill=RED)  # flame
    # Score
    d.text((W // 2, 15), "TAP TO THRUST", fill=TEAL, anchor="mm")
    add_label(d, "FLAPPY ROCKET", TEAL)
    add_corner_badge(d, "ARCADE")
    return img


# ─────────────────────────── TIC-TAC-TOE ───────────────────────────
def gen_tictactoe():
    img, d = make_base()
    # Grid
    gx, gy, gs = 70, 20, 44
    lw = 3
    for i in range(1, 3):
        d.rectangle([gx + i * gs, gy, gx + i * gs + lw, gy + 3 * gs], fill=BORDER)
        d.rectangle([gx, gy + i * gs, gx + 3 * gs + lw, gy + i * gs + lw], fill=BORDER)
    # X marks
    def draw_x(col, row):
        cx = gx + col * gs + gs // 2
        cy = gy + row * gs + gs // 2
        pad = 10
        d.line([(cx - pad, cy - pad), (cx + pad, cy + pad)], fill=TEAL, width=4)
        d.line([(cx + pad, cy - pad), (cx - pad, cy + pad)], fill=TEAL, width=4)

    def draw_o(col, row):
        cx = gx + col * gs + gs // 2
        cy = gy + row * gs + gs // 2
        r = 14
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RED, width=4)

    draw_x(0, 0); draw_o(1, 0); draw_x(2, 0)
    draw_o(0, 1); draw_x(1, 1); draw_o(2, 1)
    draw_x(0, 2); draw_o(1, 2)
    # Winning diagonal
    d.line([(gx + gs // 2, gy + gs // 2),
            (gx + 2 * gs + gs // 2, gy + 2 * gs + gs // 2)], fill=YELLOW, width=3)
    d.text((gx + 3 * gs + 24, gy + 44), "X WINS!", fill=TEAL)
    add_label(d, "TIC-TAC-TOE")
    add_corner_badge(d, "ARCADE")
    return img


# ─────────────────────────── BLACKJACK ───────────────────────────
def gen_blackjack():
    img, d = make_base(_hex("#0A1A0A"))
    # Green felt
    d.ellipse([40, 20, W - 40, H - 20], fill=_hex("#1A3A1A"))
    # Cards – player hand
    def draw_card(x, y, label, face_down=False):
        d.rounded_rectangle([x, y, x + 48, y + 70], radius=4, fill=WHITE)
        if face_down:
            d.rounded_rectangle([x + 3, y + 3, x + 45, y + 67], radius=3, fill=BLUE)
        else:
            d.text((x + 6, y + 6), label, fill=RED if label[0] in "HD" else DARK)
    draw_card(60, 50, "A♠")
    draw_card(90, 55, "K♥")
    # Dealer
    draw_card(W - 150, 30, "7♦")
    draw_card(W - 120, 35, face_down=True, label="")
    # Score
    d.rounded_rectangle([50, 125, 130, 148], radius=6, fill=TEAL)
    d.text((90, 136), "21 – WIN!", fill=DARK, anchor="mm")
    add_label(d, "BLACKJACK 21", TEAL)
    add_corner_badge(d, "CARDS")
    return img


# ─────────────────────────── HIGH-LOW ───────────────────────────
def gen_highlow():
    img, d = make_base(_hex("#0A100A"))
    d.ellipse([30, 10, W - 30, H - 10], fill=_hex("#1A2A1A"))
    # Center card
    cx = W // 2
    d.rounded_rectangle([cx - 30, 30, cx + 30, 110], radius=5, fill=WHITE)
    d.text((cx, 60), "8♣", fill=DARK, anchor="mm")
    # Arrow up
    d.polygon([(cx + 65, 70), (cx + 85, 50), (cx + 105, 70)], fill=GREEN)
    d.rectangle([cx + 81, 70, cx + 89, 90], fill=GREEN)
    # Arrow down
    d.polygon([(cx - 65, 60), (cx - 85, 80), (cx - 105, 60)], fill=RED)
    d.rectangle([cx - 89, 40, cx - 81, 60], fill=RED)
    d.text((cx + 85, 100), "HIGH", fill=GREEN, anchor="mm")
    d.text((cx - 85, 40), "LOW", fill=RED, anchor="mm")
    add_label(d, "HIGH-LOW CARDS")
    add_corner_badge(d, "CARDS")
    return img


# ─────────────────────────── WORD GUESS ───────────────────────────
def gen_word_guess():
    img, d = make_base()
    # 5x6 grid of letter tiles
    letters = [
        [("C", "gray"), ("R", "gray"), ("A", "gray"), ("N", "gray"), ("E", "green")],
        [("S", "gray"), ("T", "gray"), ("A", "gray"), ("L", "yellow"), ("E", "green")],
        [("T", "gray"), ("A", "yellow"), ("B", "gray"), ("L", "yellow"), ("E", "green")],
        [("F", "gray"), ("A", "yellow"), ("B", "gray"), ("L", "gray"), ("E", "green")],
        [("F", "gray"), ("A", "yellow"), ("B", "gray"), ("L", "gray"), ("E", "green")],
        [("T", "green"), ("A", "green"), ("B", "green"), ("L", "green"), ("E", "green")],
    ]
    color_map = {"gray": SURFACE, "yellow": YELLOW, "green": GREEN}
    tile_w, tile_h = 42, 28
    ox = (W - 5 * tile_w - 4 * 4) // 2
    oy = 8
    for row_i, row in enumerate(letters[:5]):
        for col_i, (letter, state) in enumerate(row):
            x0 = ox + col_i * (tile_w + 4)
            y0 = oy + row_i * (tile_h + 4)
            d.rounded_rectangle([x0, y0, x0 + tile_w, y0 + tile_h], radius=4,
                                 fill=color_map[state], outline=BORDER, width=1)
            d.text((x0 + tile_w // 2, y0 + tile_h // 2), letter, fill=WHITE, anchor="mm")
    # Answer row
    for col_i, (letter, _) in enumerate(letters[5]):
        x0 = ox + col_i * (tile_w + 4)
        y0 = oy + 5 * (tile_h + 4)
        d.rounded_rectangle([x0, y0, x0 + tile_w, y0 + tile_h], radius=4, fill=GREEN)
        d.text((x0 + tile_w // 2, y0 + tile_h // 2), letter, fill=DARK, anchor="mm")
    add_label(d, "5-LETTER WORD GUESS", TEAL)
    add_corner_badge(d, "WORDS")
    return img


# ─────────────────────────── WORD SCRAMBLE ───────────────────────────
def gen_word_scramble():
    img, d = make_base()
    # Scrambled tiles
    scrambled = "TBELA"
    tile_w = 36
    ox = W // 2 - len(scrambled) * (tile_w + 6) // 2
    for i, ch in enumerate(scrambled):
        x0 = ox + i * (tile_w + 6)
        shade = [TEAL, YELLOW, RED, BLUE, GREEN][i % 5]
        d.rounded_rectangle([x0, 25, x0 + tile_w, 65], radius=5, fill=shade)
        d.text((x0 + tile_w // 2, 45), ch, fill=DARK, anchor="mm")
    # Arrow pointing down
    ax = W // 2
    d.polygon([(ax - 12, 78), (ax + 12, 78), (ax, 94)], fill=WHITE)
    # Answer
    answer = "TABLE"
    ox2 = W // 2 - len(answer) * (tile_w + 6) // 2
    for i, ch in enumerate(answer):
        x0 = ox2 + i * (tile_w + 6)
        d.rounded_rectangle([x0, 100, x0 + tile_w, 140], radius=5, fill=SURFACE,
                             outline=TEAL, width=2)
        d.text((x0 + tile_w // 2, 120), ch, fill=TEAL, anchor="mm")
    add_label(d, "WORD SCRAMBLE")
    add_corner_badge(d, "WORDS")
    return img


# ─────────────────────────── TRIVIA (generic) ───────────────────────────
def gen_trivia(label: str, accent=TEAL, badge="TRIVIA"):
    img, d = make_base()
    # Question bubble
    d.rounded_rectangle([20, 15, W - 20, 65], radius=10, fill=SURFACE, outline=accent, width=2)
    d.text((W // 2, 40), "?  Which came first?", fill=WHITE, anchor="mm")
    # Answer buttons
    answers = [("A) Pong", GREEN), ("B) Pac-Man", BORDER),
               ("C) Space Invaders", BORDER), ("D) Tetris", BORDER)]
    for i, (text, color) in enumerate(answers):
        col = i % 2
        row = i // 2
        x0 = 20 + col * (W // 2 - 25)
        y0 = 80 + row * 42
        d.rounded_rectangle([x0, y0, x0 + W // 2 - 30, y0 + 32], radius=6,
                             fill=color, outline=accent if color == GREEN else BORDER, width=1)
        d.text((x0 + (W // 2 - 30) // 2, y0 + 16), text, fill=WHITE, anchor="mm")
    # Timer indicator
    d.arc([W - 50, 15, W - 10, 55], start=0, end=252, fill=accent, width=5)
    d.text((W - 30, 35), "14s", fill=accent, anchor="mm")
    add_label(d, label.upper()[:22], accent)
    add_corner_badge(d, badge, accent)
    return img


# ─────────────────────────── SAVE ALL ───────────────────────────
GAMES = {
    "arcade_snake": gen_snake,
    "arcade_pong": gen_pong,
    "arcade_breakout": gen_breakout,
    "arcade_flappy": gen_flappy,
    "arcade_tictactoe": gen_tictactoe,
    "cards_blackjack": gen_blackjack,
    "cards_highlow": gen_highlow,
    "words_guess": gen_word_guess,
    "words_scramble": gen_word_scramble,
}

if __name__ == "__main__":
    for name, fn in GAMES.items():
        path = OUT_DIR / f"{name}.png"
        fn().save(str(path), "PNG")
        print(f"  saved {path.name}")

    # Trivia categories with custom accent colors
    trivia_map = [
        ("trivia_videogames", "Video Games Trivia", TEAL),
        ("trivia_tech", "Computers & Tech", BLUE),
        ("trivia_movies", "Movies & Film", RED),
        ("trivia_music", "Music Trivia", PURPLE),
        ("trivia_general", "General Knowledge", YELLOW),
        ("trivia_sports", "Sports Trivia", GREEN),
        ("trivia_science", "Science Trivia", _hex("#00BCD4")),
        ("trivia_history", "History Trivia", ORANGE),
    ]
    for name, label, accent in trivia_map:
        path = OUT_DIR / f"{name}.png"
        gen_trivia(label, accent).save(str(path), "PNG")
        print(f"  saved {path.name}")

    print("Done. All game art saved to", OUT_DIR)
