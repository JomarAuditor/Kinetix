"""Pure-tkinter in-app arcade games embedded inside a CTkFrame.

Each game is a subclass of ArcadeGame which manages a tk.Canvas running
a game loop via after().  All sizes/colors are hard-coded per-game because
the canvas is a raw Tk widget; we keep them in sync with the dark Kinetix
palette by referencing Colors constants as strings at class level.

Games
-----
SnakeGame       — classic snake, WASD / arrow keys
PongGame        — single-player Pong vs simple AI, W/S to move
BreakoutGame    — Breakout / brick breaker, A/D or Left/Right
FlappyGame      — Flappy-bird style tap game, Space to thrust
TicTacToeGame   — Tic-Tac-Toe vs minimax AI, click to place
"""
from __future__ import annotations

import random
import tkinter as tk
from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple

from presentation.styles.colors import Colors

# Canvas palette strings (must be plain Tk color strings)
_BG = Colors.CARD          # "#191B20"
_ACCENT = Colors.ACCENT    # "#27C5A8"
_TEXT = Colors.TEXT        # "#F4F5F7"
_MUTED = Colors.TEXT_MUTED # "#666D78"
_ERR = Colors.ERROR        # "#E05B65"
_BORDER = Colors.BORDER    # "#30343B"
_SURFACE = Colors.SURFACE  # "#202329"


class ArcadeGame(ABC):
    """Base class for every embedded arcade game."""

    FPS: int = 60

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        self._w = width
        self._h = height
        self._running = False
        self._score = 0
        self._on_score_change: Optional[Callable[[int], None]] = None
        self._after_id: Optional[str] = None

        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=_BG,
            highlightthickness=1,
            highlightbackground=_BORDER,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_score_callback(self, cb: Callable[[int], None]) -> None:
        self._on_score_change = cb

    def start(self) -> None:
        """Begin or restart the game loop."""
        self._running = True
        self._score = 0
        self._init()
        self._tick()

    def stop(self) -> None:
        """Halt the game loop without destroying the canvas."""
        self._running = False
        if self._after_id is not None:
            try:
                self.canvas.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001
                pass
            self._after_id = None

    def destroy(self) -> None:
        self.stop()
        try:
            self.canvas.destroy()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _init(self) -> None:
        """Reset all game state; called at start/restart."""

    @abstractmethod
    def _update(self) -> None:
        """Advance game logic by one frame."""

    @abstractmethod
    def _draw(self) -> None:
        """Redraw the entire canvas from current state."""

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self._running:
            return
        self._update()
        self._draw()
        delay = max(1, 1000 // self.FPS)
        try:
            self._after_id = self.canvas.after(delay, self._tick)
        except tk.TclError:
            self._running = False

    def _emit_score(self, value: int) -> None:
        self._score = value
        if self._on_score_change is not None:
            self._on_score_change(value)


# ===========================================================================
# SNAKE
# ===========================================================================

class SnakeGame(ArcadeGame):
    """Classic snake game. WASD or arrow keys to steer."""

    FPS = 12  # snake moves slower than 60fps
    _CELL = 20

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        # Snap to grid
        w = (width // self._CELL) * self._CELL
        h = (height // self._CELL) * self._CELL
        super().__init__(parent, w, h)
        self._cols = w // self._CELL
        self._rows = h // self._CELL
        self._snake: List[Tuple[int, int]] = []
        self._direction = (1, 0)
        self._next_dir = (1, 0)
        self._food: Tuple[int, int] = (0, 0)
        self._dead = False

        self.canvas.bind("<KeyPress>", self._on_key)

    def _on_key(self, event: tk.Event) -> None:  # type: ignore[override]
        mapping = {
            "Up": (0, -1), "w": (0, -1), "W": (0, -1),
            "Down": (0, 1), "s": (0, 1), "S": (0, 1),
            "Left": (-1, 0), "a": (-1, 0), "A": (-1, 0),
            "Right": (1, 0), "d": (1, 0), "D": (1, 0),
        }
        sym = event.keysym
        new = mapping.get(sym)
        if new and (new[0] != -self._direction[0] or new[1] != -self._direction[1]):
            self._next_dir = new
        if sym in ("r", "R") and self._dead:
            self.start()

    def _place_food(self) -> None:
        occupied = set(self._snake)
        empty = [
            (c, r)
            for c in range(self._cols)
            for r in range(self._rows)
            if (c, r) not in occupied
        ]
        self._food = random.choice(empty) if empty else (0, 0)

    def _init(self) -> None:
        cx, cy = self._cols // 2, self._rows // 2
        self._snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self._direction = (1, 0)
        self._next_dir = (1, 0)
        self._dead = False
        self._place_food()

    def _update(self) -> None:
        if self._dead:
            return
        self._direction = self._next_dir
        head = (
            (self._snake[0][0] + self._direction[0]) % self._cols,
            (self._snake[0][1] + self._direction[1]) % self._rows,
        )
        if head in self._snake[:-1]:
            self._dead = True
            return
        self._snake.insert(0, head)
        if head == self._food:
            self._emit_score(self._score + 10)
            self._place_food()
        else:
            self._snake.pop()

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        cell = self._CELL

        # Grid dots
        for col in range(0, self._w, cell * 4):
            for row in range(0, self._h, cell * 4):
                c.create_rectangle(col, row, col + 2, row + 2, fill=_MUTED, outline="")

        # Snake
        for i, (col, row) in enumerate(self._snake):
            x1, y1 = col * cell + 1, row * cell + 1
            x2, y2 = x1 + cell - 2, y1 + cell - 2
            color = _ACCENT if i == 0 else Colors.ACCENT_HOVER
            c.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

        # Food
        fx, fy = self._food
        mx = fx * cell + cell // 2
        my = fy * cell + cell // 2
        r = cell // 2 - 2
        c.create_oval(mx - r, my - r, mx + r, my + r, fill=_ERR, outline="")

        # Score HUD
        c.create_text(8, 8, text=f"Score: {self._score}", fill=_TEXT, anchor="nw",
                      font=("Segoe UI", 12, "bold"))

        if self._dead:
            self._draw_overlay("Game Over!", f"Score: {self._score}  |  Press R to restart")

    def _draw_overlay(self, title: str, sub: str) -> None:
        c = self.canvas
        cx, cy = self._w // 2, self._h // 2
        c.create_rectangle(cx - 170, cy - 60, cx + 170, cy + 60,
                           fill=_SURFACE, outline=_BORDER, width=2)
        c.create_text(cx, cy - 20, text=title, fill=_ACCENT, font=("Segoe UI", 20, "bold"))
        c.create_text(cx, cy + 16, text=sub, fill=_TEXT, font=("Segoe UI", 11))

    def start(self) -> None:
        super().start()
        self.canvas.focus_set()


# ===========================================================================
# PONG
# ===========================================================================

class PongGame(ArcadeGame):
    """Single-player Pong vs a simple AI. W/S or Up/Down to move your paddle."""

    FPS = 60

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        super().__init__(parent, width, height)
        self._py = 0.0        # player paddle y (centre)
        self._ay = 0.0        # AI paddle y
        self._bx = 0.0        # ball x
        self._by = 0.0        # ball y
        self._vx = 0.0        # ball velocity x
        self._vy = 0.0        # ball velocity y
        self._ph = 70         # paddle height
        self._pw = 10         # paddle width
        self._br = 7          # ball radius
        self._dead = False
        self._up = False
        self._down = False

        self.canvas.bind("<KeyPress>", self._on_key)
        self.canvas.bind("<KeyRelease>", self._on_release)

    def _on_key(self, event: tk.Event) -> None:  # type: ignore[override]
        if event.keysym in ("Up", "w", "W"):
            self._up = True
        if event.keysym in ("Down", "s", "S"):
            self._down = True
        if event.keysym in ("r", "R") and self._dead:
            self.start()

    def _on_release(self, event: tk.Event) -> None:
        if event.keysym in ("Up", "w", "W"):
            self._up = False
        if event.keysym in ("Down", "s", "S"):
            self._down = False

    def _init(self) -> None:
        self._py = self._h / 2.0
        self._ay = self._h / 2.0
        self._reset_ball(direction=1)
        self._dead = False

    def _reset_ball(self, direction: int = 1) -> None:
        self._bx = self._w / 2.0
        self._by = self._h / 2.0
        speed = 4.5
        angle = random.uniform(-0.5, 0.5)
        self._vx = direction * speed * (1.0 - abs(angle) * 0.3)
        self._vy = speed * angle

    def _update(self) -> None:
        if self._dead:
            return
        spd = 5.0
        if self._up:
            self._py = max(self._ph / 2, self._py - spd)
        if self._down:
            self._py = min(self._h - self._ph / 2, self._py + spd)

        # AI tracks ball with slight lag
        ai_spd = 3.8
        if self._ay < self._by - 4:
            self._ay = min(self._ay + ai_spd, self._h - self._ph / 2)
        elif self._ay > self._by + 4:
            self._ay = max(self._ay - ai_spd, self._ph / 2)

        # Ball move
        self._bx += self._vx
        self._by += self._vy

        # Wall bounce
        if self._by - self._br < 0:
            self._by = float(self._br)
            self._vy = abs(self._vy)
        elif self._by + self._br > self._h:
            self._by = float(self._h - self._br)
            self._vy = -abs(self._vy)

        # Player paddle (left side, x=28)
        px = 28 + self._pw
        if (self._bx - self._br <= px
                and abs(self._by - self._py) < self._ph / 2 + self._br):
            self._bx = float(px + self._br)
            self._vx = abs(self._vx) * 1.05
            self._vy += (self._by - self._py) * 0.08
            self._emit_score(self._score + 1)

        # AI paddle (right side, x=w-28-pw)
        ax = self._w - 28 - self._pw
        if (self._bx + self._br >= ax
                and abs(self._by - self._ay) < self._ph / 2 + self._br):
            self._bx = float(ax - self._br)
            self._vx = -abs(self._vx) * 1.03
            self._vy += (self._by - self._ay) * 0.06

        # Ball out left -> player lost
        if self._bx < 0:
            self._dead = True

        # Ball out right -> player scored bonus
        if self._bx > self._w:
            self._emit_score(self._score + 5)
            self._reset_ball(direction=-1)

        # Cap speed
        import math
        spd_ball = math.hypot(self._vx, self._vy)
        if spd_ball > 14:
            scale = 14 / spd_ball
            self._vx *= scale
            self._vy *= scale

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")

        # Court divider
        for y in range(0, self._h, 24):
            c.create_rectangle(self._w // 2 - 1, y, self._w // 2 + 1, y + 12,
                               fill=_MUTED, outline="")

        # Player paddle
        c.create_rectangle(
            28, self._py - self._ph / 2,
            28 + self._pw, self._py + self._ph / 2,
            fill=_ACCENT, outline="",
        )
        # AI paddle
        c.create_rectangle(
            self._w - 28 - self._pw, self._ay - self._ph / 2,
            self._w - 28, self._ay + self._ph / 2,
            fill=_ERR, outline="",
        )
        # Ball
        bx, by, br = int(self._bx), int(self._by), self._br
        c.create_oval(bx - br, by - br, bx + br, by + br, fill=_TEXT, outline="")

        # HUD
        c.create_text(8, 8, text=f"Rallies: {self._score}", fill=_TEXT, anchor="nw",
                      font=("Segoe UI", 12, "bold"))
        c.create_text(self._w - 8, 8, text="AI", fill=_ERR, anchor="ne",
                      font=("Segoe UI", 12, "bold"))
        c.create_text(self._w // 2, 8, text="W/S to move", fill=_MUTED, anchor="n",
                      font=("Segoe UI", 10))

        if self._dead:
            self._draw_overlay()

    def _draw_overlay(self) -> None:
        c = self.canvas
        cx, cy = self._w // 2, self._h // 2
        c.create_rectangle(cx - 170, cy - 60, cx + 170, cy + 60,
                           fill=_SURFACE, outline=_BORDER, width=2)
        c.create_text(cx, cy - 20, text="Ball Out!", fill=_ERR, font=("Segoe UI", 20, "bold"))
        c.create_text(cx, cy + 16, text=f"Rallies: {self._score}  |  Press R to restart",
                      fill=_TEXT, font=("Segoe UI", 11))

    def start(self) -> None:
        super().start()
        self.canvas.focus_set()


# ===========================================================================
# BREAKOUT
# ===========================================================================

class BreakoutGame(ArcadeGame):
    """Breakout / brick breaker. Left/Right or A/D to move paddle."""

    FPS = 60
    _ROWS = 5
    _COLS = 10
    _BRICK_H = 22
    _BRICK_PAD = 3
    _PADDLE_H = 12
    _BALL_R = 7

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        super().__init__(parent, width, height)
        self._bricks: List[List[bool]] = []
        self._brick_colors: List[List[str]] = []
        self._paddle_x = 0.0
        self._pw = 100
        self._bx = 0.0
        self._by = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._launched = False
        self._dead = False
        self._win = False
        self._left = False
        self._right = False
        self._level = 1

        self.canvas.bind("<KeyPress>", self._on_key)
        self.canvas.bind("<KeyRelease>", self._on_release)

    def _on_key(self, event: tk.Event) -> None:  # type: ignore[override]
        sym = event.keysym
        if sym in ("Left", "a", "A"):
            self._left = True
        if sym in ("Right", "d", "D"):
            self._right = True
        if sym == "space" and not self._launched and not self._dead:
            self._launch_ball()
        if sym in ("r", "R") and (self._dead or self._win):
            self._level = 1
            self.start()

    def _on_release(self, event: tk.Event) -> None:
        if event.keysym in ("Left", "a", "A"):
            self._left = False
        if event.keysym in ("Right", "d", "D"):
            self._right = False

    def _init(self) -> None:
        self._paddle_x = self._w / 2.0
        self._reset_bricks()
        self._reset_ball()
        self._launched = False
        self._dead = False
        self._win = False

    def _reset_bricks(self) -> None:
        row_colors = [_ACCENT, Colors.WARNING, Colors.SUCCESS, Colors.TEXT_SECONDARY, Colors.ERROR]
        self._bricks = [[True] * self._COLS for _ in range(self._ROWS)]
        self._brick_colors = [
            [row_colors[r % len(row_colors)]] * self._COLS
            for r in range(self._ROWS)
        ]

    def _reset_ball(self) -> None:
        self._bx = float(self._paddle_x)
        self._by = float(self._h - 60)
        self._vx = 0.0
        self._vy = 0.0

    def _launch_ball(self) -> None:
        speed = 5.0 + self._level * 0.5
        self._vx = random.choice([-1, 1]) * speed * 0.6
        self._vy = -speed
        self._launched = True

    def _brick_rect(self, r: int, c: int) -> Tuple[float, float, float, float]:
        top_y = 50
        bw = (self._w - self._BRICK_PAD * (self._COLS + 1)) / self._COLS
        bh = self._BRICK_H
        x1 = self._BRICK_PAD + c * (bw + self._BRICK_PAD)
        y1 = top_y + r * (bh + self._BRICK_PAD)
        return x1, y1, x1 + bw, y1 + bh

    def _update(self) -> None:
        if self._dead or self._win:
            return

        spd = 6.0
        if self._left:
            self._paddle_x = max(self._pw / 2, self._paddle_x - spd)
        if self._right:
            self._paddle_x = min(self._w - self._pw / 2, self._paddle_x + spd)

        if not self._launched:
            self._bx = float(self._paddle_x)
            return

        self._bx += self._vx
        self._by += self._vy
        br = self._BALL_R

        # Wall bounces
        if self._bx - br < 0:
            self._bx = float(br)
            self._vx = abs(self._vx)
        elif self._bx + br > self._w:
            self._bx = float(self._w - br)
            self._vx = -abs(self._vx)
        if self._by - br < 0:
            self._by = float(br)
            self._vy = abs(self._vy)

        # Paddle bounce
        py = self._h - 40
        if (self._by + br >= py
                and abs(self._bx - self._paddle_x) <= self._pw / 2):
            self._by = float(py - br)
            # Add spin based on hit position
            offset = (self._bx - self._paddle_x) / (self._pw / 2)
            self._vx += offset * 2.5
            self._vy = -abs(self._vy)

        # Ball out
        if self._by > self._h:
            self._dead = True
            return

        # Brick collision
        for r in range(self._ROWS):
            for c in range(self._COLS):
                if not self._bricks[r][c]:
                    continue
                x1, y1, x2, y2 = self._brick_rect(r, c)
                if x1 - br < self._bx < x2 + br and y1 - br < self._by < y2 + br:
                    self._bricks[r][c] = False
                    self._emit_score(self._score + 10 * self._level)
                    # Determine which side was hit
                    if abs(self._by - y1) < br or abs(self._by - y2) < br:
                        self._vy = -self._vy
                    else:
                        self._vx = -self._vx
                    break
            else:
                continue
            break

        # Win check
        if all(not b for row in self._bricks for b in row):
            self._level += 1
            self._emit_score(self._score + 100 * self._level)
            self._win = True

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")

        # Bricks
        for r in range(self._ROWS):
            for col in range(self._COLS):
                if not self._bricks[r][col]:
                    continue
                x1, y1, x2, y2 = self._brick_rect(r, col)
                color = self._brick_colors[r][col]
                c.create_rectangle(x1, y1, x2, y2, fill=color, outline=_BG, width=2)

        # Paddle
        py = self._h - 40
        c.create_rectangle(
            self._paddle_x - self._pw / 2, py,
            self._paddle_x + self._pw / 2, py + self._PADDLE_H,
            fill=_ACCENT, outline="",
        )

        # Ball
        br = self._BALL_R
        c.create_oval(
            self._bx - br, self._by - br,
            self._bx + br, self._by + br,
            fill=_TEXT, outline="",
        )

        # HUD
        c.create_text(8, 8, text=f"Score: {self._score}", fill=_TEXT, anchor="nw",
                      font=("Segoe UI", 12, "bold"))
        c.create_text(self._w - 8, 8, text=f"Level: {self._level}", fill=_ACCENT, anchor="ne",
                      font=("Segoe UI", 12, "bold"))

        if not self._launched and not self._dead and not self._win:
            c.create_text(self._w // 2, self._h - 20, fill=_MUTED, anchor="s",
                          text="A/D to move  |  Space to launch",
                          font=("Segoe UI", 11))

        if self._dead:
            self._draw_overlay("Ball Lost!", f"Score: {self._score}  |  R to restart")
        elif self._win:
            self._draw_overlay(f"Level {self._level - 1} Clear!", "R for next level")

    def _draw_overlay(self, title: str, sub: str) -> None:
        c = self.canvas
        cx, cy = self._w // 2, self._h // 2
        c.create_rectangle(cx - 170, cy - 60, cx + 170, cy + 60,
                           fill=_SURFACE, outline=_BORDER, width=2)
        c.create_text(cx, cy - 20, text=title, fill=_ACCENT, font=("Segoe UI", 20, "bold"))
        c.create_text(cx, cy + 16, text=sub, fill=_TEXT, font=("Segoe UI", 11))

    def start(self) -> None:
        super().start()
        self.canvas.focus_set()


# ===========================================================================
# FLAPPY ROCKET
# ===========================================================================

class FlappyGame(ArcadeGame):
    """Flappy-bird style. Space or click to thrust."""

    FPS = 60
    _GAP = 160
    _PIPE_W = 48
    _PIPE_SPEED = 3.0
    _GRAVITY = 0.35
    _THRUST = -7.0

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        super().__init__(parent, width, height)
        self._ry = 0.0        # rocket y
        self._vel = 0.0       # rocket vertical velocity
        self._pipes: List[Tuple[float, float]] = []  # (x, gap_top_y)
        self._dead = False
        self._started = False

        self.canvas.bind("<KeyPress>", self._on_key)
        self.canvas.bind("<Button-1>", self._on_click)

    def _on_key(self, event: tk.Event) -> None:  # type: ignore[override]
        if event.keysym == "space":
            if self._dead:
                self.start()
            else:
                self._thrust()
        if event.keysym in ("r", "R"):
            self.start()

    def _on_click(self, _event: tk.Event) -> None:
        if self._dead:
            self.start()
        else:
            self._thrust()

    def _thrust(self) -> None:
        if not self._started:
            self._started = True
        self._vel = self._THRUST

    def _init(self) -> None:
        self._ry = float(self._h // 2)
        self._vel = 0.0
        self._pipes = []
        self._dead = False
        self._started = False
        # Seed first pipe offscreen
        self._pipes.append((float(self._w + 100), random.uniform(80, self._h - 80 - self._GAP)))

    def _update(self) -> None:
        if self._dead or not self._started:
            return

        # Gravity
        self._vel += self._GRAVITY
        self._ry += self._vel

        # Ceiling / floor
        if self._ry < 10 or self._ry > self._h - 10:
            self._dead = True
            return

        # Move pipes
        new_pipes = []
        for x, top in self._pipes:
            nx = x - self._PIPE_SPEED
            if nx < -self._PIPE_W:
                # Passed: score and spawn next
                self._emit_score(self._score + 1)
                new_pipes.append((float(self._w + 50),
                                  random.uniform(80, self._h - 80 - self._GAP)))
            else:
                new_pipes.append((nx, top))
        self._pipes = new_pipes

        # Spawn additional pipes when only 1 on screen
        if len(self._pipes) < 2:
            last_x = max(p[0] for p in self._pipes)
            if last_x < self._w - 220:
                self._pipes.append((last_x + 260,
                                    random.uniform(80, self._h - 80 - self._GAP)))

        # Collision with pipes
        rx = 60
        for x, top in self._pipes:
            bot = top + self._GAP
            if x < rx + 16 < x + self._PIPE_W:
                if self._ry < top + 16 or self._ry > bot - 16:
                    self._dead = True
                    return

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")

        # Starfield (static seed for speed)
        rng = random.Random(42)
        for _ in range(60):
            sx = rng.randint(0, self._w)
            sy = rng.randint(0, self._h)
            c.create_oval(sx, sy, sx + 1, sy + 1, fill=_MUTED, outline="")

        # Pipes
        for x, top in self._pipes:
            # Top pipe
            c.create_rectangle(x, 0, x + self._PIPE_W, top, fill=_BORDER, outline=_MUTED)
            c.create_rectangle(x - 4, top - 20, x + self._PIPE_W + 4, top,
                               fill=Colors.TEXT_MUTED, outline="")
            # Bottom pipe
            bot = top + self._GAP
            c.create_rectangle(x, bot, x + self._PIPE_W, self._h, fill=_BORDER, outline=_MUTED)
            c.create_rectangle(x - 4, bot, x + self._PIPE_W + 4, bot + 20,
                               fill=Colors.TEXT_MUTED, outline="")

        # Rocket body
        ry = int(self._ry)
        rx = 60
        c.create_polygon(
            rx + 20, ry,
            rx - 10, ry + 10,
            rx - 10, ry - 10,
            fill=_ACCENT, outline=Colors.ACCENT_HOVER, width=1,
        )
        # Flame
        if self._vel < 0:
            c.create_polygon(
                rx - 10, ry + 5,
                rx - 10, ry - 5,
                rx - 24, ry,
                fill=Colors.WARNING, outline="",
            )

        # HUD
        c.create_text(8, 8, text=f"Score: {self._score}", fill=_TEXT, anchor="nw",
                      font=("Segoe UI", 12, "bold"))

        if not self._started:
            c.create_text(self._w // 2, self._h // 2 + 40,
                          text="Click or Space to start", fill=_MUTED, anchor="center",
                          font=("Segoe UI", 13))

        if self._dead:
            cx, cy = self._w // 2, self._h // 2
            c.create_rectangle(cx - 170, cy - 60, cx + 170, cy + 60,
                               fill=_SURFACE, outline=_BORDER, width=2)
            c.create_text(cx, cy - 20, text="Crashed!", fill=_ERR, font=("Segoe UI", 20, "bold"))
            c.create_text(cx, cy + 16, text=f"Score: {self._score}  |  Click to restart",
                          fill=_TEXT, font=("Segoe UI", 11))

    def start(self) -> None:
        super().start()
        self.canvas.focus_set()


# ===========================================================================
# TIC-TAC-TOE
# ===========================================================================

class TicTacToeGame(ArcadeGame):
    """Tic-Tac-Toe vs minimax AI. Click a cell to play."""

    FPS = 10  # low FPS; mostly event-driven

    _EMPTY = 0
    _PLAYER = 1
    _AI = 2

    def __init__(self, parent: tk.Widget, width: int = 640, height: int = 420) -> None:
        super().__init__(parent, width, height)
        self._board: List[int] = [self._EMPTY] * 9
        self._turn = self._PLAYER
        self._status = "play"  # "play" | "player_win" | "ai_win" | "draw"
        self._wins = 0
        self._losses = 0
        self._draws = 0

        self.canvas.bind("<Button-1>", self._on_click)

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[override]
        if self._status != "play" or self._turn != self._PLAYER:
            if self._status != "play":
                self._init()
                self._draw()
            return
        cx, cy = self._cell_origin()
        cell_size = self._cell_size()
        col = int((event.x - cx) // cell_size)
        row = int((event.y - cy) // cell_size)
        if 0 <= row <= 2 and 0 <= col <= 2:
            idx = row * 3 + col
            if self._board[idx] == self._EMPTY:
                self._make_move(idx, self._PLAYER)

    def _cell_size(self) -> int:
        return min(self._w, self._h) * 55 // 100

    def _cell_origin(self) -> Tuple[int, int]:
        s = self._cell_size()
        return (self._w - s) // 2, (self._h - s) // 2

    def _init(self) -> None:
        self._board = [self._EMPTY] * 9
        self._turn = self._PLAYER
        self._status = "play"

    def _make_move(self, idx: int, who: int) -> None:
        self._board[idx] = who
        winner = self._check_winner()
        if winner == self._PLAYER:
            self._wins += 1
            self._emit_score(self._score + 10)
            self._status = "player_win"
        elif winner == self._AI:
            self._losses += 1
            self._status = "ai_win"
        elif self._EMPTY not in self._board:
            self._draws += 1
            self._status = "draw"
        else:
            self._turn = self._AI if who == self._PLAYER else self._PLAYER
            if self._turn == self._AI:
                self.canvas.after(300, self._ai_move)

    def _ai_move(self) -> None:
        if self._status != "play":
            return
        idx = self._best_move()
        self._make_move(idx, self._AI)
        self._draw()

    def _best_move(self) -> int:
        best_val = -1000
        best_idx = -1
        for i in range(9):
            if self._board[i] == self._EMPTY:
                self._board[i] = self._AI
                val = self._minimax(0, False)
                self._board[i] = self._EMPTY
                if val > best_val:
                    best_val = val
                    best_idx = i
        return best_idx

    def _minimax(self, depth: int, maximizing: bool) -> int:
        winner = self._check_winner()
        if winner == self._AI:
            return 10 - depth
        if winner == self._PLAYER:
            return depth - 10
        if self._EMPTY not in self._board:
            return 0
        if maximizing:
            best = -1000
            for i in range(9):
                if self._board[i] == self._EMPTY:
                    self._board[i] = self._AI
                    best = max(best, self._minimax(depth + 1, False))
                    self._board[i] = self._EMPTY
            return best
        else:
            best = 1000
            for i in range(9):
                if self._board[i] == self._EMPTY:
                    self._board[i] = self._PLAYER
                    best = min(best, self._minimax(depth + 1, True))
                    self._board[i] = self._EMPTY
            return best

    _LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
              (0, 3, 6), (1, 4, 7), (2, 5, 8),
              (0, 4, 8), (2, 4, 6)]

    def _check_winner(self) -> int:
        for a, b, cc in self._LINES:
            if self._board[a] != self._EMPTY and self._board[a] == self._board[b] == self._board[cc]:
                return self._board[a]
        return self._EMPTY

    def _update(self) -> None:
        pass  # event-driven

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")

        s = self._cell_size()
        ox, oy = self._cell_origin()
        cell = s // 3
        pad = cell // 5

        # Grid lines
        for i in range(1, 3):
            c.create_line(ox + i * cell, oy, ox + i * cell, oy + s, fill=_BORDER, width=2)
            c.create_line(ox, oy + i * cell, ox + s, oy + i * cell, fill=_BORDER, width=2)

        # Pieces
        for idx in range(9):
            row, col = divmod(idx, 3)
            x1 = ox + col * cell + pad
            y1 = oy + row * cell + pad
            x2 = ox + col * cell + cell - pad
            y2 = oy + row * cell + cell - pad
            if self._board[idx] == self._PLAYER:
                c.create_oval(x1, y1, x2, y2, outline=_ACCENT, width=4)
            elif self._board[idx] == self._AI:
                c.create_line(x1, y1, x2, y2, fill=_ERR, width=4)
                c.create_line(x2, y1, x1, y2, fill=_ERR, width=4)

        # Score HUD
        c.create_text(8, 8, text=f"You: {self._wins}  AI: {self._losses}  Draw: {self._draws}",
                      fill=_TEXT, anchor="nw", font=("Segoe UI", 12, "bold"))
        c.create_text(self._w // 2, oy - 12, text="You = O   |   AI = X",
                      fill=_MUTED, anchor="center", font=("Segoe UI", 11))

        # Status overlay
        if self._status == "player_win":
            self._draw_result("You Win!", _ACCENT)
        elif self._status == "ai_win":
            self._draw_result("AI Wins!", _ERR)
        elif self._status == "draw":
            self._draw_result("Draw!", Colors.WARNING)

    def _draw_result(self, text: str, color: str) -> None:
        c = self.canvas
        cx, cy = self._w // 2, self._h // 2
        c.create_rectangle(cx - 150, cy + 60, cx + 150, cy + 110,
                           fill=_SURFACE, outline=_BORDER, width=2)
        c.create_text(cx, cy + 78, text=text, fill=color, font=("Segoe UI", 18, "bold"))
        c.create_text(cx, cy + 100, text="Click anywhere to play again",
                      fill=_TEXT, font=("Segoe UI", 10))

    def start(self) -> None:
        super().start()
        self.canvas.focus_set()
        self._wins = 0
        self._losses = 0
        self._draws = 0


# ===========================================================================
# Factory
# ===========================================================================

_GAME_CLASSES = {
    "snake": SnakeGame,
    "pong": PongGame,
    "breakout": BreakoutGame,
    "flappy": FlappyGame,
    "tictactoe": TicTacToeGame,
}


def make_arcade_game(kind: str, parent: tk.Widget, width: int = 640, height: int = 420) -> Optional[ArcadeGame]:
    """Instantiate an arcade game by its kind key; returns None if unknown."""
    cls = _GAME_CLASSES.get(kind)
    if cls is None:
        return None
    return cls(parent, width, height)
