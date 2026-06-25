"""
Custom Widgets — VectorCAST Automotive Suite
All button styles applied inline (not via QSS objectName) for guaranteed visibility.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame,
    QPushButton, QLineEdit, QTextEdit, QScrollArea,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import (
    QPainter, QColor, QLinearGradient, QBrush, QPixmap, QFont
)
import urllib.request, threading

from ui.button_styles import (
    BTN_BROWSE, BTN_DEL, BTN_SECONDARY
)


# ── colours ───────────────────────────────────────────────────────────────────
C_BLACK  = "#1e293b"
C_DARK1  = "#1e293b"
C_DARK2  = "#263347"
C_DARK3  = "#2e3f56"
C_BORDER = "#3d5472"
C_RED    = "#ef4444"
C_BLUE   = "#38bdf8"
C_GREEN  = "#4ade80"
C_AMBER  = "#fbbf24"
C_ERRCLR = "#f87171"
C_TEXT   = "#f1f5f9"
C_MUTED  = "#94a3b8"
C_METAL  = "#cbd5e1"


# ─────────────────────────────────────────────────────────────────────────────
# FONT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _display_font(size: int) -> QFont:
    f = QFont("Bebas Neue")
    if not f.exactMatch(): f = QFont("Impact")
    f.setPixelSize(size)
    return f

def _ui_font(size: int, bold: bool = False) -> QFont:
    f = QFont("Rajdhani")
    if not f.exactMatch(): f = QFont("Segoe UI")
    f.setPixelSize(size)
    f.setBold(bold)
    return f

def _mono_font(size: int) -> QFont:
    f = QFont("JetBrains Mono")
    if not f.exactMatch(): f = QFont("Courier New")
    f.setPixelSize(size)
    return f


# ─────────────────────────────────────────────────────────────────────────────
# ACCENT STRIP
# ─────────────────────────────────────────────────────────────────────────────
class AccentStrip(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(3)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.0, QColor(C_RED))
        g.setColorAt(0.5, QColor("#ff6b35"))
        g.setColorAt(1.0, QColor(C_BLUE))
        p.fillRect(self.rect(), QBrush(g))


# ─────────────────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────────────────
class HeroHeader(QWidget):
    BG_URL = "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200&q=70"

    def __init__(self):
        super().__init__()
        self.setFixedHeight(140)
        self._pixmap = None
        self._fetch_bg()
        self._build_overlay()

    def _build_overlay(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(48, 0, 48, 0)
        h.setAlignment(Qt.AlignVCenter)

        brand = QVBoxLayout()
        brand.setSpacing(3)
        brand.setAlignment(Qt.AlignVCenter)

        name_lbl = QLabel("VECTORCAST")
        name_lbl.setFont(_display_font(52))
        name_lbl.setStyleSheet(f"color:{C_RED}; letter-spacing:4px; background:transparent;")
        brand.addWidget(name_lbl)

        sub_lbl = QLabel("AUTOMOTIVE COMPILATION TOOL")
        sub_lbl.setFont(_ui_font(11, bold=True))
        sub_lbl.setStyleSheet(f"color:{C_MUTED}; letter-spacing:4px; background:transparent;")
        brand.addWidget(sub_lbl)

        h.addLayout(brand)
        h.addStretch()

        #pills = QHBoxLayout()
        #pills.setSpacing(8)
        #pills.setAlignment(Qt.AlignVCenter)
        #for text in ("UT", "BATCH", "IT", "EXCEL", "LOGS"):
            #p = QLabel(text)
            #p.setFont(_mono_font(10))
            #p.setAlignment(Qt.AlignCenter)
            #p.setFixedHeight(28)
            #p.setContentsMargins(14, 0, 14, 0)
            #p.setStyleSheet(
             #   f"color:{C_METAL}; background:rgba(30,41,59,0.8);"
             #   f"border:1px solid {C_BORDER}; border-radius:2px; letter-spacing:1px;"
            #)
            #pills.addWidget(p)
        #h.addLayout(pills)

    def _fetch_bg(self):
        def worker():
            try:
                req = urllib.request.Request(self.BG_URL, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=5).read()
                px = QPixmap()
                px.loadFromData(data)
                if not px.isNull():
                    self._pixmap = px
                    self.update()
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width()  - scaled.width())  // 2
            y = (self.height() - scaled.height()) // 2
            p.setOpacity(0.35)
            p.drawPixmap(x, y, scaled)
            p.setOpacity(1.0)
        else:
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0, QColor("#1e293b"))
            g.setColorAt(1, QColor("#1e293b"))
            p.fillRect(self.rect(), QBrush(g))
        ov = QLinearGradient(0, 0, self.width(), 0)
        ov.setColorAt(0.0, QColor(30, 41, 59, 240))
        ov.setColorAt(0.5, QColor(30, 41, 59, 153))
        ov.setColorAt(1.0, QColor(30, 41, 59, 216))
        p.fillRect(self.rect(), QBrush(ov))


# ─────────────────────────────────────────────────────────────────────────────
# STATS BAR — no border lines on numbers, correct colors, big display font
# ─────────────────────────────────────────────────────────────────────────────
class StatCell(QWidget):
    """
    One stat cell. Top 2-px colored accent bar.
    Number colored to match the accent. NO border/underline on the number label.
    """
    COLOURS = {
        "total": C_METAL,
        "pass":  C_GREEN,
        "fail":  C_ERRCLR,
        "time":  C_BLUE,
    }

    def __init__(self, kind: str, label: str):
        super().__init__()
        self._kind  = kind
        self._color = self.COLOURS.get(kind, C_METAL)

        # No stylesheet on self — pure paintEvent background
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 12)
        v.setSpacing(4)
        v.setAlignment(Qt.AlignCenter)

        # Label — small uppercase muted
        lbl = QLabel(label.upper())
        lbl.setAlignment(Qt.AlignCenter)
        lf = _ui_font(10, bold=True)
        lbl.setFont(lf)
        # Explicitly NO border, NO background — pure text
        lbl.setStyleSheet(
            f"color:{C_MUTED}; letter-spacing:2px;"
            "background:transparent; border:none; padding:0; margin:0;"
        )
        v.addWidget(lbl)

        # Value — big display number
        self.value_lbl = QLabel("0")
        self.value_lbl.setAlignment(Qt.AlignCenter)
        vf = _display_font(38)
        self.value_lbl.setFont(vf)
        # Explicitly NO border, NO background — just colored text
        self.value_lbl.setStyleSheet(
            f"color:{self._color};"
            "background:transparent; border:none; padding:0; margin:0;"
        )
        v.addWidget(self.value_lbl)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(76)

    def set_value(self, val):
        self.value_lbl.setText(str(val))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Dark background
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C_DARK2))
        p.drawRect(self.rect())
        # Top 2-px accent bar (color matches the number)
        p.setBrush(QColor(self._color))
        p.drawRect(0, 0, self.width(), 2)
        # Right 1-px separator (subtle)
        p.setBrush(QColor(C_BORDER))
        p.drawRect(self.width() - 1, 2, 1, self.height() - 2)


class StatsBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(76)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self._total = StatCell("total", "Total Compilations")
        self._pass  = StatCell("pass",  "Passed")
        self._fail  = StatCell("fail",  "Failed")
        self._time  = StatCell("time",  "Total Time")

        for cell in (self._total, self._pass, self._fail, self._time):
            h.addWidget(cell)

    def update_stats(self, total, passed, failed, time_str):
        self._total.set_value(total)
        self._pass.set_value(passed)
        self._fail.set_value(failed)
        self._time.set_value(time_str)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BANNER
# ─────────────────────────────────────────────────────────────────────────────
class SectionBanner(QWidget):
    def __init__(self, title: str, subtitle: str, img_url: str):
        super().__init__()
        self.setFixedHeight(110)
        self._pixmap  = None
        self._img_url = img_url
        self._fetch_bg()
        self._build_overlay(title, subtitle)

    def _build_overlay(self, title, subtitle):
        h = QHBoxLayout(self)
        h.setContentsMargins(48, 0, 0, 0)
        h.setAlignment(Qt.AlignVCenter)

        block = QVBoxLayout()
        block.setSpacing(4)
        block.setAlignment(Qt.AlignVCenter)

        title_lbl = QLabel(title)
        title_lbl.setFont(_display_font(36))
        title_lbl.setStyleSheet(
            "color:#ffffff; letter-spacing:3px; background:transparent; border:none;")
        block.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle.upper())
        sub_lbl.setFont(_ui_font(11, bold=True))
        sub_lbl.setStyleSheet(
            f"color:{C_MUTED}; letter-spacing:2px; background:transparent; border:none;")
        block.addWidget(sub_lbl)

        h.addLayout(block)
        h.addStretch()

    def _fetch_bg(self):
        def worker():
            try:
                req = urllib.request.Request(self._img_url, headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=5).read()
                px = QPixmap()
                px.loadFromData(data)
                if not px.isNull():
                    self._pixmap = px
                    self.update()
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width()  - scaled.width())  // 2
            y = (self.height() - scaled.height()) // 2
            p.setOpacity(0.30)
            p.drawPixmap(x, y, scaled)
            p.setOpacity(1.0)
        else:
            p.fillRect(self.rect(), QColor(C_DARK1))
        ov = QLinearGradient(0, 0, self.width(), 0)
        ov.setColorAt(0.0, QColor(30, 41, 59, 250))
        ov.setColorAt(0.5, QColor(30, 41, 59, 180))
        ov.setColorAt(1.0, QColor(30, 41, 59, 0))
        p.fillRect(self.rect(), QBrush(ov))


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER BAR
# ─────────────────────────────────────────────────────────────────────────────
class FooterBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(46)
        self.setStyleSheet(f"background:{C_DARK1}; border-top:1px none {C_BORDER};")

        h = QHBoxLayout(self)
        #h.setContentsMargins(48, 0, 48, 0)

        left = QLabel("VECTORCAST  -  AUTOMOTIVE COMPILATION TOOL")
        left.setFont(_ui_font(11, bold=True))
        left.setStyleSheet(f"color:{C_MUTED}; letter-spacing:2px; border:none;")
        h.addWidget(left)
        h.addStretch()

        self._dot = _PulseDot()
        h.addWidget(self._dot)

        self._status = QLabel("Idle")
        self._status.setFont(_mono_font(11))
        self._status.setStyleSheet(f"color:{C_GREEN}; border:none;")
        h.addWidget(self._status)

        h.addSpacing(24)

        self._time_lbl = QLabel("--:--:--")
        self._time_lbl.setFont(_mono_font(11))
        self._time_lbl.setStyleSheet(f"color:{C_MUTED}; border:none;")
        h.addWidget(self._time_lbl)

    def set_status(self, text: str, colour: str = "green"):
        colours = {"green": C_GREEN, "amber": C_AMBER, "red": C_ERRCLR}
        c = colours.get(colour, C_GREEN)
        self._status.setText(text)
        self._status.setStyleSheet(f"color:{c}; border:none;")
        self._dot.set_color(c)

    def set_time(self, t: str):
        self._time_lbl.setText(t)


class _PulseDot(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(10, 10)
        self._color = QColor(C_GREEN)
        self._alpha = 255
        t = QTimer(self)
        t.timeout.connect(self._pulse)
        t.start(33)
        self._dir = -4

    def _pulse(self):
        self._alpha += self._dir
        if self._alpha <= 100: self._dir =  4
        if self._alpha >= 255: self._dir = -4
        self.update()

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(self._color)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 8, 8)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION SEPARATOR
# ─────────────────────────────────────────────────────────────────────────────
class SectionSep(QWidget):
    def __init__(self, label: str, color: str = "red"):
        super().__init__()
        self.setFixedHeight(36)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 10, 0, 6)
        h.setSpacing(12)

        c = C_RED if color == "red" else C_BLUE

        tick = QFrame()
        tick.setFixedSize(32, 2)
        tick.setStyleSheet(f"background:{c}; border:none;")
        h.addWidget(tick, 0, Qt.AlignVCenter)

        lbl = QLabel(label.upper())
        lbl.setFont(_ui_font(11, bold=True))
        lbl.setStyleSheet(f"color:{c}; letter-spacing:3px; background:transparent; border:none;")
        h.addWidget(lbl)

        rest = QFrame()
        rest.setFrameShape(QFrame.HLine)
        rest.setStyleSheet(f"color:{C_BORDER}; border:none;")
        rest.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h.addWidget(rest, 1)


# ─────────────────────────────────────────────────────────────────────────────
# FIELD ROW — inline browse button styles
# ─────────────────────────────────────────────────────────────────────────────
class FieldRow(QWidget):
    def __init__(self, label: str, placeholder: str = "", default: str = "",
                 browse: bool = False, browse_dir: bool = False):
        super().__init__()
        self.setFixedHeight(38)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 3, 0, 3)
        h.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(_ui_font(12, bold=True))
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setFixedWidth(220)
        lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent; border:none;")
        h.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setFont(_ui_font(13))
        self.edit.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255,255,255,0.04);
                border: 1px solid {C_BORDER};
                border-radius: 3px;
                color: {C_TEXT};
                font-family: 'Rajdhani', 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 3px 8px;
            }}
            QLineEdit:focus {{
                border-color: {C_BLUE};
                background: rgba(255,255,255,0.07);
            }}
            QLineEdit[readOnly="true"] {{
                color: {C_MUTED};
            }}
        """)
        # Placeholder colour — slightly dimmer than real text but same font
        palette = self.edit.palette()
        from PySide6.QtGui import QPalette, QColor as _QC
        palette.setColor(QPalette.PlaceholderText, _QC(C_MUTED))
        self.edit.setPalette(palette)
        if default:
            self.edit.setText(default)
        h.addWidget(self.edit, 1)

        if browse:
            btn = QPushButton("Browse")
            btn.setStyleSheet(BTN_BROWSE)
            btn.setFixedWidth(80)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda: self._browse_dir() if browse_dir else self._browse_file()
            )
            h.addWidget(btn)
        else:
            sp = QWidget(); sp.setFixedWidth(80)
            h.addWidget(sp)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path: self.edit.setText(path)

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path: self.edit.setText(path)

    def value(self): return self.edit.text().strip()
    def set_value(self, v): self.edit.setText(v)


# ─────────────────────────────────────────────────────────────────────────────
# CONSOLE WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class ConsoleWidget(QWidget):
    def __init__(self, title: str = "COMPILE OUTPUT"):
        super().__init__()
        self.setStyleSheet(
            f"background:#1a2942; border:1px solid {C_BORDER}; border-radius:4px;")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        toolbar = QWidget()
        toolbar.setFixedHeight(34)
        toolbar.setStyleSheet(
            f"background:{C_DARK2}; border-bottom:1px solid {C_BORDER};")
        th = QHBoxLayout(toolbar)
        th.setContentsMargins(12, 0, 12, 0)

        for col in ("#ff5f57", "#febc2e", "#28c840"):
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background:{col}; border-radius:5px; border:none;")
            th.addWidget(dot)
        th.addSpacing(8)

        t_lbl = QLabel(title)
        t_lbl.setFont(_ui_font(11, bold=True))
        t_lbl.setStyleSheet(f"color:{C_BLUE}; letter-spacing:2px; background:transparent; border:none;")
        th.addWidget(t_lbl)
        th.addStretch()

        clr = QPushButton("Clear")
        clr.setStyleSheet(BTN_BROWSE)
        clr.setFixedHeight(22)
        clr.setCursor(Qt.PointingHandCursor)
        clr.clicked.connect(self.clear)
        th.addWidget(clr)

        v.addWidget(toolbar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setMinimumHeight(220)
        v.addWidget(self._text)

    def clear(self): self._text.clear()

    def append(self, text: str, kind: str = ""):
        colours = {
            "ok":   C_GREEN,  "err": C_ERRCLR,
            "info": C_BLUE,   "warn": C_AMBER,
            "dim":  "#64748b",
        }
        c = colours.get(kind, C_TEXT)
        escaped = (text
                   .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                   .replace("\n", "<br>").replace(" ", "&nbsp;"))
        self._text.append(
            f'<span style="color:{c};font-family:\'JetBrains Mono\','
            f'monospace;font-size:12px;">{escaped}</span>')
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def get_text(self): return self._text.toPlainText()


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC LIST
# ─────────────────────────────────────────────────────────────────────────────
class DynamicList(QWidget):
    def __init__(self, placeholder: str = ""):
        super().__init__()
        self._placeholder = placeholder
        self.setStyleSheet(
            f"border:1px solid {C_BORDER}; border-radius:4px; background:{C_DARK1};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("border:none; background:transparent;")
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        outer.addWidget(self._rows_widget)

    def add_row(self, value: str = ""):
        row = _DynRow(self._placeholder, value, on_delete=lambda r: self._remove(r))
        self._rows_layout.addWidget(row)

    def _remove(self, row):
        self._rows_layout.removeWidget(row)
        row.deleteLater()

    def values(self):
        result = []
        for i in range(self._rows_layout.count()):
            item = self._rows_layout.itemAt(i)
            if item and item.widget():
                v = item.widget().value()
                if v: result.append(v)
        return result

    def set_values(self, values: list):
        """Replace all rows with the given values (deduped, non-empty)."""
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        seen = set()
        for raw in values or []:
            v = (raw or "").strip()
            if not v:
                continue
            key = v.lower()
            if key in seen:
                continue
            seen.add(key)
            self.add_row(v)
        if self._rows_layout.count() == 0:
            self.add_row()


class _DynRow(QWidget):
    def __init__(self, placeholder, value, on_delete):
        super().__init__()
        self.setFixedHeight(36)
        self.setStyleSheet(
            "background:transparent; border:none;"
            "border-bottom:1px solid rgba(30,45,61,0.5);")
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(8)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        if value: self._edit.setText(value)
        self._edit.setStyleSheet(
            "background:transparent; border:1px solid transparent; border-radius:2px;"
            f"color:{C_TEXT}; font-family:'JetBrains Mono',monospace; font-size:12px;")
        h.addWidget(self._edit)

        btn = QPushButton("X")
        btn.setStyleSheet(BTN_DEL)
        btn.setFixedSize(28, 24)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: on_delete(self))
        h.addWidget(btn)

    def value(self): return self._edit.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
# STATUS BADGE
# ─────────────────────────────────────────────────────────────────────────────
class StatusBadge(QLabel):
    STYLES = {
        "PASS": f"background:rgba(45,198,83,0.15); color:{C_GREEN}; border:1px solid rgba(45,198,83,0.3);",
        "FAIL": f"background:rgba(255,77,109,0.15); color:{C_ERRCLR}; border:1px solid rgba(255,77,109,0.3);",
        "RUN":  f"background:rgba(244,162,97,0.15); color:{C_AMBER}; border:1px solid rgba(244,162,97,0.3);",
    }

    def __init__(self, status: str = "RUN"):
        super().__init__(status)
        self.setFont(_ui_font(11, bold=True))
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(56)
        self._set(status)

    def _set(self, status: str):
        base = "padding:2px 6px; border-radius:2px; letter-spacing:1px;"
        self.setStyleSheet(base + self.STYLES.get(status, self.STYLES["RUN"]))
        self.setText(status)

    def set_status(self, s): self._set(s)
