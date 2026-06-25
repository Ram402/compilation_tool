"""Logs Tab"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QEvent

from ui.widgets         import SectionBanner, ConsoleWidget, StatusBadge
from ui.button_styles   import BTN_CLEAR_LOGS
from ui.style_helpers   import UI_FONT, MONO_FONT
from ui.dark_bg         import apply_dark_animated_bg

C_DARK1  = "#1e293b"
C_DARK2  = "#263347"
C_BORDER = "#3d5472"
C_MUTED  = "#94a3b8"
C_METAL  = "#cbd5e1"
C_RED    = "#ef4444"
C_GREEN  = "#4ade80"
C_ERRCLR = "#f87171"
C_AMBER  = "#fbbf24"


class LogsTab(QWidget):
    IMG = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=70"

    def __init__(self, run_log: list, on_clear=None):
        super().__init__()
        self._run_log = run_log
        self._on_clear = on_clear
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionBanner(
            "LOGS",
            "Run History · Console Output · Compilation Records",
            self.IMG
        ))

        toolbar = QWidget()
        toolbar.setFixedHeight(46)
        toolbar.setStyleSheet(f"background:{C_DARK2}; border-bottom:1px solid {C_BORDER};")
        th = QHBoxLayout(toolbar)
        th.setContentsMargins(48, 0, 24, 0)

        hdr = QLabel("RUN HISTORY")
        hdr.setFont(UI_FONT(11, bold=True))
        hdr.setStyleSheet(f"color:{C_METAL}; letter-spacing:2px; border:none;")
        th.addWidget(hdr)
        th.addStretch()

        self.clr_btn = QPushButton("Clear History")
        self.clr_btn.setStyleSheet(BTN_CLEAR_LOGS)
        self.clr_btn.setCursor(Qt.PointingHandCursor)
        self.clr_btn.setFixedHeight(30)
        self.clr_btn.clicked.connect(self._clear_logs)
        th.addWidget(self.clr_btn)
        outer.addWidget(toolbar)

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        outer.addWidget(split, 1)

        # Left — history list
        left = QWidget()
        left.setStyleSheet("background:rgba(30,45,61,0.3);")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        col_hdr = QWidget()
        col_hdr.setFixedHeight(34)
        col_hdr.setStyleSheet(f"background:{C_DARK2}; border-bottom:1px solid {C_BORDER};")
        ch = QHBoxLayout(col_hdr)
        ch.setContentsMargins(16, 0, 16, 0)
        for txt, w in (("TIME", 130), ("TAB", None), ("DUR", 70), ("STATUS", 60)):
            lbl = QLabel(txt)
            lbl.setFont(UI_FONT(10, bold=True))
            lbl.setStyleSheet(f"color:{C_METAL}; letter-spacing:2px; border:none;")
            if w:
                lbl.setFixedWidth(w)
            else:
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            ch.addWidget(lbl)
        lv.addWidget(col_hdr)

        self._list = QListWidget()
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setStyleSheet(
            "QListWidget { background:transparent; border:none; outline:none; }"
            f"QListWidget::item {{ padding:0; border-bottom:1px solid rgba(30,45,61,0.4); }}"
            f"QListWidget::item:hover {{ background:rgba(46,63,86,0.6); }}"
            f"QListWidget::item:selected {{"
            f"  background:rgba(46,63,86,0.8); border-left:2px solid {C_RED}; }}"
        )
        self._list.currentRowChanged.connect(self._on_row_select)
        self._list.viewport().installEventFilter(self)
        lv.addWidget(self._list)
        split.addWidget(left)

        # Right — console
        right = QWidget()
        right.setStyleSheet("background:transparent;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.console = ConsoleWidget("SELECTED RUN OUTPUT")
        rv.addWidget(self.console)
        split.addWidget(right)

        split.setSizes([460, 900])
        self.console.append("// No runs yet. Execute a compilation to see history.", "dim")

        # Apply dark gradient + neural field animation background
        apply_dark_animated_bg(self)

    def refresh(self):
        self._list.clear()
        if not self._run_log:
            self.console.clear()
            self.console.append("// No runs yet. Execute a compilation to see history.", "dim")
            return
        for rec in self._run_log:
            item, row_w = self._make_item(rec)
            self._list.addItem(item)
            self._list.setItemWidget(item, row_w)
        self._resize_list_items()
        self._list.setCurrentRow(0)

    def _make_item(self, rec: dict) -> tuple[QListWidgetItem, QWidget]:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, rec)

        row_w = QWidget()
        row_w.setFixedHeight(44)
        row_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_w.setStyleSheet("background:transparent; border:none;")
        rh = QHBoxLayout(row_w)
        rh.setContentsMargins(16, 0, 16, 0)
        rh.setSpacing(8)

        time_lbl = QLabel(rec["start"].strftime("%H:%M:%S  %d/%m"))
        time_lbl.setFont(MONO_FONT(11))
        time_lbl.setFixedWidth(130)
        time_lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent; border:none;")
        rh.addWidget(time_lbl)

        tab_lbl = QLabel(rec.get("tab", ""))
        tab_lbl.setFont(UI_FONT(13, bold=True))
        tab_lbl.setStyleSheet(f"color:{C_METAL}; background:transparent; border:none;")
        tab_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rh.addWidget(tab_lbl)

        dur_lbl = QLabel(rec.get("elapsed", "-"))
        dur_lbl.setFont(MONO_FONT(11))
        dur_lbl.setFixedWidth(70)
        dur_lbl.setAlignment(Qt.AlignCenter)
        dur_lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent; border:none;")
        rh.addWidget(dur_lbl)

        badge = StatusBadge(rec.get("status", "RUN"))
        rh.addWidget(badge)

        return item, row_w

    def _resize_list_items(self):
        width = max(self._list.viewport().width(), 1)
        for i in range(self._list.count()):
            item = self._list.item(i)
            row_w = self._list.itemWidget(item)
            if row_w:
                row_w.setFixedWidth(width)
                item.setSizeHint(QSize(width, 44))

    def eventFilter(self, obj, event):
        if obj is self._list.viewport() and event.type() == QEvent.Resize:
            self._resize_list_items()
        return super().eventFilter(obj, event)

    def _on_row_select(self, row: int):
        if row < 0 or row >= len(self._run_log):
            return
        self._show_output(self._run_log[row])

    def _show_output(self, rec: dict):
        self.console.clear()
        status = rec.get("status", "RUN")
        kind   = "ok" if status == "PASS" else "err"
        header = (
            f"Run - {rec.get('tab', '')}\n"
            f"Started: {rec['start'].strftime('%Y-%m-%d %H:%M:%S')}  "
            f"Duration: {rec.get('elapsed', '-')}  Status: {status}\n"
            f"{'=' * 60}"
        )
        self.console.append(header, kind)
        if rec.get("output"):
            self.console.append(rec["output"], "")

    def _clear_logs(self):
        if not self._run_log:
            return
        if QMessageBox.question(self, "Clear Logs", "Clear all log history?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._run_log.clear()
            self.refresh()
            if self._on_clear:
                self._on_clear()
