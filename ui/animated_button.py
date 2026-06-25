"""
AnimatedRunButton — red primary button with a ripple/flash animation on click.
Uses QPropertyAnimation on a custom 'flash' property (background brightness).
"""

from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PySide6.QtCore    import (Qt, QTimer, QPropertyAnimation,
                                QSequentialAnimationGroup, QEasingCurve, Property)
from PySide6.QtGui     import QColor

from ui.button_styles import BTN_PRIMARY, BTN_BLUE


class AnimatedRunButton(QPushButton):
    """
    Primary action button (green run, red stop, or blue).
    On click: briefly flashes white border, then restores.
    """

    def __init__(self, text: str, color: str = "red", parent=None):
        super().__init__(text, parent)
        self._color = color
        self._animating = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(46)
        self._apply_style(False)

    # ── style helpers ─────────────────────────────────────────────────────
    def _apply_style(self, pressed: bool):
        if self._color == "green":
            bg     = "#16a34a" if pressed else "#22c55e"
            bg_hov = "#16a34a"
            dis_bg = "#14532d"
            dis_fg = "#86efac"
            fg     = "#ffffff"
        elif self._color == "red":
            bg     = "#dc2626" if pressed else "#ef4444"
            bg_hov = "#dc2626"
            dis_bg = "#7f1d1d"
            dis_fg = "#fca5a5"
            fg     = "#ffffff"
        else:
            bg     = "#0ea5e9" if pressed else "#38bdf8"
            bg_hov = "#0ea5e9"
            dis_bg = "#075985"
            dis_fg = "#bae6fd"
            fg     = "#1e293b"
        border = "2px solid #ffffff" if pressed else "none"

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: {border};
                border-radius: 4px;
                color: {fg};
                font-family: 'Rajdhani', 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 12px 32px;
                min-height: 46px;
            }}
            QPushButton:hover {{ background: {bg_hov}; }}
            QPushButton:disabled {{
                background: {dis_bg};
                color: {dis_fg};
                border: none;
            }}
        """)

    # ── click animation ───────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if not self._animating:
            self._flash()
        super().mousePressEvent(event)

    def _flash(self):
        """Quick 3-step flash: darken → white border → restore."""
        self._animating = True
        self._apply_style(True)           # step 1: pressed look

        def step2():
            self._apply_style(False)      # step 2: restore
            self._animating = False

        QTimer.singleShot(140, step2)     # restore after 140 ms

    # ── enabled/disabled ──────────────────────────────────────────────────
    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self._apply_style(False)
