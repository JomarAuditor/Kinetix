"""Dialogs: ConfirmDialog (modal) and show_toast (small message in the corner)."""
from typing import Callable, Optional

import customtkinter as ctk

from config import settings
from presentation.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from presentation.styles import icons, typography
from presentation.styles.colors import Colors, Sizes, Spacing

_TOAST_ATTRIBUTE = "_kinetix_toast"
_TOAST_STYLES = {
    "success": ("check", Colors.SUCCESS),
    "error": ("alert", Colors.ERROR),
    "info": ("alert", Colors.ACCENT),
}


def apply_window_icon(window) -> None:
    """Set the Kinetix icon. CustomTkinter resets it on Windows, so set it again after 200 ms."""
    path = str(settings.LOGOS_DIR / "kinetix.ico")

    def set_icon() -> None:
        try:
            window.iconbitmap(path)
        except Exception:  # noqa: BLE001 - icon is optional (e.g. not on Linux)
            pass

    set_icon()
    try:
        window.after(200, set_icon)
    except Exception:  # noqa: BLE001
        pass


class ConfirmDialog(ctk.CTkToplevel):
    """ConfirmDialog(parent, title, message, confirm_text="Confirm", on_confirm=fn, danger=False)"""

    def __init__(self, parent, title: str, message: str, confirm_text: str = "Confirm",
                 cancel_text: str = "Cancel", on_confirm: Optional[Callable[[], None]] = None,
                 danger: bool = False):
        super().__init__(parent, fg_color=Colors.CARD)
        self._on_confirm = on_confirm
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        apply_window_icon(self)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        ctk.CTkLabel(body, text=title, font=typography.section(), text_color=Colors.TEXT,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(body, text=message, font=typography.body(), text_color=Colors.TEXT_SECONDARY,
                     anchor="w", justify="left", wraplength=Sizes.DIALOG_WIDTH - 2 * Spacing.XL
                     ).pack(fill="x", pady=(Spacing.SM, Spacing.XL))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")
        confirm_class = DangerButton if danger else PrimaryButton
        confirm_class(buttons, confirm_text, self._confirm, width=120).pack(side="right")
        SecondaryButton(buttons, cancel_text, self.close, width=100).pack(side="right", padx=(0, Spacing.SM))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<Return>", lambda _e: self._confirm())
        self._center_on(parent)
        self.after(20, lambda: self._center_on(parent))
        self.after(120, self._take_focus)

    def _center_on(self, parent) -> None:
        if not self.winfo_exists():
            return
        root = parent.winfo_toplevel()
        root.update_idletasks()
        self.update_idletasks()
        try:
            scale = self._get_window_scaling()
        except Exception:  # noqa: BLE001
            scale = 1.0
        req_w = max(Sizes.DIALOG_WIDTH, round(self.winfo_reqwidth() / max(scale, 0.1)))
        req_h = max(140, round(self.winfo_reqheight() / max(scale, 0.1)))
        phys_w = round(req_w * scale)
        phys_h = round(req_h * scale)
        x = root.winfo_rootx() + (root.winfo_width() - phys_w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - phys_h) // 2
        self.geometry(f"{req_w}x{req_h}+{max(x, 0)}+{max(y, 0)}")

    def _take_focus(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # noqa: BLE001 - window closed too fast
            pass

    def _confirm(self) -> None:
        callback = self._on_confirm
        self.close()
        if callback:
            callback()

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


class Toast(ctk.CTkFrame):
    def __init__(self, parent, message: str, kind: str):
        icon_name, color = _TOAST_STYLES.get(kind, _TOAST_STYLES["info"])
        super().__init__(parent, fg_color=Colors.CARD, border_width=1, border_color=color,
                         corner_radius=Sizes.CARD_RADIUS)
        self._job: Optional[str] = None
        ctk.CTkLabel(self, text="", image=icons.icon(icon_name, color, 18)).pack(
            side="left", padx=(Spacing.MD, Spacing.SM), pady=Spacing.MD)
        ctk.CTkLabel(self, text=message, font=typography.body(), text_color=Colors.TEXT, anchor="w",
                     justify="left", wraplength=Sizes.TOAST_WIDTH - 72).pack(
            side="left", padx=(0, Spacing.LG), pady=Spacing.MD)

    def schedule_close(self, milliseconds: int) -> None:
        self._job = self.after(milliseconds, self.destroy)

    def destroy(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:  # noqa: BLE001
                pass
            self._job = None
        super().destroy()


def show_toast(widget, message: str, kind: str = "info", duration_ms: int = 3200) -> None:
    """Show a short message in the bottom-right corner. kind: info, success or error."""
    try:
        root = widget.winfo_toplevel()
        old = getattr(root, _TOAST_ATTRIBUTE, None)
        if old is not None:
            old.destroy()
        toast = Toast(root, message, kind)
        toast.place(relx=1.0, rely=1.0, x=-Spacing.XL, y=-Spacing.XL, anchor="se")
        toast.lift()
        toast.schedule_close(duration_ms)
        setattr(root, _TOAST_ATTRIBUTE, toast)
    except Exception:  # noqa: BLE001 - a toast must never crash the app
        pass
