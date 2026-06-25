"""
Main Window — VectorCAST Automotive Suite
Implements: Hero Header, Stats Bar, Tab Navigation, Footer
"""

import os
import time
from datetime import datetime

from app_paths import resource_path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QFrame, QSizePolicy,
    QApplication, QStatusBar
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QLinearGradient,
    QBrush, QPen, QFontDatabase
)

from ui.widgets import (
    AccentStrip, HeroHeader, StatsBar, FooterBar, SectionBanner
)
from ui.tab_module_summary  import ModuleSummaryTab
from ui.tab_batch           import BatchTab
from ui.tab_integration     import IntegrationTab
from ui.tab_excel           import ExcelTab
from ui.tab_logs            import LogsTab
from ui.tab_home            import HomeTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VectorCAST — Automotive Compilation Tool")
        self.setMinimumSize(1200, 800)
        self.resize(1440, 900)

        # Shared run log (list of dicts)
        self.run_log = []

        self._load_theme()
        self._build_ui()
        self._start_clock()

    # ── theme ──────────────────────────────────────────────────────────────
    def _load_theme(self):
        qss_path = resource_path("theme.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except (FileNotFoundError, OSError):
            pass   # graceful fallback — no stylesheet

    # ── UI ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # ── Top accent strip (red→orange→blue, 3 px) ──
        vbox.addWidget(AccentStrip())

        # ── Hero header with automotive background ──
        self.hero = HeroHeader()
        vbox.addWidget(self.hero)

        # ── Stats bar ──
        self.stats_bar = StatsBar()
        vbox.addWidget(self.stats_bar)

        # ── Tab widget ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        vbox.addWidget(self.tabs, 1)

        # Home tab (index 0)
        def switch_to_tab(index):
            """Callback for HomeTab feature cards — index is 1-based card id."""
            self.tabs.setCurrentIndex(index)   # card indexes match tab indexes

        self.home_tab = HomeTab(switch_to_tab)
        self.tabs.addTab(self.home_tab, "Home")

        # Instantiate all tabs
        self.mod_summary_tab  = ModuleSummaryTab()
        self.batch_tab        = BatchTab(      run_log=self.run_log, on_run_done=self._on_run_done)
        self.it_tab           = IntegrationTab(run_log=self.run_log, on_run_done=self._on_run_done)
        self.excel_tab        = ExcelTab(      batch_tab=self.batch_tab,
                                              switch_to_batch=lambda: self.tabs.setCurrentIndex(2))
        self.logs_tab         = LogsTab(       run_log=self.run_log, on_clear=self._reset_stats)

        self.tabs.addTab(self.mod_summary_tab, "Project Analysis")
        self.tabs.addTab(self.batch_tab,       "UT Compilation")
        self.tabs.addTab(self.it_tab,          "IT Compilation")
        self.tabs.addTab(self.excel_tab,       "Import Excel")
        self.tabs.addTab(self.logs_tab,        "Logs")

        # ── Footer ──
        self.footer = FooterBar()
        vbox.addWidget(self.footer)

        # Wire status updates from each tab
        for tab in (self.mod_summary_tab, self.batch_tab, self.it_tab):
            tab.status_changed.connect(self.footer.set_status)

    # ── clock ──────────────────────────────────────────────────────────────
    def _start_clock(self):
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)

    def _tick(self):
        self.footer.set_time(datetime.now().strftime("%H:%M:%S"))

    # ── run callback ───────────────────────────────────────────────────────
    def _on_run_done(self):
        """Called by any tab when a run finishes — refreshes stats + logs."""
        total = len(self.run_log)
        passed = sum(1 for r in self.run_log if r.get("status") == "PASS")
        failed = sum(1 for r in self.run_log if r.get("status") == "FAIL")
        secs   = sum(float(str(r.get("elapsed", 0)).rstrip("s") or 0) for r in self.run_log)
        mins   = int(secs // 60)
        rem    = int(secs % 60)
        time_str = f"{mins}m {rem}s" if mins else f"{secs:.0f}s"

        self.stats_bar.update_stats(total, passed, failed, time_str)
        self.logs_tab.refresh()

    def _reset_stats(self):
        """Called when the user clears log history — zeros all stats counters."""
        self.stats_bar.update_stats(0, 0, 0, "0s")
