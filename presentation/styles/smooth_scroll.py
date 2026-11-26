"""Responsive, tear-free mouse-wheel scrolling for all CTkScrollableFrame widgets."""
import sys
import tkinter as tk
import customtkinter as ctk

_PIXELS_PER_NOTCH = 56
_INSTALLED = False


def scroll_to_top(scrollable: ctk.CTkScrollableFrame) -> None:
    """Reset a CTkScrollableFrame to the top and refresh its scrollregion."""
    try:
        if not scrollable.winfo_exists():
            return
        canvas = scrollable._parent_canvas
        bbox = canvas.bbox("all")
        if bbox is not None:
            canvas.configure(scrollregion=bbox)
        canvas.yview_moveto(0.0)
    except Exception:  # noqa: BLE001
        pass


def _safe_valid_scroll(scrollable: ctk.CTkScrollableFrame, widget) -> bool:
    """Safely check if `widget` belongs to `scrollable` without failing on dead/string widgets."""
    try:
        if widget is None or isinstance(widget, str):
            return False
        if not widget.winfo_exists():
            return False
        return bool(scrollable._check_if_valid_scroll(widget))
    except (tk.TclError, AttributeError):
        return False


def enable_smooth_scrolling() -> None:
    """Patch CTkScrollableFrame for crisp, tear-free scrolling and safe cleanup."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    orig_wheel = ctk.CTkScrollableFrame._mouse_wheel_all
    orig_shift_press = ctk.CTkScrollableFrame._keyboard_shift_press_all
    orig_shift_release = ctk.CTkScrollableFrame._keyboard_shift_release_all
    orig_destroy = ctk.CTkScrollableFrame.destroy

    def _fast_wheel(self, event):
        if getattr(self, "_kinetix_destroyed", False):
            return
        try:
            if not self.winfo_exists() or not self.winfo_ismapped():
                return
        except tk.TclError:
            return

        if not _safe_valid_scroll(self, getattr(event, "widget", None)):
            return

        if not sys.platform.startswith("win") or getattr(self, "_shift_pressed", False):
            try:
                orig_wheel(self, event)
            except tk.TclError:
                pass
            return

        canvas = self._parent_canvas
        try:
            if canvas.yview() == (0.0, 1.0):
                return
            if not getattr(self, "_scroll_inc_set", False):
                canvas.configure(yscrollincrement=1)
                self._scroll_inc_set = True

            delta_px = -round((event.delta / 120.0) * _PIXELS_PER_NOTCH)
            if delta_px == 0:
                delta_px = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta_px, "units")
            # Flush pending child-window moves synchronously so nested widgets
            # never lag behind or smear when scrolling on Windows.
            canvas.update_idletasks()
        except tk.TclError:
            pass

    def _safe_shift_press(self, event):
        if getattr(self, "_kinetix_destroyed", False):
            return
        try:
            if self.winfo_exists():
                orig_shift_press(self, event)
        except tk.TclError:
            pass

    def _safe_shift_release(self, event):
        if getattr(self, "_kinetix_destroyed", False):
            return
        try:
            if self.winfo_exists():
                orig_shift_release(self, event)
        except tk.TclError:
            pass

    def _safe_destroy(self):
        self._kinetix_destroyed = True
        orig_destroy(self)

    ctk.CTkScrollableFrame._mouse_wheel_all = _fast_wheel
    ctk.CTkScrollableFrame._keyboard_shift_press_all = _safe_shift_press
    ctk.CTkScrollableFrame._keyboard_shift_release_all = _safe_shift_release
    ctk.CTkScrollableFrame.destroy = _safe_destroy
