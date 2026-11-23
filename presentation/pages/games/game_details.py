"""In-app playable Game Arena for Open Trivia DB, Deck of Cards API, Datamuse Word API, and built-in arcade games."""
import random
import tkinter as tk
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from core.exceptions import ApiError, KinetixError
from models.game import GameItem, PlayingCard, TriviaQuestion, WordPuzzle
from presentation.components.buttons import GhostButton, PrimaryButton, SecondaryButton
from presentation.pages.games.arcade_games import make_arcade_game
from presentation.components.cards import Chip, HeartButton
from presentation.components.dialogs import show_toast
from presentation.components.images import ImageView
from presentation.components.loaders import StateMessage
from presentation.styles import icons, typography, widgets
from presentation.styles.colors import Colors, Sizes, Spacing
from services.games.game_service import GameService
from utils.helpers import run_in_background
from utils.logger import get_logger

logger = get_logger("game_play")

_TRIVIA_SECONDS = 20
_TRIVIA_DIFFICULTIES = ("easy", "medium", "hard")
_CARD_W, _CARD_H = 88, 124
_BIG_CARD_W, _BIG_CARD_H = 128, 180


def _hand_value(cards: List[PlayingCard]) -> int:
    total = sum(c.blackjack_value for c in cards)
    aces = sum(1 for c in cards if c.value == "ACE")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


class GamePlayView(ctk.CTkFrame):
    """Hosts an interactive API-backed game directly inside Kinetix."""

    def __init__(
        self,
        parent,
        ctx,
        game: GameItem,
        *,
        is_favorite: bool = False,
        on_back: Callable[[], None],
        on_favorite_changed: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.ctx = ctx
        self._service: GameService = ctx.game_service or GameService()
        self._game = game
        self._is_favorite = is_favorite
        self._on_back = on_back
        self._on_favorite_changed = on_favorite_changed

        self._score = 0
        self._best_score = self._load_best_score()
        self._timer_job: Optional[str] = None
        self._op_token = 0

        self._build_top_bar()
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.HOVER,
        )
        self._scroll.pack(fill="both", expand=True)

        self._stage = ctk.CTkFrame(
            self._scroll, fg_color=Colors.CARD, corner_radius=Sizes.CARD_RADIUS,
            border_width=1, border_color=Colors.BORDER,
        )
        self._stage.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))

        if self._game.playable:
            self._record_played()
        self._launch_kind()

    # ------------------------------------------------------------------
    # Top Bar & Score
    # ------------------------------------------------------------------

    def _build_top_bar(self) -> None:
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", padx=Spacing.XL, pady=(Spacing.LG, Spacing.MD))

        GhostButton(
            nav, " Back to Games", command=self._handle_back,
            image=icons.icon("arrow_left", Colors.TEXT_SECONDARY, 16), compound="left", width=150,
        ).pack(side="left")

        title_box = ctk.CTkFrame(nav, fg_color="transparent")
        title_box.pack(side="left", padx=(Spacing.MD, 0))
        ctk.CTkLabel(
            title_box, text=self._game.title, font=typography.section(),
            text_color=Colors.TEXT, anchor="w",
        ).pack(side="left", padx=(0, Spacing.SM))
        Chip(title_box, self._game.api_source, accent=True).pack(side="left")

        self._heart = HeartButton(
            nav, favorite=self._is_favorite, command=self._toggle_favorite, circle=True,
        )
        self._heart.pack(side="right")

        if self._game.playable:
            self._best_label = ctk.CTkLabel(
                nav, text=f"Best: {self._best_score}", font=typography.body_bold(),
                text_color=Colors.TEXT_SECONDARY,
            )
            self._best_label.pack(side="right", padx=(0, Spacing.LG))

            self._score_label = ctk.CTkLabel(
                nav, text="Score: 0", font=typography.section(),
                text_color=Colors.ACCENT,
            )
            self._score_label.pack(side="right", padx=(0, Spacing.LG))
        else:
            self._best_label = None
            self._score_label = None

    def _set_score(self, value: int) -> None:
        self._score = max(0, int(value))
        if not self._alive():
            return
        self._score_label.configure(text=f"Score: {self._score}")
        if self._score > self._best_score:
            self._best_score = self._score
            self._best_label.configure(text=f"Best: {self._best_score}")
            self._save_best_score(self._best_score)

    def _clear_stage(self) -> None:
        self._cancel_timer()
        for child in self._stage.winfo_children():
            child.destroy()

    def _launch_kind(self) -> None:
        kind = self._game.kind
        if kind == "trivia":
            self._init_trivia()
        elif kind == "blackjack":
            self._init_blackjack()
        elif kind == "highlow":
            self._init_highlow()
        elif kind == "word_guess":
            self._init_word_guess()
        elif kind == "word_scramble":
            self._init_word_scramble()
        elif kind in ("snake", "pong", "breakout", "flappy", "tictactoe"):
            self._init_arcade(kind)
        elif kind == "rawg":
            self._init_rawg_details()
        else:
            StateMessage(self._stage, "error", "Unsupported game mode.").pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

    # ==================================================================
    # RAWG GAME DETAILS (Info-only, not playable in-app)
    # ==================================================================

    def _init_rawg_details(self) -> None:
        self._clear_stage()
        game = self._game
        body = ctk.CTkFrame(self._stage, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")

        cover = ImageView(top, (360, 202), placeholder="game", radius=Sizes.IMAGE_RADIUS)
        cover.pack(side="left", anchor="n")
        cover.load(game.image_url)

        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(Spacing.XL, 0))

        ctk.CTkLabel(
            info, text=game.title, font=typography.title(),
            text_color=Colors.TEXT, anchor="w", wraplength=560, justify="left",
        ).pack(fill="x")

        meta = ctk.CTkFrame(info, fg_color="transparent")
        meta.pack(fill="x", pady=(Spacing.SM, Spacing.MD))

        if game.released:
            ctk.CTkLabel(
                meta, text=f"Released {game.released}", font=typography.body(),
                text_color=Colors.TEXT_SECONDARY,
            ).pack(side="left", padx=(0, Spacing.MD))

        if game.rating > 0:
            ctk.CTkLabel(meta, text="", image=icons.icon("star", Colors.WARNING, 14)).pack(side="left")
            ctk.CTkLabel(
                meta, text=f" {game.rating:.1f} / 5", font=typography.body_bold(),
                text_color=Colors.TEXT,
            ).pack(side="left", padx=(0, Spacing.MD))

        if game.metacritic is not None:
            Chip(meta, f"Metacritic {game.metacritic}", accent=True).pack(side="left", padx=(0, Spacing.SM))

        Chip(meta, "Not Playable In-App").pack(side="left")

        genres = [g.strip() for g in game.genres.split(",") if g.strip()]
        if genres:
            genre_row = ctk.CTkFrame(info, fg_color="transparent")
            genre_row.pack(fill="x", pady=(0, Spacing.SM))
            for g in genres[:6]:
                Chip(genre_row, g).pack(side="left", padx=(0, Spacing.SM))

        if game.platforms:
            ctk.CTkLabel(
                info, text=f"Platforms: {game.platforms}", font=typography.small(),
                text_color=Colors.TEXT_SECONDARY, anchor="w", wraplength=560, justify="left",
            ).pack(fill="x", pady=(0, Spacing.XS))

        dev_label = ctk.CTkLabel(
            info, text=f"Developer: {game.developers}" if game.developers else "",
            font=typography.small(), text_color=Colors.TEXT_MUTED, anchor="w",
        )
        dev_label.pack(fill="x", pady=(0, Spacing.MD))

        actions = ctk.CTkFrame(info, fg_color="transparent")
        actions.pack(fill="x", pady=(Spacing.SM, 0))

        play_btn = PrimaryButton(
            actions, " Play Unavailable", command=None,
            image=icons.icon("games", Colors.ON_ACCENT, 15), compound="left", width=180,
        )
        play_btn.configure(state="disabled")
        play_btn.pack(side="left", padx=(0, Spacing.MD))

        fav_btn = SecondaryButton(
            actions,
            " Favorited" if self._is_favorite else " Add to Favorites",
            command=lambda: self._toggle_rawg_favorite(fav_btn),
            image=icons.icon("heart_filled" if self._is_favorite else "heart",
                             Colors.ACCENT if self._is_favorite else Colors.TEXT, 15),
            compound="left", width=170,
        )
        fav_btn.pack(side="left")

        ctk.CTkFrame(body, height=1, fg_color=Colors.BORDER, corner_radius=0).pack(
            fill="x", pady=(Spacing.XL, Spacing.LG),
        )
        ctk.CTkLabel(
            body, text="About This Game", font=typography.section(),
            text_color=Colors.TEXT, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.SM))

        desc_label = ctk.CTkLabel(
            body,
            text=game.description or "Loading detailed description...",
            font=typography.body(), text_color=Colors.TEXT_SECONDARY,
            anchor="w", justify="left", wraplength=860,
        )
        desc_label.pack(fill="x")

        if not game.description and game.game_id.startswith("rawg:"):
            rawg_id = int(game.game_id.split(":", 1)[1])
            self._op_token += 1
            token = self._op_token

            def done(detailed: Optional[GameItem], _error) -> None:
                if token != self._op_token or not self._alive():
                    return
                if detailed is not None:
                    self._game = detailed
                    if detailed.developers:
                        dev_label.configure(text=f"Developer: {detailed.developers}")
                    desc_label.configure(
                        text=detailed.description or "No detailed description available for this game.",
                    )
                else:
                    desc_label.configure(text="No detailed description available for this game.")

            run_in_background(self, lambda: self._service.get_rawg_details(rawg_id), done)

    def _toggle_rawg_favorite(self, fav_btn: SecondaryButton) -> None:
        state = self._toggle_favorite()
        if state is None:
            return
        self._heart.set_favorite(state)
        fav_btn.configure(
            text=" Favorited" if state else " Add to Favorites",
            image=icons.icon("heart_filled" if state else "heart",
                             Colors.ACCENT if state else Colors.TEXT, 15),
        )

    # ==================================================================
    # ARCADE GAMES (embedded tkinter Canvas)
    # ==================================================================

    def _init_arcade(self, kind: str) -> None:
        """Embed a pure-tkinter arcade game inside the stage frame."""
        self._clear_stage()
        self._arcade_game = None

        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)

        # Controls help text per game
        controls = {
            "snake": "Arrow keys / WASD to steer  |  R to restart",
            "pong": "W/S or Up/Down to move paddle  |  R to restart",
            "breakout": "A/D or Left/Right to move  |  Space to launch  |  R to restart",
            "flappy": "Space or Click to thrust  |  Click to restart after crash",
            "tictactoe": "Click a cell to place your move  |  You are O, AI is X",
        }
        hint = controls.get(kind, "")

        hint_label = ctk.CTkLabel(
            wrap,
            text=hint,
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_MUTED,
            anchor="center",
        )
        hint_label.pack(pady=(0, Spacing.SM))

        # Canvas host — plain tk.Frame so we don't pass width/height to CTk layout
        canvas_host = tk.Frame(wrap, bg=Colors.CARD)
        canvas_host.pack(anchor="center")

        game = make_arcade_game(kind, canvas_host, width=640, height=400)
        if game is None:
            StateMessage(self._stage, "error", "Could not load arcade game.").pack(
                fill="x", padx=Spacing.XL, pady=Spacing.XL,
            )
            return

        self._arcade_game = game
        game.canvas.pack()
        game.set_score_callback(self._set_score)
        game.start()

        # Restart button below canvas
        btn_row = ctk.CTkFrame(wrap, fg_color="transparent")
        btn_row.pack(pady=(Spacing.MD, 0))
        PrimaryButton(btn_row, "Restart", command=game.start, width=120).pack(side="left", padx=(0, Spacing.SM))
        SecondaryButton(btn_row, "Back to Games", command=self._handle_back, width=140).pack(side="left")

    # ==================================================================
    # 1. OPEN TRIVIA DB ARENA
    # ==================================================================

    def _init_trivia(self) -> None:
        self._trivia_diff = "medium"
        self._trivia_questions: List[TriviaQuestion] = []
        self._trivia_idx = 0
        self._trivia_streak = 0
        self._trivia_correct = 0
        self._trivia_left = _TRIVIA_SECONDS
        self._trivia_answered = False
        self._load_trivia_round()

    def _load_trivia_round(self) -> None:
        self._op_token += 1
        token = self._op_token
        self._clear_stage()

        box = ctk.CTkFrame(self._stage, fg_color="transparent")
        box.pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)
        StateMessage(box, "loading", "Fetching live questions from Open Trivia DB...").pack(fill="x")

        diff = self._trivia_diff
        cat_id = self._game.category_id

        run_in_background(
            self,
            lambda: self._service.load_trivia_round(cat_id, difficulty=diff, amount=10),
            lambda r, e: self._on_trivia_loaded(token, r, e),
        )

    def _on_trivia_loaded(self, token: int, questions: Optional[List[TriviaQuestion]], error: Optional[Exception]) -> None:
        if token != self._op_token or not self._alive():
            return
        if error is not None or not questions:
            self._clear_stage()
            msg = str(error) if isinstance(error, ApiError) else "Could not load trivia questions."
            StateMessage(self._stage, "error", msg, self._load_trivia_round).pack(
                fill="x", padx=Spacing.XL, pady=Spacing.XL,
            )
            return
        self._trivia_questions = questions
        self._trivia_idx = 0
        self._trivia_streak = 0
        self._trivia_correct = 0
        self._set_score(0)
        self._render_trivia_question()

    def _render_trivia_question(self) -> None:
        self._clear_stage()
        if self._trivia_idx >= len(self._trivia_questions):
            self._render_trivia_summary()
            return

        q = self._trivia_questions[self._trivia_idx]
        self._trivia_answered = False
        self._trivia_left = _TRIVIA_SECONDS

        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XL)

        # Header controls: difficulty + progress + timer
        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x", pady=(0, Spacing.LG))

        ctk.CTkLabel(
            top, text=f"Question {self._trivia_idx + 1} of {len(self._trivia_questions)}",
            font=typography.body_bold(), text_color=Colors.TEXT,
        ).pack(side="left")

        if self._trivia_streak > 0:
            Chip(top, f"Streak: {self._trivia_streak}", accent=True).pack(side="left", padx=(Spacing.MD, 0))

        self._trivia_timer_lbl = ctk.CTkLabel(
            top, text=f"{self._trivia_left}s", font=typography.section(),
            text_color=Colors.ACCENT,
        )
        self._trivia_timer_lbl.pack(side="right")

        diff_bar = ctk.CTkFrame(top, fg_color="transparent")
        diff_bar.pack(side="right", padx=(0, Spacing.XL))
        for d in _TRIVIA_DIFFICULTIES:
            active = d == self._trivia_diff
            ctk.CTkButton(
                diff_bar, text=d.title(), width=70, height=28, corner_radius=14,
                font=typography.tiny(),
                fg_color=Colors.ACCENT if active else Colors.SURFACE,
                hover_color=Colors.ACCENT_HOVER if active else Colors.HOVER,
                text_color=Colors.ON_ACCENT if active else Colors.TEXT_SECONDARY,
                border_width=1, border_color=Colors.ACCENT if active else Colors.BORDER,
                command=lambda val=d: self._change_trivia_diff(val),
            ).pack(side="left", padx=2)

        # Question card
        q_box = ctk.CTkFrame(
            wrap, fg_color=Colors.SURFACE, corner_radius=Sizes.CARD_RADIUS,
            border_width=1, border_color=Colors.BORDER,
        )
        q_box.pack(fill="x", pady=(0, Spacing.LG))
        ctk.CTkLabel(
            q_box, text=q.question, font=typography.section(), text_color=Colors.TEXT,
            anchor="w", justify="left", wraplength=820,
        ).pack(fill="x", padx=Spacing.XL, pady=Spacing.XL)

        # 2x2 answers grid
        grid = ctk.CTkFrame(wrap, fg_color="transparent")
        grid.pack(fill="x", pady=(0, Spacing.LG))
        for col in range(2):
            grid.grid_columnconfigure(col, weight=1, uniform="trivia_opts")

        self._trivia_btns: List[ctk.CTkButton] = []
        letters = ("A", "B", "C", "D")
        for idx, choice in enumerate(q.choices[:4]):
            btn = ctk.CTkButton(
                grid, text=f"{letters[idx]}.  {choice}", anchor="w", height=54,
                corner_radius=Sizes.BUTTON_RADIUS, font=typography.body_bold(),
                fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                text_color=Colors.TEXT, border_width=1, border_color=Colors.BORDER,
                command=lambda c=choice, b_idx=idx: self._answer_trivia(c, b_idx),
            )
            r, c = divmod(idx, 2)
            btn.grid(row=r, column=c, sticky="ew",
                     padx=(0, Spacing.MD if c == 0 else 0), pady=(0, Spacing.MD))
            self._trivia_btns.append(btn)

        bottom = ctk.CTkFrame(wrap, fg_color="transparent")
        bottom.pack(fill="x")
        self._trivia_feedback = ctk.CTkLabel(
            bottom, text="Choose the best answer before time runs out.",
            font=typography.body(), text_color=Colors.TEXT_SECONDARY,
        )
        self._trivia_feedback.pack(side="left")
        self._trivia_next_btn = PrimaryButton(bottom, "Next Question", command=self._next_trivia, width=150)
        self._trivia_next_btn.configure(state="disabled")
        self._trivia_next_btn.pack(side="right")

        self._tick_trivia_timer()

    def _change_trivia_diff(self, diff: str) -> None:
        if diff != self._trivia_diff:
            self._trivia_diff = diff
            self._load_trivia_round()

    def _tick_trivia_timer(self) -> None:
        if not self._alive() or self._trivia_answered:
            return
        if self._trivia_left <= 0:
            self._answer_trivia(None, -1)
            return
        self._trivia_left -= 1
        color = Colors.ERROR if self._trivia_left <= 5 else Colors.ACCENT
        self._trivia_timer_lbl.configure(text=f"{self._trivia_left}s", text_color=color)
        self._timer_job = self.after(1000, self._tick_trivia_timer)

    def _answer_trivia(self, selected: Optional[str], btn_idx: int) -> None:
        if self._trivia_answered:
            return
        self._trivia_answered = True
        self._cancel_timer()

        q = self._trivia_questions[self._trivia_idx]
        is_right = selected == q.correct_answer

        for i, btn in enumerate(self._trivia_btns):
            choice = q.choices[i]
            btn.configure(state="disabled")
            if choice == q.correct_answer:
                btn.configure(fg_color=Colors.SUCCESS_TINT, border_color=Colors.SUCCESS, text_color=Colors.SUCCESS)
            elif i == btn_idx and not is_right:
                btn.configure(fg_color=Colors.ERROR_TINT, border_color=Colors.ERROR, text_color=Colors.ERROR)

        if is_right:
            self._trivia_streak += 1
            self._trivia_correct += 1
            gained = 100 + (self._trivia_streak - 1) * 20 + self._trivia_left * 3
            self._set_score(self._score + gained)
            self._trivia_feedback.configure(text=f"Correct! +{gained} pts", text_color=Colors.SUCCESS)
        elif selected is None:
            self._trivia_streak = 0
            self._trivia_feedback.configure(
                text=f"Time's up! Answer: {q.correct_answer}", text_color=Colors.ERROR,
            )
        else:
            self._trivia_streak = 0
            self._trivia_feedback.configure(
                text=f"Incorrect. Correct answer: {q.correct_answer}", text_color=Colors.ERROR,
            )

        self._trivia_next_btn.configure(
            state="normal",
            text="Finish Round" if self._trivia_idx + 1 >= len(self._trivia_questions) else "Next Question",
        )

    def _next_trivia(self) -> None:
        self._trivia_idx += 1
        self._render_trivia_question()

    def _render_trivia_summary(self) -> None:
        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XXL)

        total = len(self._trivia_questions)
        ctk.CTkLabel(wrap, text="Round Complete", font=typography.title(), text_color=Colors.TEXT).pack(
            pady=(Spacing.LG, Spacing.SM),
        )
        ctk.CTkLabel(
            wrap,
            text=f"You answered {self._trivia_correct} of {total} correctly  •  Final Score: {self._score}",
            font=typography.section(), text_color=Colors.ACCENT,
        ).pack(pady=(0, Spacing.XL))

        PrimaryButton(wrap, "Play Another Round", command=self._load_trivia_round, width=180).pack()

    # ==================================================================
    # 2. BLACKJACK 21 (DECK OF CARDS API)
    # ==================================================================

    def _init_blackjack(self) -> None:
        self._bj_deck_id: Optional[str] = None
        self._bj_player: List[PlayingCard] = []
        self._bj_dealer: List[PlayingCard] = []
        self._bj_done = False
        self._deal_blackjack_hand()

    def _deal_blackjack_hand(self) -> None:
        self._op_token += 1
        token = self._op_token
        self._clear_stage()
        StateMessage(self._stage, "loading", "Shuffling and dealing from Deck of Cards API...").pack(
            fill="x", padx=Spacing.XL, pady=Spacing.XL,
        )

        deck_id = self._bj_deck_id

        def work():
            d_id = deck_id or self._service.new_deck(1)
            cards, remaining = self._service.draw_cards(d_id, 4)
            if remaining < 12:
                d_id = self._service.new_deck(1)
                cards, _ = self._service.draw_cards(d_id, 4)
            return d_id, cards

        run_in_background(self, work, lambda r, e: self._on_bj_dealt(token, r, e))

    def _on_bj_dealt(self, token: int, result, error: Optional[Exception]) -> None:
        if token != self._op_token or not self._alive():
            return
        if error is not None or not result:
            self._clear_stage()
            msg = str(error) if isinstance(error, ApiError) else "Could not reach Deck of Cards API."
            StateMessage(self._stage, "error", msg, self._deal_blackjack_hand).pack(
                fill="x", padx=Spacing.XL, pady=Spacing.XL,
            )
            return
        d_id, cards = result
        self._bj_deck_id = d_id
        self._bj_player = [cards[0], cards[2]]
        self._bj_dealer = [cards[1], cards[3]]
        self._bj_done = False

        p_val = _hand_value(self._bj_player)
        if p_val == 21:
            self._bj_done = True
            self._set_score(self._score + 75)
            self._render_blackjack("Blackjack! You hit 21! +75 pts", Colors.SUCCESS)
        else:
            self._render_blackjack("Hit to draw a card or Stand to hold.", Colors.TEXT_SECONDARY)

    def _render_blackjack(self, status_text: str, status_color: str) -> None:
        self._clear_stage()
        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XL)

        dealer_shown = _hand_value(self._bj_dealer) if self._bj_done else self._bj_dealer[0].blackjack_value
        ctk.CTkLabel(
            wrap, text=f"Dealer Hand ({dealer_shown if self._bj_done else f'{dealer_shown} + ?'})",
            font=typography.body_bold(), text_color=Colors.TEXT_SECONDARY, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.SM))

        d_row = ctk.CTkFrame(wrap, fg_color="transparent")
        d_row.pack(fill="x", pady=(0, Spacing.XL))
        for idx, card in enumerate(self._bj_dealer):
            if idx == 1 and not self._bj_done:
                back = ctk.CTkFrame(
                    d_row, width=_CARD_W, height=_CARD_H, fg_color=Colors.SURFACE,
                    corner_radius=Sizes.IMAGE_RADIUS, border_width=1, border_color=Colors.ACCENT,
                )
                back.pack(side="left", padx=(0, Spacing.SM))
                back.pack_propagate(False)
                ctk.CTkLabel(back, text="?", font=typography.title(), text_color=Colors.ACCENT).pack(expand=True)
            else:
                iv = ImageView(d_row, (_CARD_W, _CARD_H), placeholder="game")
                iv.pack(side="left", padx=(0, Spacing.SM))
                iv.load(card.image_url)

        p_val = _hand_value(self._bj_player)
        ctk.CTkLabel(
            wrap, text=f"Your Hand ({p_val})", font=typography.body_bold(),
            text_color=Colors.TEXT, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.SM))

        p_row = ctk.CTkFrame(wrap, fg_color="transparent")
        p_row.pack(fill="x", pady=(0, Spacing.XL))
        for card in self._bj_player:
            iv = ImageView(p_row, (_CARD_W, _CARD_H), placeholder="game")
            iv.pack(side="left", padx=(0, Spacing.SM))
            iv.load(card.image_url)

        ctk.CTkLabel(
            wrap, text=status_text, font=typography.section(), text_color=status_color, anchor="w",
        ).pack(fill="x", pady=(0, Spacing.LG))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x")
        hit_btn = PrimaryButton(btns, "Hit", command=self._bj_hit, width=120)
        hit_btn.pack(side="left", padx=(0, Spacing.SM))
        stand_btn = SecondaryButton(btns, "Stand", command=self._bj_stand, width=120)
        stand_btn.pack(side="left", padx=(0, Spacing.SM))
        if self._bj_done:
            hit_btn.configure(state="disabled")
            stand_btn.configure(state="disabled")
        SecondaryButton(btns, "Deal New Hand", command=self._deal_blackjack_hand, width=150).pack(side="left")

    def _bj_hit(self) -> None:
        if self._bj_done or not self._bj_deck_id:
            return
        self._op_token += 1
        token = self._op_token
        deck_id = self._bj_deck_id

        def work():
            return self._service.draw_cards(deck_id, 1)

        def done(res, error):
            if token != self._op_token or not self._alive() or error or not res:
                if error:
                    show_toast(self, str(error), "error")
                return
            cards, _ = res
            self._bj_player.extend(cards)
            val = _hand_value(self._bj_player)
            if val > 21:
                self._bj_done = True
                self._set_score(0)
                self._render_blackjack(f"Bust ({val})! Score reset.", Colors.ERROR)
            elif val == 21:
                self._bj_stand()
            else:
                self._render_blackjack("Hit or Stand?", Colors.TEXT_SECONDARY)

        run_in_background(self, work, done)

    def _bj_stand(self) -> None:
        if self._bj_done or not self._bj_deck_id:
            return
        self._op_token += 1
        token = self._op_token
        deck_id = self._bj_deck_id
        dealer = list(self._bj_dealer)

        def work():
            while _hand_value(dealer) < 17:
                more, _ = self._service.draw_cards(deck_id, 1)
                if not more:
                    break
                dealer.extend(more)
            return dealer

        def done(full_dealer, error):
            if token != self._op_token or not self._alive():
                return
            if error or not full_dealer:
                show_toast(self, "Could not finish dealer hand.", "error")
                return
            self._bj_dealer = full_dealer
            self._bj_done = True
            p_val = _hand_value(self._bj_player)
            d_val = _hand_value(self._bj_dealer)
            if d_val > 21 or p_val > d_val:
                self._set_score(self._score + 50)
                self._render_blackjack(f"You Win! ({p_val} vs {d_val}) +50 pts", Colors.SUCCESS)
            elif p_val == d_val:
                self._render_blackjack(f"Push! Tied at {p_val}.", Colors.WARNING)
            else:
                self._set_score(0)
                self._render_blackjack(f"Dealer Wins ({d_val} vs {p_val}). Score reset.", Colors.ERROR)

        run_in_background(self, work, done)

    # ==================================================================
    # 3. HIGH-LOW CARD STREAK (DECK OF CARDS API)
    # ==================================================================

    def _init_highlow(self) -> None:
        self._hl_deck_id: Optional[str] = None
        self._hl_card: Optional[PlayingCard] = None
        self._hl_remaining = 52
        self._hl_busy = False
        self._start_highlow()

    def _start_highlow(self) -> None:
        self._op_token += 1
        token = self._op_token
        self._clear_stage()
        StateMessage(self._stage, "loading", "Shuffling deck from Deck of Cards API...").pack(
            fill="x", padx=Spacing.XL, pady=Spacing.XL,
        )

        def work():
            d_id = self._service.new_deck(1)
            cards, remaining = self._service.draw_cards(d_id, 1)
            return d_id, cards[0], remaining

        def done(res, error):
            if token != self._op_token or not self._alive():
                return
            if error or not res:
                self._clear_stage()
                StateMessage(self._stage, "error", "Could not start High-Low.", self._start_highlow).pack(
                    fill="x", padx=Spacing.XL, pady=Spacing.XL,
                )
                return
            d_id, card, remaining = res
            self._hl_deck_id = d_id
            self._hl_card = card
            self._hl_remaining = remaining
            self._set_score(0)
            self._render_highlow("Will the next card be Higher or Lower?", Colors.TEXT_SECONDARY)

        run_in_background(self, work, done)

    def _render_highlow(self, status_text: str, status_color: str) -> None:
        self._clear_stage()
        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XL)

        ctk.CTkLabel(
            wrap, text=f"Cards Remaining: {self._hl_remaining}",
            font=typography.small(), text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.MD))

        iv = ImageView(wrap, (_BIG_CARD_W, _BIG_CARD_H), placeholder="game")
        iv.pack(pady=(0, Spacing.LG))
        if self._hl_card:
            iv.load(self._hl_card.image_url)

        ctk.CTkLabel(
            wrap, text=status_text, font=typography.section(), text_color=status_color,
        ).pack(pady=(0, Spacing.LG))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack()
        PrimaryButton(btns, "Higher", command=lambda: self._guess_highlow("high"), width=130).pack(
            side="left", padx=(0, Spacing.SM),
        )
        PrimaryButton(btns, "Lower", command=lambda: self._guess_highlow("low"), width=130).pack(
            side="left", padx=(0, Spacing.SM),
        )
        SecondaryButton(btns, "New Deck", command=self._start_highlow, width=120).pack(side="left")

    def _guess_highlow(self, guess: str) -> None:
        if self._hl_busy or not self._hl_deck_id or not self._hl_card:
            return
        self._hl_busy = True
        self._op_token += 1
        token = self._op_token
        deck_id = self._hl_deck_id
        prev = self._hl_card

        def work():
            if self._hl_remaining <= 0:
                d_id = self._service.new_deck(1)
                cards, rem = self._service.draw_cards(d_id, 1)
                return d_id, cards[0], rem
            cards, rem = self._service.draw_cards(deck_id, 1)
            return deck_id, cards[0], rem

        def done(res, error):
            self._hl_busy = False
            if token != self._op_token or not self._alive() or error or not res:
                if error:
                    show_toast(self, str(error), "error")
                return
            d_id, nxt, rem = res
            self._hl_deck_id = d_id
            self._hl_card = nxt
            self._hl_remaining = rem

            if nxt.rank_number == prev.rank_number:
                self._render_highlow(f"Tie ({nxt.value})! Streak kept.", Colors.WARNING)
            elif (guess == "high" and nxt.rank_number > prev.rank_number) or \
                    (guess == "low" and nxt.rank_number < prev.rank_number):
                self._set_score(self._score + 25)
                self._render_highlow(f"Nice! {nxt.value} of {nxt.suit.title()} (+25 pts)", Colors.SUCCESS)
            else:
                self._set_score(0)
                self._render_highlow(f"Missed! {nxt.value} of {nxt.suit.title()}. Streak reset.", Colors.ERROR)

        run_in_background(self, work, done)

    # ==================================================================
    # 4. 5-LETTER WORD GUESS (DATAMUSE WORD API)
    # ==================================================================

    def _init_word_guess(self) -> None:
        self._wg_puzzle: Optional[WordPuzzle] = None
        self._wg_guesses: List[str] = []
        self._wg_current = ""
        self._wg_done = False
        self._wg_hint_shown = False
        self._load_word_guess()

    def _load_word_guess(self) -> None:
        self._op_token += 1
        token = self._op_token
        self._clear_stage()
        StateMessage(self._stage, "loading", "Fetching a 5-letter word from Datamuse API...").pack(
            fill="x", padx=Spacing.XL, pady=Spacing.XL,
        )
        run_in_background(
            self,
            lambda: self._service.load_word_puzzle(5),
            lambda r, e: self._on_wg_loaded(token, r, e),
        )

    def _on_wg_loaded(self, token: int, puzzle: Optional[WordPuzzle], error: Optional[Exception]) -> None:
        if token != self._op_token or not self._alive():
            return
        if error or not puzzle:
            self._clear_stage()
            msg = str(error) if isinstance(error, ApiError) else "Could not fetch word puzzle."
            StateMessage(self._stage, "error", msg, self._load_word_guess).pack(
                fill="x", padx=Spacing.XL, pady=Spacing.XL,
            )
            return
        self._wg_puzzle = puzzle
        self._wg_guesses = []
        self._wg_current = ""
        self._wg_done = False
        self._wg_hint_shown = False
        self._render_word_guess()

    def _render_word_guess(self) -> None:
        self._clear_stage()
        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XL)

        # Grid 6x5
        grid = ctk.CTkFrame(wrap, fg_color="transparent")
        grid.pack(pady=(0, Spacing.MD))

        secret = self._wg_puzzle.word if self._wg_puzzle else ""
        key_states: Dict[str, str] = {}

        for r in range(6):
            row_f = ctk.CTkFrame(grid, fg_color="transparent")
            row_f.pack(pady=3)
            guess = self._wg_guesses[r] if r < len(self._wg_guesses) else (self._wg_current if r == len(self._wg_guesses) else "")
            evaluated = r < len(self._wg_guesses)
            colors = self._score_wordle_row(guess, secret) if evaluated else [(Colors.SURFACE, Colors.BORDER, Colors.TEXT)] * 5

            if evaluated:
                for ch, (bg, _br, _fg) in zip(guess, colors):
                    if bg == Colors.SUCCESS or key_states.get(ch) != Colors.SUCCESS:
                        if bg != Colors.SURFACE or ch not in key_states:
                            key_states[ch] = bg

            for c in range(5):
                ch = guess[c] if c < len(guess) else ""
                bg, br, fg = colors[c]
                tile = ctk.CTkLabel(
                    row_f, text=ch, width=48, height=48, corner_radius=8,
                    fg_color=bg, text_color=fg, font=typography.section(),
                )
                tile.pack(side="left", padx=3)

        # Hint & status
        hint_text = f"Hint: {self._wg_puzzle.definition}" if (self._wg_hint_shown and self._wg_puzzle) else ""
        self._wg_status = ctk.CTkLabel(
            wrap, text=hint_text or "Type on your keyboard or tap letters below.",
            font=typography.body(), text_color=Colors.TEXT_SECONDARY, wraplength=600,
        )
        self._wg_status.pack(pady=(Spacing.XS, Spacing.MD))

        # On-screen keyboard
        kb = ctk.CTkFrame(wrap, fg_color="transparent")
        kb.pack(pady=(0, Spacing.MD))
        for kb_row in ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"):
            rf = ctk.CTkFrame(kb, fg_color="transparent")
            rf.pack(pady=2)
            if kb_row == "ZXCVBNM":
                ctk.CTkButton(
                    rf, text="ENTER", width=62, height=34, corner_radius=6,
                    fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
                    text_color=Colors.ON_ACCENT, font=typography.tiny(),
                    command=self._wg_submit,
                ).pack(side="left", padx=2)
            for ch in kb_row:
                bg = key_states.get(ch, Colors.SURFACE)
                fg = Colors.ON_ACCENT if bg in (Colors.SUCCESS, Colors.WARNING) else Colors.TEXT
                ctk.CTkButton(
                    rf, text=ch, width=36, height=34, corner_radius=6,
                    fg_color=bg, hover_color=Colors.HOVER, text_color=fg,
                    border_width=1, border_color=Colors.BORDER, font=typography.body_bold(),
                    command=lambda letter=ch: self._wg_type(letter),
                ).pack(side="left", padx=2)
            if kb_row == "ZXCVBNM":
                ctk.CTkButton(
                    rf, text="DEL", width=52, height=34, corner_radius=6,
                    fg_color=Colors.SURFACE, hover_color=Colors.HOVER,
                    text_color=Colors.TEXT, border_width=1, border_color=Colors.BORDER,
                    font=typography.tiny(), command=self._wg_backspace,
                ).pack(side="left", padx=2)

        actions = ctk.CTkFrame(wrap, fg_color="transparent")
        actions.pack()
        SecondaryButton(actions, "Definition Hint", command=self._wg_show_hint, width=140).pack(
            side="left", padx=(0, Spacing.SM),
        )
        PrimaryButton(actions, "New Word", command=self._load_word_guess, width=120).pack(side="left")

        wrap.bind("<Key>", self._on_wg_key)
        self.after(30, lambda: wrap.focus_set() if self._alive() and wrap.winfo_exists() else None)

    @staticmethod
    def _score_wordle_row(guess: str, secret: str) -> List[tuple]:
        result = [(Colors.SURFACE, Colors.BORDER, Colors.TEXT_MUTED)] * 5
        counts: Dict[str, int] = {}
        for s in secret:
            counts[s] = counts.get(s, 0) + 1
        for i in range(5):
            if guess[i] == secret[i]:
                result[i] = (Colors.SUCCESS, Colors.SUCCESS, Colors.ON_ACCENT)
                counts[guess[i]] -= 1
        for i in range(5):
            if result[i][0] == Colors.SUCCESS:
                continue
            ch = guess[i]
            if counts.get(ch, 0) > 0:
                result[i] = (Colors.WARNING, Colors.WARNING, Colors.ON_ACCENT)
                counts[ch] -= 1
        return result

    def _on_wg_key(self, event) -> None:
        if self._wg_done:
            return
        if event.keysym == "Return":
            self._wg_submit()
        elif event.keysym == "BackSpace":
            self._wg_backspace()
        elif len(event.char) == 1 and event.char.isalpha():
            self._wg_type(event.char.upper())

    def _wg_type(self, letter: str) -> None:
        if self._wg_done or len(self._wg_current) >= 5:
            return
        self._wg_current += letter
        self._render_word_guess()

    def _wg_backspace(self) -> None:
        if self._wg_done or not self._wg_current:
            return
        self._wg_current = self._wg_current[:-1]
        self._render_word_guess()

    def _wg_show_hint(self) -> None:
        self._wg_hint_shown = True
        self._render_word_guess()

    def _wg_submit(self) -> None:
        if self._wg_done or len(self._wg_current) != 5 or not self._wg_puzzle:
            return
        guess = self._wg_current
        self._wg_guesses.append(guess)
        self._wg_current = ""
        if guess == self._wg_puzzle.word:
            self._wg_done = True
            pts = (7 - len(self._wg_guesses)) * 40
            self._set_score(self._score + pts)
            self._render_word_guess()
            self._wg_status.configure(text=f"Solved! {self._wg_puzzle.word} (+{pts} pts)", text_color=Colors.SUCCESS)
        elif len(self._wg_guesses) >= 6:
            self._wg_done = True
            self._set_score(0)
            self._render_word_guess()
            self._wg_status.configure(
                text=f"Out of tries! The word was {self._wg_puzzle.word}.", text_color=Colors.ERROR,
            )
        else:
            self._render_word_guess()

    # ==================================================================
    # 5. WORD SCRAMBLE (DATAMUSE WORD API)
    # ==================================================================

    def _init_word_scramble(self) -> None:
        self._ws_puzzle: Optional[WordPuzzle] = None
        self._ws_scrambled = ""
        self._load_scramble()

    def _load_scramble(self) -> None:
        self._op_token += 1
        token = self._op_token
        self._clear_stage()
        StateMessage(self._stage, "loading", "Fetching a word puzzle from Datamuse API...").pack(
            fill="x", padx=Spacing.XL, pady=Spacing.XL,
        )
        length = random.choice((5, 6, 7))
        run_in_background(
            self,
            lambda: self._service.load_word_puzzle(length),
            lambda r, e: self._on_ws_loaded(token, r, e),
        )

    def _on_ws_loaded(self, token: int, puzzle: Optional[WordPuzzle], error: Optional[Exception]) -> None:
        if token != self._op_token or not self._alive():
            return
        if error or not puzzle:
            self._clear_stage()
            msg = str(error) if isinstance(error, ApiError) else "Could not fetch word puzzle."
            StateMessage(self._stage, "error", msg, self._load_scramble).pack(
                fill="x", padx=Spacing.XL, pady=Spacing.XL,
            )
            return
        self._ws_puzzle = puzzle
        letters = list(puzzle.word)
        for _ in range(5):
            random.shuffle(letters)
            if "".join(letters) != puzzle.word:
                break
        self._ws_scrambled = "".join(letters)
        self._render_scramble()

    def _render_scramble(self) -> None:
        self._clear_stage()
        if not self._ws_puzzle:
            return
        wrap = ctk.CTkFrame(self._stage, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=Spacing.XXL, pady=Spacing.XXL)

        tiles = ctk.CTkFrame(wrap, fg_color="transparent")
        tiles.pack(pady=(Spacing.MD, Spacing.LG))
        for ch in self._ws_scrambled:
            ctk.CTkLabel(
                tiles, text=ch, width=52, height=56, corner_radius=10,
                fg_color=Colors.ACCENT_TINT_CARD, text_color=Colors.ACCENT,
                font=typography.title(),
            ).pack(side="left", padx=Spacing.XS)

        clue = f"({self._ws_puzzle.part_of_speech}) {self._ws_puzzle.definition}" if self._ws_puzzle.part_of_speech else self._ws_puzzle.definition
        ctk.CTkLabel(
            wrap, text=f"Clue: {clue}", font=typography.body(),
            text_color=Colors.TEXT_SECONDARY, wraplength=640, justify="center",
        ).pack(pady=(0, Spacing.LG))

        entry_box = ctk.CTkFrame(
            wrap, fg_color=Colors.SURFACE, border_width=1, border_color=Colors.BORDER,
            corner_radius=Sizes.INPUT_RADIUS, width=320, height=Sizes.INPUT_HEIGHT,
        )
        entry_box.pack(pady=(0, Spacing.MD))
        entry_box.pack_propagate(False)

        self._ws_entry = ctk.CTkEntry(
            entry_box, placeholder_text="Type the unscrambled word...", **widgets.entry(),
        )
        self._ws_entry.pack(fill="both", expand=True, padx=Spacing.MD)
        self._ws_entry.bind("<Return>", lambda _e: self._submit_scramble())
        self.after(50, lambda: self._ws_entry.focus_set() if self._alive() else None)

        self._ws_feedback = ctk.CTkLabel(wrap, text="", font=typography.body(), text_color=Colors.TEXT_SECONDARY)
        self._ws_feedback.pack(pady=(0, Spacing.MD))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack()
        PrimaryButton(btns, "Submit", command=self._submit_scramble, width=120).pack(
            side="left", padx=(0, Spacing.SM),
        )
        SecondaryButton(btns, "Reshuffle", command=self._reshuffle_scramble, width=110).pack(
            side="left", padx=(0, Spacing.SM),
        )
        SecondaryButton(btns, "Next Word", command=self._load_scramble, width=110).pack(side="left")

    def _reshuffle_scramble(self) -> None:
        letters = list(self._ws_scrambled)
        random.shuffle(letters)
        self._ws_scrambled = "".join(letters)
        self._render_scramble()

    def _submit_scramble(self) -> None:
        if not self._ws_puzzle:
            return
        guess = self._ws_entry.get().strip().upper()
        if not guess:
            return
        if guess == self._ws_puzzle.word:
            self._set_score(self._score + 50)
            show_toast(self, f"Correct! {self._ws_puzzle.word} (+50 pts)", "success", 2000)
            self._load_scramble()
        else:
            self._ws_feedback.configure(text="Not quite — try again!", text_color=Colors.ERROR)

    # ------------------------------------------------------------------
    # Persistence, Favorites, History & Cleanup
    # ------------------------------------------------------------------

    def _toggle_favorite(self) -> Optional[bool]:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return None
        try:
            state = self.ctx.library.toggle_favorite(user.id, self._game.to_media_item())
        except KinetixError:
            show_toast(self, "Could not update favorites.", "error")
            return None
        self._is_favorite = state
        if self._on_favorite_changed is not None:
            self._on_favorite_changed(self._game.game_id, state)
        return state

    def _record_played(self) -> None:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        try:
            self.ctx.library.record_play(user.id, self._game.to_media_item())
        except KinetixError as exc:
            logger.debug("Could not record game history: %s", exc)

    def _load_best_score(self) -> int:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return 0
        try:
            return self.ctx.library.get_game_high_score(user.id, self._game.game_id)
        except Exception:  # noqa: BLE001
            return 0

    def _save_best_score(self, score: int) -> None:
        user = self.ctx.session_service.current_user
        if user is None or self.ctx.library is None:
            return
        try:
            self.ctx.library.save_game_high_score(user.id, self._game.game_id, score)
        except Exception:  # noqa: BLE001
            pass

    def _cancel_timer(self) -> None:
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except Exception:  # noqa: BLE001
                pass
            self._timer_job = None

    def _handle_back(self) -> None:
        self._cancel_timer()
        self._on_back()

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except Exception:  # noqa: BLE001
            return False

    def destroy(self) -> None:
        self._op_token += 1
        self._cancel_timer()
        if hasattr(self, "_arcade_game") and self._arcade_game is not None:
            try:
                self._arcade_game.stop()
            except Exception:  # noqa: BLE001
                pass
        super().destroy()


GameDetailsView = GamePlayView
