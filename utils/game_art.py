"""Generate game-themed PNG thumbnails on first run and cache them in assets/placeholders/games/.

Called automatically by the GameService if the files are not found.
Only uses stdlib + Pillow (already in requirements.txt).
"""
import math
from pathlib import Path
from typing import Callable, Tuple

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None  # type: ignore

W, H = 320, 180

_ROOT = Path(__file__).parent.parent
_OUT = _ROOT / "assets" / "placeholders" / "games"


def _hex(c: str) -> Tuple[int, int, int]:
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


TEAL    = _hex("#27C5A8")
DARK    = _hex("#101114")
CARD_BG = _hex("#191B20")
SURFACE = _hex("#202329")
BORDER  = _hex("#30343B")
WHITE   = _hex("#F4F5F7")
YELLOW  = _hex("#E5AD55")
RED     = _hex("#E05B65")
BLUE    = _hex("#4A90D9")
GREEN   = _hex("#36B37E")
PURPLE  = _hex("#9B59B6")
ORANGE  = _hex("#E67E22")


def _base(bg=CARD_BG):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    return img, d


def _grid(d, color=(35, 39, 46), step=20):
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=color, width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=color, width=1)


def _label(d, text, color=WHITE, y=None):
    y = y or H - 24
    # shadow
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            d.text((W // 2 + ox, y + oy), text, fill=DARK, anchor="mm")
    d.text((W // 2, y), text, fill=color, anchor="mm")


def _badge(d, text, color=TEAL):
    d.rounded_rectangle([W - 76, 6, W - 6, 24], radius=5, fill=color)
    d.text((W - 41, 15), text, fill=DARK, anchor="mm")


# ─── Snake ───────────────────────────────────────────────────────────────────
def _snake():
    img, d = _base()
    _grid(d)
    segs = [(5,4),(6,4),(7,4),(7,5),(7,6),(6,6),(5,6),(5,7),(5,8)]
    for i,(gx,gy) in enumerate(segs):
        shade = max(80, 220 - i*16)
        c = (0, shade, max(0, shade-40))
        x,y = gx*20+2, gy*20+2
        d.rounded_rectangle([x,y,x+15,y+15], radius=3, fill=c)
    hx,hy = segs[0]; x,y = hx*20+2, hy*20+2
    d.rounded_rectangle([x,y,x+15,y+15], radius=3, fill=TEAL)
    d.ellipse([x+3,y+3,x+6,y+6], fill=WHITE)
    d.ellipse([x+9,y+3,x+12,y+6], fill=WHITE)
    d.ellipse([11*20+4,4*20+4,11*20+15,4*20+15], fill=RED)
    d.text((12,12), "SCORE", fill=TEAL)
    d.text((12,24), "1240",  fill=WHITE)
    _label(d, "NEON SNAKE", TEAL)
    _badge(d, "ARCADE")
    return img


# ─── Pong ────────────────────────────────────────────────────────────────────
def _pong():
    img, d = _base()
    for y in range(10, H-10, 16):
        d.rectangle([W//2-2,y,W//2+2,y+8], fill=BORDER)
    d.rounded_rectangle([18,55,30,125], radius=4, fill=TEAL)
    d.rounded_rectangle([W-30,40,W-18,110], radius=4, fill=RED)
    bx,by = 108,70
    for i in range(1,5):
        a=max(0,80-i*18)
        d.ellipse([bx-i*14,by+i*10,bx-i*14+14,by+i*10+14], fill=(a,a,a))
    d.ellipse([bx,by,bx+14,by+14], fill=WHITE)
    d.text((W//2-40,20), "5", fill=TEAL, anchor="mm")
    d.text((W//2+40,20), "3", fill=RED,  anchor="mm")
    _label(d, "PONG DUEL")
    _badge(d, "ARCADE")
    return img


# ─── Breakout ────────────────────────────────────────────────────────────────
def _breakout():
    img, d = _base()
    cols = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]
    skip = {(0,2),(1,2),(3,1),(5,0),(6,0),(6,1)}
    for row in range(4):
        for col in range(8):
            if (col,row) in skip:
                continue
            x0,y0 = 10+col*38, 20+row*24
            d.rounded_rectangle([x0,y0,x0+34,y0+18], radius=3, fill=cols[row%len(cols)])
    d.rounded_rectangle([W//2-36,H-28,W//2+36,H-18], radius=4, fill=WHITE)
    bx,by = W//2+20, H//2+20
    d.line([(bx+6,by+6),(bx+6-25,by+6+30)], fill=(180,180,180), width=1)
    d.ellipse([bx,by,bx+12,by+12], fill=WHITE)
    _label(d, "BRICK BREAKER")
    _badge(d, "ARCADE")
    return img


# ─── Flappy ──────────────────────────────────────────────────────────────────
def _flappy():
    import random
    img, d = _base(_hex("#0D1117"))
    rng = random.Random(42)
    for _ in range(40):
        sx,sy = rng.randint(0,W), rng.randint(0,H)
        d.ellipse([sx,sy,sx+2,sy+2], fill=WHITE)
    for cx,gt,gh in [(100,30,90),(200,50,80),(300,20,100)]:
        d.rectangle([cx,0,cx+24,gt], fill=BORDER)
        d.rounded_rectangle([cx-4,gt-12,cx+28,gt], radius=3, fill=SURFACE)
        bot=gt+gh
        d.rectangle([cx,bot,cx+24,H], fill=BORDER)
        d.rounded_rectangle([cx-4,bot,cx+28,bot+12], radius=3, fill=SURFACE)
    rx,ry = 55,75
    d.polygon([(rx,ry),(rx+24,ry+12),(rx,ry+24)], fill=TEAL)
    d.polygon([(rx-10,ry+8),(rx,ry+12),(rx-10,ry+16)], fill=RED)
    d.text((W//2,15), "TAP TO THRUST", fill=TEAL, anchor="mm")
    _label(d, "FLAPPY ROCKET", TEAL)
    _badge(d, "ARCADE")
    return img


# ─── Tic-Tac-Toe ─────────────────────────────────────────────────────────────
def _tictactoe():
    img, d = _base()
    gx,gy,gs = 70,20,44
    for i in range(1,3):
        d.rectangle([gx+i*gs,gy,gx+i*gs+3,gy+3*gs], fill=BORDER)
        d.rectangle([gx,gy+i*gs,gx+3*gs+3,gy+i*gs+3], fill=BORDER)

    def X(c,r):
        cx=gx+c*gs+gs//2; cy=gy+r*gs+gs//2; p=10
        d.line([(cx-p,cy-p),(cx+p,cy+p)], fill=TEAL, width=4)
        d.line([(cx+p,cy-p),(cx-p,cy+p)], fill=TEAL, width=4)

    def O(c,r):
        cx=gx+c*gs+gs//2; cy=gy+r*gs+gs//2; r2=14
        d.ellipse([cx-r2,cy-r2,cx+r2,cy+r2], outline=RED, width=4)

    X(0,0); O(1,0); X(2,0)
    O(0,1); X(1,1); O(2,1)
    X(0,2); O(1,2)
    d.line([(gx+gs//2,gy+gs//2),(gx+2*gs+gs//2,gy+2*gs+gs//2)], fill=YELLOW, width=3)
    d.text((gx+3*gs+22, gy+44), "X WINS!", fill=TEAL)
    _label(d, "TIC-TAC-TOE")
    _badge(d, "ARCADE")
    return img


# ─── Blackjack ───────────────────────────────────────────────────────────────
def _blackjack():
    img, d = _base(_hex("#0A1A0A"))
    d.ellipse([40,20,W-40,H-20], fill=_hex("#1A3A1A"))

    def card(x,y,label,face_down=False):
        d.rounded_rectangle([x,y,x+48,y+70], radius=4, fill=WHITE)
        if face_down:
            d.rounded_rectangle([x+3,y+3,x+45,y+67], radius=3, fill=BLUE)
        else:
            fc = RED if label and label[0] in "HD" else DARK
            d.text((x+6,y+6), label or "", fill=fc)

    card(60,50,"A\u2660"); card(90,55,"K\u2665")
    card(W-150,30,"7\u2666"); card(W-120,35,face_down=True,label="")
    d.rounded_rectangle([50,125,130,148], radius=6, fill=TEAL)
    d.text((90,136), "21 - WIN!", fill=DARK, anchor="mm")
    _label(d, "BLACKJACK 21", TEAL)
    _badge(d, "CARDS")
    return img


# ─── High-Low ────────────────────────────────────────────────────────────────
def _highlow():
    img, d = _base(_hex("#0A100A"))
    d.ellipse([30,10,W-30,H-10], fill=_hex("#1A2A1A"))
    cx = W//2
    d.rounded_rectangle([cx-30,30,cx+30,110], radius=5, fill=WHITE)
    d.text((cx,65), "8\u2663", fill=DARK, anchor="mm")
    d.polygon([(cx+65,70),(cx+85,50),(cx+105,70)], fill=GREEN)
    d.rectangle([cx+81,70,cx+89,90], fill=GREEN)
    d.polygon([(cx-65,60),(cx-85,80),(cx-105,60)], fill=RED)
    d.rectangle([cx-89,40,cx-81,60], fill=RED)
    d.text((cx+85,100), "HIGH", fill=GREEN, anchor="mm")
    d.text((cx-85,40), "LOW",  fill=RED,   anchor="mm")
    _label(d, "HIGH-LOW CARDS")
    _badge(d, "CARDS")
    return img


# ─── Word Guess ──────────────────────────────────────────────────────────────
def _word_guess():
    img, d = _base()
    rows = [
        [("C","s"),("R","s"),("A","s"),("N","s"),("E","g")],
        [("S","s"),("T","s"),("A","s"),("L","y"),("E","g")],
        [("T","s"),("A","y"),("B","s"),("L","y"),("E","g")],
        [("F","s"),("A","y"),("B","s"),("L","s"),("E","g")],
        [("T","g"),("A","g"),("B","g"),("L","g"),("E","g")],
    ]
    cm = {"s":SURFACE,"y":YELLOW,"g":GREEN}
    tw,th = 44,30
    ox = (W - 5*(tw+4)) // 2; oy = 10
    for ri,row in enumerate(rows):
        for ci,(ch,st) in enumerate(row):
            x0=ox+ci*(tw+4); y0=oy+ri*(th+4)
            d.rounded_rectangle([x0,y0,x0+tw,y0+th], radius=4,
                                 fill=cm[st], outline=BORDER, width=1)
            fc = DARK if st == "g" else WHITE
            d.text((x0+tw//2,y0+th//2), ch, fill=fc, anchor="mm")
    _label(d, "5-LETTER WORD GUESS", TEAL)
    _badge(d, "WORDS")
    return img


# ─── Word Scramble ───────────────────────────────────────────────────────────
def _word_scramble():
    img, d = _base()
    sc="TBELA"; tw=38
    ox = W//2 - len(sc)*(tw+6)//2
    shades=[TEAL,YELLOW,RED,BLUE,GREEN]
    for i,ch in enumerate(sc):
        x0=ox+i*(tw+6)
        d.rounded_rectangle([x0,25,x0+tw,65], radius=5, fill=shades[i%5])
        d.text((x0+tw//2,45), ch, fill=DARK, anchor="mm")
    ax=W//2
    d.polygon([(ax-12,78),(ax+12,78),(ax,96)], fill=WHITE)
    ans="TABLE"; ox2=W//2-len(ans)*(tw+6)//2
    for i,ch in enumerate(ans):
        x0=ox2+i*(tw+6)
        d.rounded_rectangle([x0,100,x0+tw,140], radius=5, fill=SURFACE,
                             outline=TEAL, width=2)
        d.text((x0+tw//2,120), ch, fill=TEAL, anchor="mm")
    _label(d, "WORD SCRAMBLE")
    _badge(d, "WORDS")
    return img


# ─── Trivia (category-specific) ──────────────────────────────────────────────
_TRIVIA_MOTIFS = ("atom", "globe", "film", "music", "gamepad", "book", "trophy", "code", "star", "paw")

_TRIVIA_PROFILES = {
    9:  (TEAL,   "General Knowledge",   "Capital of Australia?",    ("Canberra", "Sydney", "Melbourne", "Perth"),        "globe"),
    10: (ORANGE, "Books & Literature",    "Author of 1984?",          ("Orwell", "Huxley", "Bradbury", "Wells"),         "book"),
    11: (RED,    "Film & Cinema",         "Best Picture 2020?",       ("Parasite", "1917", "Joker", "Ford v Ferrari"),   "film"),
    12: (PURPLE, "Music Trivia",          "Queen lead vocalist?",     ("F. Mercury", "B. May", "R. Taylor", "J. Deacon"), "music"),
    13: (ORANGE, "Musicals & Theatre",    "Phantom composer?",        ("A.L. Webber", "Sondheim", "Lin-Manuel", "Menken"), "music"),
    14: (BLUE,   "Television",            "Breaking Bad city?",       ("Albuquerque", "Phoenix", "Austin", "Denver"),    "film"),
    15: (TEAL,   "Video Games Trivia",    "Which came first?",        ("Pong", "Pac-Man", "Tetris", "Mario"),            "gamepad"),
    16: (YELLOW, "Board Games",           "Chess total squares?",     ("64", "48", "72", "81"),                          "trophy"),
    17: (GREEN,  "Science & Nature",      "Symbol for Gold?",         ("Au", "Ag", "Fe", "Gd"),                          "atom"),
    18: (BLUE,   "Computers & Tech",      "HTTP 404 means?",          ("Not Found", "OK", "Timeout", "Denied"),          "code"),
    19: (PURPLE, "Mathematics",           "Value of Pi (approx)?",    ("3.1416", "2.7182", "1.6180", "1.4142"),          "atom"),
    20: (YELLOW, "Mythology",             "Greek god of the sea?",    ("Poseidon", "Zeus", "Hades", "Apollo"),           "star"),
    21: (GREEN,  "Sports",                "Players on soccer team?",  ("11", "9", "10", "12"),                           "trophy"),
    22: (BLUE,   "Geography",             "Largest ocean?",           ("Pacific", "Atlantic", "Indian", "Arctic"),       "globe"),
    23: (ORANGE, "History",               "First moon landing?",      ("1969", "1965", "1971", "1961"),                  "globe"),
    24: (RED,    "Politics",              "UN headquarters city?",    ("New York", "Geneva", "Vienna", "London"),        "globe"),
    25: (PURPLE, "Art & Design",          "Painted Starry Night?",    ("Van Gogh", "Monet", "Picasso", "Da Vinci"),      "star"),
    26: (YELLOW, "Celebrities",           "Iron Man actor?",          ("R. Downey Jr.", "C. Evans", "C. Hemsworth", "M. Ruffalo"), "star"),
    27: (GREEN,  "Animals & Wildlife",    "Fastest land animal?",     ("Cheetah", "Lion", "Gazelle", "Leopard"),         "paw"),
    28: (RED,    "Vehicles",              "F1 tire supplier?",        ("Pirelli", "Michelin", "Goodyear", "Dunlop"),     "code"),
    29: (BLUE,   "Comics & Manga",        "Gotham's protector?",      ("Batman", "Superman", "Flash", "Aquaman"),        "star"),
    30: (TEAL,   "Gadgets & Hardware",    "USB stands for?",          ("Universal Bus", "Unified", "Ultra", "User"),     "code"),
    31: (RED,    "Anime & Manga",         "Spirited Away studio?",    ("Ghibli", "Toei", "Madhouse", "MAPPA"),           "star"),
    32: (YELLOW, "Cartoons & Animation",  "Toy Story studio?",        ("Pixar", "DreamWorks", "Illumination", "Sony"),   "film"),
}


def _draw_motif(d, motif: str, accent) -> None:
    soft = tuple(max(18, c // 4) for c in accent)
    if motif == "atom":
        d.ellipse([230, 18, 304, 92], outline=soft, width=2)
        d.ellipse([246, 34, 288, 76], outline=soft, width=2)
        d.ellipse([262, 50, 272, 60], fill=accent)
    elif motif == "globe":
        d.ellipse([236, 22, 302, 88], outline=soft, width=2)
        d.ellipse([252, 22, 286, 88], outline=soft, width=2)
        d.line([(236, 55), (302, 55)], fill=soft, width=2)
    elif motif == "film":
        d.rounded_rectangle([232, 26, 302, 78], radius=6, outline=soft, width=2)
        for sx in (240, 258, 276, 290):
            d.rectangle([sx, 30, sx + 7, 36], fill=soft)
            d.rectangle([sx, 68, sx + 7, 74], fill=soft)
    elif motif == "music":
        for i, bh in enumerate((18, 34, 24, 42, 28)):
            bx = 236 + i * 13
            d.rounded_rectangle([bx, 76 - bh, bx + 8, 76], radius=3, fill=soft)
    elif motif == "gamepad":
        d.rounded_rectangle([232, 34, 302, 74], radius=14, outline=soft, width=2)
        d.ellipse([282, 46, 289, 53], fill=accent)
        d.ellipse([272, 54, 279, 61], fill=soft)
    elif motif == "book":
        d.rounded_rectangle([238, 24, 296, 80], radius=4, outline=soft, width=2)
        d.line([(267, 26), (267, 78)], fill=soft, width=2)
    elif motif == "trophy":
        d.polygon([(246, 28), (288, 28), (278, 56), (256, 56)], outline=soft, width=2)
        d.rectangle([264, 56, 270, 72], fill=soft)
        d.rectangle([252, 72, 282, 78], fill=soft)
    elif motif == "code":
        d.rounded_rectangle([234, 26, 302, 78], radius=6, outline=soft, width=2)
        d.text((268, 52), "</>", fill=soft, anchor="mm")
    elif motif == "paw":
        d.ellipse([256, 50, 280, 72], fill=soft)
        for px, py in ((248, 38), (260, 32), (274, 32), (286, 38)):
            d.ellipse([px, py, px + 10, py + 12], fill=soft)
    else:
        d.polygon([(268, 24), (276, 46), (298, 46), (280, 60), (286, 82),
                   (268, 68), (250, 82), (256, 60), (238, 46), (260, 46)], outline=soft, width=2)


def _trivia(label: str, accent=TEAL, cat_id: int = 0):
    profile = _TRIVIA_PROFILES.get(cat_id)
    if profile:
        accent, short_label, prompt, choices, motif = profile
    else:
        palette = (TEAL, BLUE, PURPLE, ORANGE, GREEN, RED, YELLOW)
        accent = palette[cat_id % len(palette)]
        short_label = label or "Trivia"
        prompt = f"{short_label[:20]} Challenge"
        choices = ("A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4")
        motif = _TRIVIA_MOTIFS[cat_id % len(_TRIVIA_MOTIFS)]

    bg_tint = tuple(max(16, int(CARD_BG[i] * 0.85 + accent[i] * 0.08)) for i in range(3))
    img, d = _base(bg_tint)
    _draw_motif(d, motif, accent)

    d.rounded_rectangle([16, 16, W - 96, 62], radius=8, fill=SURFACE, outline=accent, width=2)
    d.text((26, 39), f"?  {prompt[:26]}", fill=WHITE, anchor="lm")

    for i, txt in enumerate(choices[:4]):
        col = i % 2
        row = i // 2
        x0 = 16 + col * 146
        y0 = 76 + row * 36
        is_hit = i == (cat_id % 4)
        fill_c = tuple(max(24, c // 2) for c in accent) if is_hit else SURFACE
        d.rounded_rectangle([x0, y0, x0 + 138, y0 + 28], radius=6,
                            fill=fill_c, outline=accent if is_hit else BORDER, width=1)
        d.text((x0 + 69, y0 + 14), txt[:16], fill=WHITE, anchor="mm")

    _label(d, short_label[:24].upper(), accent, y=H - 18)
    _badge(d, "TRIVIA", accent)
    return img


# ─── Public API ──────────────────────────────────────────────────────────────
_GENERATORS = {
    "arcade:snake":    (_snake,  "arcade_snake.png"),
    "arcade:pong":     (_pong,   "arcade_pong.png"),
    "arcade:breakout": (_breakout,"arcade_breakout.png"),
    "arcade:flappy":   (_flappy, "arcade_flappy.png"),
    "arcade:tictactoe":(_tictactoe,"arcade_tictactoe.png"),
    "cards:blackjack": (_blackjack,"cards_blackjack.png"),
    "cards:highlow":   (_highlow,"cards_highlow.png"),
    "word:guess5":     (_word_guess,"words_guess.png"),
    "word:scramble":   (_word_scramble,"words_scramble.png"),
}

_TRIVIA_ACCENTS = {cid: (p[0], p[1]) for cid, p in _TRIVIA_PROFILES.items()}


def game_image_path(game_id: str, title: str = "", category_id: int = 0) -> str:
    """Return a local path to the generated game thumbnail.

    Generates the PNG on first call if Pillow is available; falls back to the
    generic game placeholder otherwise.
    """
    if Image is None:
        return ""  # fall back to placeholder

    _OUT.mkdir(parents=True, exist_ok=True)

    if game_id in _GENERATORS:
        fn, fname = _GENERATORS[game_id]
        path = _OUT / fname
        if not path.exists():
            try:
                fn().save(str(path), "PNG")
            except Exception:
                return ""
        return str(path)

    if game_id.startswith("trivia:"):
        try:
            cat_id = int(game_id.split(":", 1)[1])
        except ValueError:
            cat_id = 0
        fname = f"trivia_v2_{cat_id}.png"
        path = _OUT / fname
        if not path.exists():
            accent, label = _TRIVIA_ACCENTS.get(cat_id, (TEAL, title or "Trivia"))
            try:
                _trivia(label, accent, cat_id=cat_id).save(str(path), "PNG")
            except Exception:
                return ""
        return str(path)

    return ""


def ensure_all() -> None:
    """Pre-generate core game thumbnails. Called once at startup."""
    if Image is None:
        return
    _OUT.mkdir(parents=True, exist_ok=True)
    for game_id, (fn, fname) in _GENERATORS.items():
        path = _OUT / fname
        if not path.exists():
            try:
                fn().save(str(path), "PNG")
            except Exception:
                pass
    for cat_id in (15, 18, 11, 12):
        accent, label = _TRIVIA_ACCENTS[cat_id]
        path = _OUT / f"trivia_v2_{cat_id}.png"
        if not path.exists():
            try:
                _trivia(label, accent, cat_id=cat_id).save(str(path), "PNG")
            except Exception:
                pass
