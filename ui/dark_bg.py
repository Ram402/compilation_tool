"""
Dark Animated Background — reusable gradient + neural-field overlay.

Apply to any tab with:
    from ui.dark_bg import apply_dark_animated_bg
    apply_dark_animated_bg(self)        # call at end of _build_ui
"""

import math, random

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QLinearGradient, QRadialGradient,
)


# ── helpers ──────────────────────────────────────────────────────────────────
def _cl(v):
    return max(0.0, min(1.0, float(v)))

def _a(c, a):
    q = QColor(c)
    q.setAlphaF(_cl(a))
    return q

def _hex(s):
    return QColor(s)


C_BG   = "#050816"
C_CYAN = "#00F5FF"
C_PUR  = "#7B61FF"
C_MINT = "#00FFB2"
C_WHT  = "#FFFFFF"

CYAN  = _hex(C_CYAN)
PUR   = _hex(C_PUR)
MINT  = _hex(C_MINT)
WHITE = _hex(C_WHT)


# ════════════════════════════════════════════════════════════════════════════
#  DARK GRADIENT BACKGROUND  (animated sweeping gradient, subtle grid)
# ════════════════════════════════════════════════════════════════════════════
class DarkGradientBg(QWidget):
    """Animated dark gradient matching the homepage hero header."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._t = 0.0
        QTimer(self, timeout=self._tick, interval=33).start()

    def _tick(self):
        self._t += 0.022
        self.update()

    def paintEvent(self, _):
        if self.width() < 2:
            return
        pa = QPainter(self)
        pa.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        t = self._t

        # Base fill
        pa.fillRect(self.rect(), _hex(C_BG))

        # Animated sweeping linear gradient
        g = QLinearGradient(0, 0, w, h)
        s = math.sin(t * 0.45) * 0.11
        g.setColorAt(_cl(s),          QColor(0, 8, 38, 255))
        g.setColorAt(_cl(0.44 + s),   QColor(8, 0, 55, 210))
        g.setColorAt(_cl(0.87 + s * 0.5), QColor(0, 28, 48, 255))
        pa.fillRect(self.rect(), g)

        # Sweeping cyan radial highlight
        sx = (math.sin(t * 0.35) * 0.5 + 0.5) * w
        g2 = QRadialGradient(sx, h * 0.65, 250)
        g2.setColorAt(0, _a(CYAN, 0.018))
        g2.setColorAt(1, _a(CYAN, 0.000))
        pa.fillRect(self.rect(), g2)

        # Purple radial accent
        g3 = QRadialGradient(w * 0.82, h * 0.3, 180)
        g3.setColorAt(0, _a(PUR, 0.015))
        g3.setColorAt(1, _a(PUR, 0.000))
        pa.fillRect(self.rect(), g3)

        # Subtle grid lines
        pa.setPen(QPen(_a(WHITE, 0.035), 0.8))
        for x in range(0, w, 48):
            pa.drawLine(x, 0, x, h)
        for y in range(0, h, 48):
            pa.drawLine(0, y, w, y)


# ════════════════════════════════════════════════════════════════════════════
#  NEURAL PARTICLE FIELD  (transparent mouse-passthrough overlay)
# ════════════════════════════════════════════════════════════════════════════
class NeuralFieldOverlay(QWidget):
    """Animated particles + neural-network connection lines."""

    N_NODES  = 52
    MAX_DIST = 0.18  # fraction of diagonal for connection

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._t = 0
        rng = random.Random(99)
        self._nodes = [
            {
                'x': rng.random(), 'y': rng.random(),
                'vx': (rng.random() - 0.5) * 0.00025,
                'vy': (rng.random() - 0.5) * 0.00025,
                'r': rng.uniform(0.9, 2.2),
                'a0': rng.uniform(0.12, 0.38),
                'ph': rng.uniform(0, math.pi * 2),
                'col': rng.choice([CYAN, PUR, MINT]),
            }
            for _ in range(self.N_NODES)
        ]
        self._streaks = [
            {
                'x': rng.random(), 'y': rng.random(),
                'len': rng.uniform(0.03, 0.09),
                'ang': rng.uniform(0, math.pi * 2),
                'spd': rng.uniform(0.00012, 0.00050),
                'a0': rng.uniform(0.04, 0.12),
                'col': rng.choice([CYAN, PUR]),
            }
            for _ in range(9)
        ]
        QTimer(self, timeout=self._step, interval=38).start()

    def _step(self):
        self._t += 1
        for n in self._nodes:
            n['x'] = (n['x'] + n['vx']) % 1.0
            n['y'] = (n['y'] + n['vy']) % 1.0
        for s in self._streaks:
            s['x'] = (s['x'] + math.cos(s['ang']) * s['spd']) % 1.0
            s['y'] = (s['y'] + math.sin(s['ang']) * s['spd']) % 1.0
        self.update()

    def paintEvent(self, _):
        if self.width() < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        diag = math.hypot(w, h)
        t = self._t * 0.05

        # streaks
        for s in self._streaks:
            c = _a(s['col'], s['a0'])
            p.setPen(QPen(c, 0.8))
            sx, sy = s['x'] * w, s['y'] * h
            p.drawLine(
                QPointF(sx, sy),
                QPointF(
                    sx + math.cos(s['ang']) * s['len'] * w,
                    sy + math.sin(s['ang']) * s['len'] * h,
                ),
            )

        # connections
        nodes = self._nodes
        for i, a in enumerate(nodes):
            ax, ay = a['x'] * w, a['y'] * h
            for b in nodes[i + 1:]:
                bx, by = b['x'] * w, b['y'] * h
                d = math.hypot(ax - bx, ay - by) / diag
                if d < self.MAX_DIST:
                    alpha = _cl(0.12 * (1 - d / self.MAX_DIST))
                    p.setPen(QPen(_a(CYAN, alpha), 0.6))
                    p.drawLine(QPointF(ax, ay), QPointF(bx, by))

        # nodes
        p.setPen(Qt.NoPen)
        for n in nodes:
            pulse = 0.5 + 0.5 * math.sin(t + n['ph'])
            a = _cl(n['a0'] * (0.55 + 0.45 * pulse))
            r = n['r'] * (0.8 + 0.3 * pulse)
            p.setBrush(_a(n['col'], a))
            p.drawEllipse(QPointF(n['x'] * w, n['y'] * h), r, r)


# ════════════════════════════════════════════════════════════════════════════
#  HELPER — apply dark animated background to any tab widget
# ════════════════════════════════════════════════════════════════════════════
def apply_dark_animated_bg(tab_widget):
    """
    Add the animated dark gradient and neural-field particle overlay
    behind all content in *tab_widget*.

    Call this at the **end** of _build_ui() in any tab class.
    The tab's own layout content renders on top; only the animated
    background visuals are added — no functional changes.
    """
    gradient = DarkGradientBg(tab_widget)
    neural   = NeuralFieldOverlay(tab_widget)

    # Z-order: gradient at bottom, neural above it, content on top
    gradient.lower()
    neural.lower()
    gradient.lower()

    # Size them to fill the tab
    gradient.setGeometry(0, 0, tab_widget.width(), tab_widget.height())
    neural.setGeometry(0, 0, tab_widget.width(), tab_widget.height())

    # Store refs so they don't get garbage-collected
    tab_widget._dark_gradient_bg = gradient
    tab_widget._dark_neural_field = neural

    # Hook resizeEvent to keep overlays sized correctly
    _original_resize = tab_widget.resizeEvent

    def _new_resize(event):
        w = tab_widget.width()
        h = tab_widget.height()
        gradient.setGeometry(0, 0, w, h)
        neural.setGeometry(0, 0, w, h)
        _original_resize(event)

    tab_widget.resizeEvent = _new_resize
