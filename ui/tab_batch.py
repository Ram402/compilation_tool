"""UT Compilation Tab"""

import os
import re
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QMessageBox, QLabel, QLineEdit
)
from PySide6.QtCore import Qt, Signal

from ui.widgets         import SectionBanner, SectionSep, FieldRow, ConsoleWidget
from ui.animated_button import AnimatedRunButton
from ui.button_styles   import BTN_ADD, BTN_CLEAR_RED, BTN_SECONDARY
from ui.runner          import ScriptRunner
from ui.module_table    import ModuleTable
from ui.style_helpers   import UI_FONT, MONO_FONT
from ui.dark_bg         import apply_dark_animated_bg
from app_paths          import scripts_dir

C_MUTED = "#94a3b8"

_DEFAULT_SCRIPT = os.path.join(scripts_dir(), "vcast_batch_compile.py")


class BatchTab(QWidget):
    status_changed = Signal(str, str)
    IMG = "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=1200&q=70"

    def __init__(self, run_log: list, on_run_done):
        super().__init__()
        self._run_log     = run_log
        self._on_run_done = on_run_done
        self._runner      = None
        self.imported_excel_path = ""
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionBanner(
            "UT COMPILATION",
            "One or Multi-Module Compilation · Per-Module Pass/Fail Dashboard",
            self.IMG
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

        v.addWidget(SectionSep("VectorCAST"))
        self.f_vcast = FieldRow("VectorCAST dir", r"C:\VCAST",
                                default=r"C:\VCAST", browse=True, browse_dir=True)
        v.addWidget(self.f_vcast)

        v.addWidget(SectionSep("Environment"))
        self.f_workdir = FieldRow("WORKSPACE_ROOT", "Workspace root directory",
                                  browse=True, browse_dir=True)
        v.addWidget(self.f_workdir)

        v.addWidget(SectionSep("Base / Source"))
        self.f_basename = FieldRow("BASE_DIR_NAME", "R or R2")
        self.f_basepath = FieldRow("BASE_DIR_PATH", "Project root path",
                                   browse=True, browse_dir=True)
        self.f_hdrroot  = FieldRow("HEADER_SEARCH_ROOT",
                                   "Header search root (defaults to base path)",
                                   browse=True, browse_dir=True)
        self.f_defines  = FieldRow("DEFINES (space-sep)", "Space-separated defines",
                                   default="__USE_MINGW_ANSI_STDIO")
        for w in (self.f_basename, self.f_basepath, self.f_hdrroot, self.f_defines):
            v.addWidget(w)

        retry_row = QHBoxLayout()
        retry_row.setContentsMargins(0, 6, 0, 0)
        retry_row.setSpacing(12)

        lbl = QLabel("MAX_RETRIES")
        lbl.setFont(UI_FONT(12, bold=True))
        lbl.setFixedWidth(220)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet(f"color:{C_MUTED}; background:transparent; border:none;")
        retry_row.addWidget(lbl)

        self.f_retries = QLineEdit("100")
        self.f_retries.setPlaceholderText("1 – 1000")
        self.f_retries.setFixedWidth(100)
        retry_row.addWidget(self.f_retries)

        hint = QLabel("(1 – 1000)")
        hint.setFont(UI_FONT(12))
        hint.setStyleSheet("color:#64748b; background:transparent; border:none;")
        retry_row.addWidget(hint)
        retry_row.addStretch()
        v.addLayout(retry_row)

        v.addWidget(SectionSep("Modules"))
        self.module_table = ModuleTable()
        v.addWidget(self.module_table)

        tbl_btns = QHBoxLayout()
        tbl_btns.setContentsMargins(0, 8, 0, 0)
        tbl_btns.setSpacing(8)

        add_btn = QPushButton("+ Add Row")
        add_btn.setStyleSheet(BTN_ADD)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.module_table.add_row)
        tbl_btns.addWidget(add_btn)

        clr_btn2 = QPushButton("Clear All")
        clr_btn2.setStyleSheet(BTN_CLEAR_RED)
        clr_btn2.setCursor(Qt.PointingHandCursor)
        clr_btn2.clicked.connect(self.module_table.clear_all)
        tbl_btns.addWidget(clr_btn2)
        tbl_btns.addStretch()
        v.addLayout(tbl_btns)

        v.addSpacing(24)
        self.console = ConsoleWidget("UT COMPILE OUTPUT")
        v.addWidget(self.console)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 20, 0, 0)
        btn_row.setSpacing(12)

        self.run_btn = AnimatedRunButton("  Run UT Compilation", color="green")
        self.run_btn.clicked.connect(self._run)
        btn_row.addWidget(self.run_btn)

        self.stop_btn = AnimatedRunButton("  Stop", color="red")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)

        clr_btn3 = QPushButton("Clear Console")
        clr_btn3.setStyleSheet(BTN_SECONDARY)
        clr_btn3.setCursor(Qt.PointingHandCursor)
        clr_btn3.setFixedHeight(46)
        clr_btn3.clicked.connect(self.console.clear)
        btn_row.addWidget(clr_btn3)
        btn_row.addStretch()
        v.addLayout(btn_row)
        v.addStretch()

        # Apply dark gradient + neural field animation background
        apply_dark_animated_bg(self)

    # ── public API ────────────────────────────────────────────────────────────
    def set_modules(self, modules: list, replace: bool = True):
        """Load modules directly without showing any confirmation dialog."""
        if replace:
            self._clear_table_silent()
        for name, file in modules:
            self.module_table.add_row(name, file)
        if self.module_table._rows_layout.count() == 0:
            self.module_table.add_row()

    def _clear_table_silent(self):
        """Clear all rows silently — no dialog, used by Excel import."""
        layout = self.module_table._rows_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def get_modules(self):
        return self.module_table.get_values()

    def _get_retries(self):
        try:
            return max(1, min(1000, int(self.f_retries.text())))
        except ValueError:
            return 100

    # ── run ───────────────────────────────────────────────────────────────────
    def _run(self):
        if self._runner and self._runner.isRunning():
            return

        script_path = _DEFAULT_SCRIPT
        if not os.path.isfile(script_path):
            QMessageBox.warning(self, "Missing Script",
                                f"Compile script not found: {script_path}")
            return

        mods = self.module_table.get_values()
        if not mods:
            QMessageBox.warning(self, "No Modules", "Add at least one module first.")
            return

        workspace_root = self.f_workdir.value()
        if not workspace_root:
            QMessageBox.warning(self, "Missing Field", "WORKSPACE_ROOT is required.")
            return

        base_name = self.f_basename.value()
        if not base_name:
            QMessageBox.warning(self, "Missing Field", "BASE_DIR_NAME is required.")
            return

        base_path = self.f_basepath.value()
        hdr_root  = self.f_hdrroot.value() or base_path

        # Parse defines — space-separated list, with default fallback
        defines_str  = self.f_defines.value()
        defines_list = defines_str.split() if defines_str else ["__USE_MINGW_ANSI_STDIO"]

        normalized = []
        for n, f in mods:
            uut = (n or "").strip()
            if not uut:
                continue
            cfile = (f or "").strip()
            if not cfile:
                cfile = f"{uut}.c"
            else:
                cfile = os.path.basename(cfile)
                if not cfile.lower().endswith(".c"):
                    cfile = f"{cfile}.c"
            normalized.append((uut, cfile))

        if not normalized:
            QMessageBox.warning(self, "No Valid Modules",
                                "Please add at least one module with a UUT name.")
            return

        overrides = {
            "VECTORCAST_DIR":     self.f_vcast.value(),
            "BASE_DIR_NAME":      base_name,
            "BASE_DIR_PATH":      base_path,
            "HEADER_SEARCH_ROOT": hdr_root,
            "WORKSPACE_ROOT":     workspace_root,
            "MAX_RETRY_ROUNDS":   self._get_retries(),
            "MODULES":            normalized,
            "DEFINES":            defines_list,
            "IMPORTED_EXCEL_PATH": getattr(self, "imported_excel_path", ""),
        }

        # Store normalized list for per-module result parsing
        self._normalized_modules = normalized
        self._batch_start        = datetime.now()

        name = f"UT Compilation ({len(normalized)} modules)"
        self.console.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("  Running...")
        self.stop_btn.setEnabled(True)
        self.status_changed.emit("Running...", "amber")

        self._runner = ScriptRunner(
            name=name,
            script_path=script_path,
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

    # ── parse per-module results from console output ──────────────────────────
    def _parse_module_results(self, console_text: str, normalized: list):
        """
        Build one result record per module in *normalized* (the authoritative list).

        Strategy — three passes in priority order:
          1. Summary table lines  (✓/✗/~ + PASS/FAIL/SKIP)
          2. Per-module Result: lines emitted during compilation
          3. Guaranteed fallback  — any module not found in passes 1/2 is
             marked FAIL so the total always equals len(normalized).

        Returns list of (uut_stem, c_file, status, elapsed_s) in the same
        order as *normalized*.
        """
        lines = console_text.splitlines()

        # ── Pass 1: summary table ─────────────────────────────────────────
        # Matches:  ✓ Stem   File.c   PASS   12s
        #           ✗ Stem   File.c   FAIL    3s
        #           ~ Stem   File.c   SKIP –  file not found   -
        # The icon may be the unicode chars or ASCII > / < / ~ after
        # toPlainText() strips HTML.  Accept any single non-space char.
        table_re = re.compile(
            r'^\s*\S\s+(\S+)\s+(\S+\.c)\s+(PASS|FAIL|SKIP\S*)\s+(\S+)',
            re.IGNORECASE
        )
        table_hits: dict[str, tuple[str, float]] = {}   # uut_lower -> (status, secs)
        for line in lines:
            m = table_re.match(line)
            if m:
                uut, _cfile, status, tstr = m.groups()
                try:
                    secs = float(tstr.rstrip("s"))
                except ValueError:
                    secs = 0.0
                st = status.upper()
                if st.startswith("SKIP"):
                    st = "FAIL"   # treat skip as fail per requirements
                table_hits[uut.lower()] = (st, secs)

        # ── Pass 2: inline Result: lines  ─────────────────────────────────
        # Emitted as:  Result: PASS  (elapsed: 45s)
        #              Result: FAIL  (elapsed: 3s)
        # Each is preceded by a MODULE N/M line naming the current module.
        module_re = re.compile(
            r'\[MODULE\s+\d+/\d+\]\s+(\S+)', re.IGNORECASE)
        result_re = re.compile(
            r'Result:\s*(PASS|FAIL)', re.IGNORECASE)
        time_re   = re.compile(
            r'elapsed[:\s]+(\d+(?:\.\d+)?)s', re.IGNORECASE)

        inline_hits: dict[str, tuple[str, float]] = {}
        current_uut = None
        for line in lines:
            mm = module_re.search(line)
            if mm:
                current_uut = mm.group(1)
            rm = result_re.search(line)
            if rm and current_uut:
                tm = time_re.search(line)
                secs = float(tm.group(1)) if tm else 0.0
                inline_hits[current_uut.lower()] = (rm.group(1).upper(), secs)
                current_uut = None   # reset; don't double-assign

        # ── Merge: one record per input module ────────────────────────────
        results = []
        for uut_stem, c_file in normalized:
            key = uut_stem.lower()
            if key in table_hits:
                status, secs = table_hits[key]
            elif key in inline_hits:
                status, secs = inline_hits[key]
            else:
                # Module ran but output couldn't be parsed → mark FAIL
                status, secs = "FAIL", 0.0
            results.append((uut_stem, c_file, status, secs))

        return results

    # ── finished ──────────────────────────────────────────────────────────────
    def _on_done(self, passed: bool, elapsed: float, name: str):
        console_text   = self.console.get_text()
        normalized     = getattr(self, "_normalized_modules", [])
        module_results = self._parse_module_results(console_text, normalized)
        now            = datetime.now()

        if module_results:
            # One log record per module — total always equals number of .c files
            # "tab" is set to the .c filename so the Logs tab shows the file name
            for uut, cfile, status, mod_secs in reversed(module_results):
                rec = {
                    "tab":     cfile,        # .c filename as the log label
                    "name":    uut,          # just the UUT stem, no extra text
                    "start":   self._batch_start,
                    "elapsed": f"{mod_secs:.0f}s",
                    "status":  status,       # already PASS / FAIL
                    "output":  console_text,
                }
                self._run_log.insert(0, rec)
        else:
            # Should never reach here if normalized is non-empty, but keep as safety net
            self._run_log.insert(0, {
                "tab":     "UT Compilation",
                "name":    "UT Run",
                "start":   self._batch_start,
                "elapsed": f"{elapsed:.1f}s",
                "status":  "PASS" if passed else "FAIL",
                "output":  console_text,
            })

        self.run_btn.setEnabled(True)
        self.run_btn.setText("  Run UT Compilation")
        self.stop_btn.setEnabled(False)
        self.status_changed.emit("Idle", "green")
        self._on_run_done()
