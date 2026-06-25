"""
Module Summary Tab — scan source tree, preview module inventory, then generate Excel.

Features
--------
* Source root path + browse
* Output directory + browse (defaults to source root)
* Scan & Preview — walks the tree in a background thread, fills the summary
  table with one ROW PER .c FILE (Module No. + Folder only on first file of
  each module; subsequent files in same folder leave those cells blank)
  — includes No. of Lines and Statements per file (same logic as the reference
  script: count all lines, count ';' per line)
* Generate Excel — delegates to generate_c_metrics_excel.py
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui  import QFont, QColor

from ui.widgets         import SectionBanner, SectionSep, FieldRow, ConsoleWidget
from ui.animated_button import AnimatedRunButton
from ui.button_styles   import BTN_SECONDARY
from ui.runner          import ScriptRunner
from ui.style_helpers   import UI_FONT
from ui.dark_bg         import apply_dark_animated_bg
from app_paths          import scripts_dir

# ── palette ───────────────────────────────────────────────────────────────────
C_DARK1  = "#1e293b"
C_DARK2  = "#263347"
C_DARK3  = "#2e3f56"
C_BORDER = "#3d5472"
C_RED    = "#ef4444"
C_BLUE   = "#38bdf8"
C_GREEN  = "#4ade80"
C_AMBER  = "#fbbf24"
C_MUTED  = "#94a3b8"
C_TEXT   = "#f1f5f9"
C_ERR    = "#f87171"

_DEFAULT_SCRIPT = os.path.join(scripts_dir(), "generate_c_metrics_excel.py")


# ── analysis helper (same logic as reference script) ─────────────────────────
def _analyze_c_file(file_path: str) -> tuple[int, int]:
    """Return (total_lines, statements_count) — counts ALL lines and every ';'."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        return len(lines), sum(line.count(";") for line in lines)
    except OSError:
        return 0, 0


# ── background scanner thread ─────────────────────────────────────────────────
class _ScanThread(QThread):
    """
    Walk the source tree and emit one tuple per .c file:
      (module_no, folder, c_file, line_count, stmt_count)
    module_no is None for files that are NOT the first .c file in their folder.
    """
    result_ready = Signal(list)   # list[tuple[int|None, str, str, int, int]]
    error        = Signal(str)

    def __init__(self, root_path: str, parent=None):
        super().__init__(parent)
        self._root = root_path

    def run(self):
        try:
            root = os.path.normpath(self._root)
            file_rows: list[tuple] = []

            # Collect (folder, c_file) pairs, sorted same way as the script
            raw: list[tuple[str, str]] = []
            for folder, _dirs, files in os.walk(root):
                c_files = sorted(f for f in files if f.endswith(".c"))
                for cf in c_files:
                    raw.append((folder, cf))
            raw.sort(key=lambda r: (r[0].lower(), r[1].lower()))

            mod_counter   = 0
            seen_folders: set[str] = set()

            for folder, c_file in raw:
                folder = os.path.normpath(folder)
                line_count, stmt_count = _analyze_c_file(os.path.join(folder, c_file))

                if folder not in seen_folders:
                    seen_folders.add(folder)
                    mod_counter += 1
                    mod_no = mod_counter
                else:
                    mod_no = None     # blank — same module as above

                # folder path ALWAYS included (repeated for every file in module)
                file_rows.append((mod_no, folder, c_file, line_count, stmt_count))

            self.result_ready.emit(file_rows)
        except Exception as exc:
            self.error.emit(str(exc))


# ── summary table ─────────────────────────────────────────────────────────────
class _SummaryTable(QWidget):
    """
    Styled QTableWidget — one ROW PER .c FILE:
      Module No. | Folder Path | C File | No. of Lines | Statements
    Module No. and Folder Path are blank for the 2nd+ file in each folder.
    """
    HEADERS = ["Module No.", "Folder Path", "C File", "No. of Lines", "Statements"]

    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"background:{C_DARK1}; border:1px solid {C_BORDER}; border-radius:4px;"
        )
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── toolbar ──────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(
            f"background:{C_DARK2}; border-bottom:1px solid {C_BORDER};"
        )
        th = QHBoxLayout(toolbar)
        th.setContentsMargins(14, 0, 14, 0)
        th.setSpacing(8)

        for col in ("#ff5f57", "#febc2e", "#28c840"):
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(
                f"background:{col}; border-radius:5px; border:none;"
            )
            th.addWidget(dot)
        th.addSpacing(8)

        lf = QFont("Rajdhani")
        lf.setPixelSize(11)
        lf.setBold(True)

        title_lbl = QLabel("MODULE INVENTORY")
        title_lbl.setFont(lf)
        title_lbl.setStyleSheet(
            f"color:{C_BLUE}; letter-spacing:2px; background:transparent; border:none;"
        )
        th.addWidget(title_lbl)
        th.addStretch()

        self._count_lbl = QLabel("—")
        self._count_lbl.setFont(lf)
        self._count_lbl.setStyleSheet(
            f"color:{C_MUTED}; background:transparent; border:none; letter-spacing:1px;"
        )
        th.addWidget(self._count_lbl)
        v.addWidget(toolbar)

        # ── table ─────────────────────────────────────────────────────────
        self._tbl = QTableWidget(0, len(self.HEADERS))
        self._tbl.setHorizontalHeaderLabels(self.HEADERS)
        self._tbl.setStyleSheet(f"""
            QTableWidget {{
                background: {C_DARK1};
                color: {C_TEXT};
                gridline-color: {C_BORDER};
                border: none;
                font-family: 'JetBrains Mono', 'Courier New', monospace;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: rgba(56,189,248,0.15);
                color: {C_TEXT};
            }}
            QHeaderView::section {{
                background: {C_DARK3};
                color: {C_MUTED};
                font-family: 'Rajdhani', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 2px;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid {C_BORDER};
            }}
            QScrollBar:vertical {{
                background: {C_DARK2};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {C_BORDER};
                border-radius: 4px;
            }}
        """)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setMinimumHeight(280)
        self._tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)   # Module No.
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)             # Folder Path
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # C File
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # No. of Lines
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Statements

        v.addWidget(self._tbl)

    # ── public api ─────────────────────────────────────────────────────────
    def load(self, file_rows: list[tuple]) -> None:
        """
        file_rows: list of (mod_no|None, folder, c_file, line_count, stmt_count)
        Each tuple → one table row.
        """
        self._tbl.setRowCount(0)
        n_mods  = 0
        n_files = 0

        bold_f = QFont("Rajdhani")
        bold_f.setPixelSize(12)
        bold_f.setBold(True)

        for mod_no, folder, c_file, line_count, stmt_count in file_rows:
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)

            # ── Module No. — only on first file of each module ──
            if mod_no is not None:
                mi = QTableWidgetItem(str(mod_no))
                mi.setForeground(QColor(C_AMBER))
                mi.setFont(bold_f)
                mi.setTextAlignment(Qt.AlignCenter)
                self._tbl.setItem(row, 0, mi)
                n_mods += 1
            else:
                self._tbl.setItem(row, 0, QTableWidgetItem(""))

            # ── Folder Path — ALWAYS shown on every row ──
            fi = QTableWidgetItem(folder)
            fi.setForeground(QColor(C_MUTED))
            self._tbl.setItem(row, 1, fi)

            # ── C File ──
            ci = QTableWidgetItem(c_file)
            ci.setForeground(QColor(C_BLUE))
            self._tbl.setItem(row, 2, ci)

            # ── No. of Lines ──
            li = QTableWidgetItem(str(line_count))
            li.setForeground(QColor(C_GREEN))
            li.setTextAlignment(Qt.AlignCenter)
            self._tbl.setItem(row, 3, li)

            # ── Statements ──
            si = QTableWidgetItem(str(stmt_count))
            si.setForeground(QColor(C_TEXT))
            si.setTextAlignment(Qt.AlignCenter)
            self._tbl.setItem(row, 4, si)

            n_files += 1

        self._count_lbl.setText(
            f"{n_mods} module{'s' if n_mods != 1 else ''} · "
            f"{n_files} .c file{'s' if n_files != 1 else ''}"
        )

    def clear(self):
        self._tbl.setRowCount(0)
        self._count_lbl.setText("—")


# ── main tab ──────────────────────────────────────────────────────────────────
class ModuleSummaryTab(QWidget):
    status_changed = Signal(str, str)
    IMG = "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&q=70"

    def __init__(self):
        super().__init__()
        self._runner: ScriptRunner | None = None
        self._scan_thread: _ScanThread | None = None
        self._build_ui()

    # ── build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionBanner(
            "Project Analysis",
            "Scan Source Tree · Module Inventory · Generate Project Report Excel",
            self.IMG,
        ))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll, 1)

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        scroll.setWidget(body)

        v = QVBoxLayout(body)
        v.setContentsMargins(48, 0, 48, 40)
        v.setSpacing(0)

        # ── source path ───────────────────────────────────────────────────
        v.addWidget(SectionSep("Source"))
        self.f_root = FieldRow(
            "Source root path",
            "Base path to scan for .c files",
            browse=True, browse_dir=True,
        )
        v.addWidget(self.f_root)

        # ── output path ───────────────────────────────────────────────────
        v.addWidget(SectionSep("Output"))
        self.f_output = FieldRow(
            "Output directory (optional)",
            "Leave empty to save Excel in source root path",
            browse=True, browse_dir=True,
        )
        v.addWidget(self.f_output)

        # ── info banner ───────────────────────────────────────────────────
        info = QLabel(
            "Click <b>Scan &amp; Preview</b> to walk the source tree and display "
            "each .c file on its own row with <b>No. of Lines</b> and "
            "<b>Statements</b> — then click <b>Generate Excel</b> to produce "
            "<i>Project_report.xlsx</i> with two sheets: "
            "<b>Module Summary</b> (S No · Module No. · Folder Path · C File · "
            "No. of Lines · Statements · Executable SLOC) and <b>report</b> "
            "(S NO · UT · IT · Path · C File · No. of Lines · Statements · "
            "Compilation · Actual Sloc · Remarks · Engineer Name)."
        )
        info.setFont(UI_FONT(12))
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color:{C_MUTED}; background:rgba(0,180,216,0.05);"
            f"border:1px solid rgba(0,180,216,0.2); border-radius:3px;"
            "padding:10px 14px; margin:12px 0 16px 0;"
        )
        v.addWidget(info)

        # ── scan buttons ──────────────────────────────────────────────────
        v.addSpacing(4)
        scan_row = QHBoxLayout()
        scan_row.setContentsMargins(0, 0, 0, 0)
        scan_row.setSpacing(10)

        self.scan_btn = AnimatedRunButton("  Scan & Preview", color="blue")
        self.scan_btn.clicked.connect(self._scan)
        scan_row.addWidget(self.scan_btn)

        clr_tbl_btn = QPushButton("Clear Table")
        clr_tbl_btn.setStyleSheet(BTN_SECONDARY)
        clr_tbl_btn.setCursor(Qt.PointingHandCursor)
        clr_tbl_btn.setFixedHeight(46)
        clr_tbl_btn.clicked.connect(self._clear_table)
        scan_row.addWidget(clr_tbl_btn)
        scan_row.addStretch()

        v.addLayout(scan_row)
        v.addSpacing(12)

        # ── module inventory table ────────────────────────────────────────
        self.summary_table = _SummaryTable()
        v.addWidget(self.summary_table)

        # ── console ───────────────────────────────────────────────────────
        v.addSpacing(16)
        self.console = ConsoleWidget("GENERATION OUTPUT")
        v.addWidget(self.console)

        # ── generate buttons ──────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 20, 0, 0)
        btn_row.setSpacing(12)

        self.gen_btn = AnimatedRunButton("  Generate Excel", color="green")
        self.gen_btn.clicked.connect(self._generate)
        btn_row.addWidget(self.gen_btn)

        self.stop_btn = AnimatedRunButton("  Stop", color="red")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)

        clr_con_btn = QPushButton("Clear Console")
        clr_con_btn.setStyleSheet(BTN_SECONDARY)
        clr_con_btn.setCursor(Qt.PointingHandCursor)
        clr_con_btn.setFixedHeight(46)
        clr_con_btn.clicked.connect(self.console.clear)
        btn_row.addWidget(clr_con_btn)
        btn_row.addStretch()

        v.addLayout(btn_row)

        # ── status label ──────────────────────────────────────────────────
        self.status_lbl = QLabel(
            "Ready — enter source root path and click Scan & Preview or Generate Excel."
        )
        self.status_lbl.setFont(UI_FONT(12))
        self.status_lbl.setStyleSheet(
            f"color:{C_MUTED}; padding-top:12px; border:none;"
        )
        v.addWidget(self.status_lbl)
        v.addStretch()

        # Apply dark gradient + neural field animation background
        apply_dark_animated_bg(self)

    # ── helpers ───────────────────────────────────────────────────────────
    def _set_status(self, text: str, color: str = C_MUTED):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color:{color}; padding-top:12px; border:none;"
        )

    def _validate_root(self) -> str | None:
        root = self.f_root.value()
        if not root:
            QMessageBox.warning(self, "Missing Field", "Source root path is required.")
            return None
        if not os.path.isdir(root):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Source root path does not exist:\n{root}",
            )
            return None
        return root

    # ── scan & preview ────────────────────────────────────────────────────
    def _scan(self):
        root = self._validate_root()
        if root is None:
            return
        if self._scan_thread and self._scan_thread.isRunning():
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("  Scanning...")
        self._set_status("Scanning source tree and reading .c files…", C_AMBER)
        self.summary_table.clear()

        self._scan_thread = _ScanThread(root, parent=self)
        self._scan_thread.result_ready.connect(self._on_scan_done)
        self._scan_thread.error.connect(self._on_scan_error)
        self._scan_thread.start()

    def _on_scan_done(self, file_rows: list):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("  Scan & Preview")
        if not file_rows:
            self._set_status("No .c files found under the source root.", C_ERR)
            return
        self.summary_table.load(file_rows)
        n_mods  = len({r[0] for r in file_rows if r[0] is not None})
        n_files = len(file_rows)
        self._set_status(
            f"Scan complete — {n_mods} module(s), {n_files} .c file(s) found.", C_GREEN
        )
        self.status_changed.emit("Scan complete", "green")

    def _on_scan_error(self, msg: str):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("  Scan & Preview")
        self._set_status(f"Scan failed: {msg}", C_ERR)

    def _clear_table(self):
        self.summary_table.clear()
        self._set_status(
            "Ready — enter source root path and click Scan & Preview or Generate Excel."
        )

    # ── generate excel ────────────────────────────────────────────────────
    def _generate(self):
        if self._runner and self._runner.isRunning():
            return

        root = self._validate_root()
        if root is None:
            return

        output_dir = self.f_output.value()
        if output_dir and not os.path.isdir(output_dir):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Output directory does not exist:\n{output_dir}",
            )
            return

        overrides = {"ROOT_PATH": root, "OUTPUT_DIR": output_dir}

        self.console.clear()
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Generating...")
        self.stop_btn.setEnabled(True)
        self._set_status("Scanning source tree and generating Excel…", C_AMBER)
        self.status_changed.emit("Generating Excel...", "amber")

        self._runner = ScriptRunner(
            name="C Metrics Excel",
            script_path=_DEFAULT_SCRIPT,
            overrides=overrides,
            parent=self,
        )
        self._runner.log_line.connect(self.console.append)
        self._runner.finished.connect(self._on_done)
        self._runner.start()

    def _stop(self):
        if self._runner and self._runner.isRunning():
            self.stop_btn.setEnabled(False)
            self._runner.stop()

    def _on_done(self, passed: bool, elapsed: float, name: str):
        stopped = getattr(self._runner, "_stopped", False)
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("  Generate Excel")
        self.stop_btn.setEnabled(False)

        if stopped:
            self._set_status("Generation cancelled.", C_ERR)
            self.status_changed.emit("Idle", "green")
            return

        if passed:
            out_dir  = self.f_output.value() or self.f_root.value()
            out_file = os.path.join(out_dir, "Project_report.xlsx")
            self._set_status(f"Excel generated: {out_file}", C_GREEN)
            QMessageBox.information(
                self, "Excel Generated",
                f"Excel saved successfully:\n\n{out_file}\n\n"
                f"Completed in {elapsed:.1f}s\n\n"
                "The workbook contains two sheets:\n"
                "  • Module Summary — one row per .c file with No. of Lines, Statements, "
                "and Executable SLOC (filled after UT Compilation)\n"
                "  • report — full detail report with UT / IT / compilation columns",
            )
        else:
            self._set_status("Generation failed — see console for details.", C_ERR)

        self.status_changed.emit("Idle", "green")
