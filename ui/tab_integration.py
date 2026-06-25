"""Integration Test Tab"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QLineEdit, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from ui.widgets         import SectionBanner, SectionSep, FieldRow, ConsoleWidget, DynamicList
from ui.animated_button import AnimatedRunButton
from ui.button_styles   import BTN_ADD, BTN_SECONDARY
from ui.runner          import ScriptRunner
from ui.style_helpers   import UI_FONT, MONO_FONT
from ui.dark_bg         import apply_dark_animated_bg
from app_paths          import scripts_dir

C_RED  = "#ef4444"
C_BLUE = "#38bdf8"
C_MUTED = "#94a3b8"

_DEFAULT_SCRIPT = os.path.join(scripts_dir(), "vcast_it_manual_compilation.py")


class IntegrationTab(QWidget):
    status_changed = Signal(str, str)
    IMG = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&q=70"

    def __init__(self, run_log: list, on_run_done):
        super().__init__()
        self._run_log       = run_log
        self._on_run_done   = on_run_done
        self._runner        = None
        self._discover_mode = False
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionBanner(
            "IT COMPILATION",
            "Multi-UUT Environment · SBF Stub Injection · Retry Logic",
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
        self.f_env     = FieldRow("ENV_NAME", "e.g. CAN_Integration_ENV")
        self.f_workdir = FieldRow("WORK_DIR", "Working directory path",
                                  browse=True, browse_dir=True)
        v.addWidget(self.f_env)
        v.addWidget(self.f_workdir)

        v.addWidget(SectionSep("Base / Source"))
        self.f_basename = FieldRow("BASE_DIR_NAME", "R or R2")
        self.f_basepath = FieldRow("BASE_DIR_PATH", "Project root path",
                                   browse=True, browse_dir=True)
        self.f_hdrroot  = FieldRow("HEADER_SEARCH_ROOT",
                                   "Header search root (defaults to base path)",
                                   browse=True, browse_dir=True)
        self.f_defines  = FieldRow("DEFINES", "Space-separated defines",
                                   default="__USE_MINGW_ANSI_STDIO")
        for w in (self.f_basename, self.f_basepath, self.f_hdrroot, self.f_defines):
            v.addWidget(w)

        # Extra includes
        v.addWidget(SectionSep("Extra Includes (optional)"))
        self.f_inc1 = FieldRow("EXTRA_INCLUDE_1", "Extra include path",
                                browse=True, browse_dir=True)
        self.f_inc2 = FieldRow("EXTRA_INCLUDE_2", "Extra include path",
                                browse=True, browse_dir=True)
        self.f_inc3 = FieldRow("EXTRA_INCLUDE_3", "Extra include path",
                                browse=True, browse_dir=True)
        v.addWidget(self.f_inc1)
        v.addWidget(self.f_inc2)
        v.addWidget(self.f_inc3)

        # Additional stubs
        v.addWidget(SectionSep("Additional Stubs (optional)"))
        self.f_stubs = FieldRow("ADDITIONAL_STUBS", "Space-separated stubs",
                                default="__DI __EI")
        v.addWidget(self.f_stubs)

        # MAX_RETRIES
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
        hint.setFont(MONO_FONT(11))
        hint.setStyleSheet("color:#64748b; background:transparent; border:none;")
        retry_row.addWidget(hint)
        retry_row.addStretch()
        v.addLayout(retry_row)

        # Two-column: IT_UUTs + SBF Stubs
        v.addWidget(SectionSep("IT Units / Stubs", color="blue"))
        two_col = QHBoxLayout()
        two_col.setSpacing(24)

        left_box = QVBoxLayout()
        left_box.setSpacing(4)
        left_box.addWidget(self._col_header("IT_UUT Files (manual)", "red"))
        self.uut_list = DynamicList("e.g. CAN_Handler.c")
        self.uut_list.add_row(); self.uut_list.add_row()
        left_box.addWidget(self.uut_list)
        add_uut = QPushButton("+ Add IT_UUT")
        add_uut.setStyleSheet(BTN_ADD)
        add_uut.setCursor(Qt.PointingHandCursor)
        add_uut.clicked.connect(self.uut_list.add_row)
        left_box.addWidget(add_uut)

        right_box = QVBoxLayout()
        right_box.setSpacing(4)
        right_box.addWidget(self._col_header("SBF Stub Files", "blue"))
        self.sbf_list = DynamicList("e.g. SBF_Stub.c")
        self.sbf_list.add_row(); self.sbf_list.add_row()
        right_box.addWidget(self.sbf_list)

        stub_btn_row = QHBoxLayout()
        stub_btn_row.setSpacing(8)
        add_sbf = QPushButton("+ Add SBF Stub")
        add_sbf.setStyleSheet(BTN_ADD)
        add_sbf.setCursor(Qt.PointingHandCursor)
        add_sbf.clicked.connect(self.sbf_list.add_row)
        stub_btn_row.addWidget(add_sbf)

        self.discover_btn = QPushButton("Discover Stubs from Backtrace")
        self.discover_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #3d5472;
                border-radius: 3px;
                color: #94a3b8;
                font-family: 'Rajdhani', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1px;
                padding: 5px 14px;
                min-height: 28px;
            }
            QPushButton:hover   { border-color: #38bdf8; color: #38bdf8; background: rgba(56,189,248,0.06); }
            QPushButton:pressed { background: rgba(56,189,248,0.14); }
            QPushButton:disabled { color: #64748b; border-color: #3d5472; }
        """)
        self.discover_btn.setCursor(Qt.PointingHandCursor)
        self.discover_btn.clicked.connect(self._discover_stubs)
        stub_btn_row.addWidget(self.discover_btn)
        stub_btn_row.addStretch()
        right_box.addLayout(stub_btn_row)

        self.auto_discover_chk = QCheckBox(
            "Auto-discover stubs from backtrace on build (merges with manual list)"
        )
        self.auto_discover_chk.setChecked(True)
        self.auto_discover_chk.setFont(UI_FONT(12))
        self.auto_discover_chk.setStyleSheet(
            f"color:{C_MUTED}; background:transparent; border:none;"
        )
        right_box.addWidget(self.auto_discover_chk)

        two_col.addLayout(left_box, 1)
        two_col.addLayout(right_box, 1)
        v.addLayout(two_col)

        v.addSpacing(24)
        self.console = ConsoleWidget("IT COMPILE OUTPUT")
        v.addWidget(self.console)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 20, 0, 0)
        btn_row.setSpacing(12)

        self.run_btn = AnimatedRunButton("  Run IT Compilation", color="green")
        self.run_btn.clicked.connect(self._run)
        btn_row.addWidget(self.run_btn)

        self.stop_btn = AnimatedRunButton("  Stop", color="red")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self.stop_btn)

        clr_btn = QPushButton("Clear Console")
        clr_btn.setStyleSheet(BTN_SECONDARY)
        clr_btn.setCursor(Qt.PointingHandCursor)
        clr_btn.setFixedHeight(46)
        clr_btn.clicked.connect(self.console.clear)
        btn_row.addWidget(clr_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)
        v.addStretch()

        # Apply dark gradient + neural field animation background
        apply_dark_animated_bg(self)

    @staticmethod
    def _col_header(title: str, accent: str) -> QWidget:
        w = QWidget()
        w.setFixedHeight(32)
        w.setStyleSheet("background:#263347; border:1px solid #3d5472; border-radius:3px;")
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel(title.upper())
        lbl.setFont(UI_FONT(11, bold=True))
        c = C_RED if accent == "red" else C_BLUE
        lbl.setStyleSheet(f"color:{c}; letter-spacing:2px; background:transparent; border:none;")
        h.addWidget(lbl)
        return w

    def _get_retries(self):
        try:
            return max(1, min(1000, int(self.f_retries.text())))
        except ValueError:
            return 100

    def _base_overrides(self, uuts, sbfs):
        env_name = self.f_env.value()
        work_dir = self.f_workdir.value()
        base_path = self.f_basepath.value()
        hdr_root = self.f_hdrroot.value() or base_path
        defines_str = self.f_defines.value()
        defines_list = defines_str.split() if defines_str else ["__USE_MINGW_ANSI_STDIO"]
        stubs_str = self.f_stubs.value()
        stubs_list = stubs_str.split() if stubs_str else []

        return {
            "VECTORCAST_DIR":     self.f_vcast.value(),
            "ENV_NAME":           env_name,
            "WORK_DIR":           work_dir,
            "BASE_DIR_NAME":      self.f_basename.value(),
            "BASE_DIR_PATH":      base_path,
            "HEADER_SEARCH_ROOT": hdr_root,
            "IT_UUTS":            uuts,
            "IT_SBFS":            sbfs,
            "DEFINES":            defines_list,
            "ADDITIONAL_STUBS":   stubs_list,
            "EXTRA_INCLUDE_1":    self.f_inc1.value(),
            "EXTRA_INCLUDE_2":    self.f_inc2.value(),
            "EXTRA_INCLUDE_3":    self.f_inc3.value(),
            "MAX_RETRY_ROUNDS":   self._get_retries(),
            "AUTO_DISCOVER_STUBS": self.auto_discover_chk.isChecked(),
        }

    @staticmethod
    def _parse_discovered_stubs(console_text: str) -> list:
        """Extract merged stub filenames from script output."""
        stubs = []
        for line in console_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("• ") and "Merged SBF" not in console_text:
                continue
            if "[DISCOVER]" in stripped and "Total:" not in stripped:
                # format: [DISCOVER] File.c  (calls ...)
                rest = stripped.split("[DISCOVER]", 1)[-1].strip()
                name = rest.split("(", 1)[0].strip()
                if name.lower().endswith(".c"):
                    stubs.append(name)
        return stubs

    def _apply_discovered_stubs(self, console_text: str):
        """Merge backtrace-discovered stubs into the SBF list, deduped."""
        discovered = self._parse_discovered_stubs(console_text)
        if not discovered:
            # Fall back to merged list printed under "Merged SBF stub list:"
            in_section = False
            for line in console_text.splitlines():
                if "Merged SBF stub list" in line:
                    in_section = True
                    continue
                if in_section:
                    if line.strip().startswith("• "):
                        name = line.strip()[2:].strip()
                        if name.lower().endswith(".c"):
                            discovered.append(name)
                    elif line.strip() and not line.strip().startswith("["):
                        break

        manual = self.sbf_list.values()
        merged = []
        seen = set()
        uut_keys = {os.path.splitext(u)[0].lower() for u in self.uut_list.values()}

        for raw in manual + discovered:
            name = raw.strip()
            if not name:
                continue
            if not name.lower().endswith(".c"):
                name += ".c"
            stem = os.path.splitext(name)[0].lower()
            if stem in uut_keys or stem in seen:
                continue
            seen.add(stem)
            merged.append(name)

        self.sbf_list.set_values(merged)

    def _discover_stubs(self):
        if self._runner and self._runner.isRunning():
            return

        script_path = _DEFAULT_SCRIPT
        if not os.path.isfile(script_path):
            QMessageBox.warning(self, "Missing Script",
                                f"Compile script not found: {script_path}")
            return

        uuts = self.uut_list.values()
        if not uuts:
            QMessageBox.warning(self, "No IT_UUTs",
                                "Add at least one IT_UUT file before discovering stubs.")
            return

        hdr_root = self.f_hdrroot.value() or self.f_basepath.value()
        if not hdr_root:
            QMessageBox.warning(self, "Missing Field",
                                "BASE_DIR_PATH or HEADER_SEARCH_ROOT is required for backtrace.")
            return

        overrides = self._base_overrides(uuts, self.sbf_list.values())
        overrides["DISCOVER_STUBS_ONLY"] = True
        overrides["AUTO_DISCOVER_STUBS"] = True

        self._discover_mode = True
        self.console.clear()
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("Discovering...")
        self.stop_btn.setEnabled(True)
        self.status_changed.emit("Discovering stubs...", "amber")

        self._runner = ScriptRunner(
            name="IT Stub Discovery",
            script_path=script_path,
            overrides=overrides,
            parent=self,
        )
        self._runner.log_line.connect(self.console.append)
        self._runner.finished.connect(self._on_discover_done)
        self._runner.start()

    def _on_discover_done(self, passed, elapsed, name):
        self._apply_discovered_stubs(self.console.get_text())
        self.discover_btn.setEnabled(True)
        self.discover_btn.setText("Discover Stubs from Backtrace")
        self.stop_btn.setEnabled(False)
        self.status_changed.emit("Idle", "green")
        self._discover_mode = False
        if not passed:
            QMessageBox.warning(self, "Discovery Failed",
                                "Stub discovery did not complete successfully.\n"
                                "Check the console output for details.")

    def _run(self):
        if self._runner and self._runner.isRunning():
            return

        script_path = _DEFAULT_SCRIPT
        if not os.path.isfile(script_path):
            QMessageBox.warning(self, "Missing Script",
                                f"Compile script not found: {script_path}")
            return

        uuts = self.uut_list.values()
        if not uuts:
            QMessageBox.warning(self, "No IT_UUTs", "Add at least one IT_UUT entry.")
            return

        env_name = self.f_env.value()
        work_dir = self.f_workdir.value()
        base_name = self.f_basename.value()
        if not env_name:
            QMessageBox.warning(self, "Missing Field", "ENV_NAME is required.")
            return
        if not work_dir:
            QMessageBox.warning(self, "Missing Field", "WORK_DIR is required.")
            return
        if not base_name:
            QMessageBox.warning(self, "Missing Field", "BASE_DIR_NAME is required.")
            return

        sbfs = self.sbf_list.values()
        overrides = self._base_overrides(uuts, sbfs)
        overrides["DISCOVER_STUBS_ONLY"] = False

        name = f"IT ({len(uuts)} UUTs)"
        self.console.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("  Running...")
        self.stop_btn.setEnabled(True)
        self.status_changed.emit("Running...", "amber")

        self._rec = {
            "tab": "IT Compilation", "name": name,
            "start": datetime.now(), "elapsed": "0s", "status": "RUN", "output": ""
        }
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

    def _on_done(self, passed, elapsed, name):
        stopped = getattr(self._runner, "_stopped", False)
        self._rec["status"]  = "STOPPED" if stopped else ("PASS" if passed else "FAIL")
        self._rec["elapsed"] = f"{elapsed:.1f}s"
        self._rec["output"]  = self.console.get_text()
        self._run_log.insert(0, self._rec)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("  Run IT Compilation")
        self.stop_btn.setEnabled(False)
        self.status_changed.emit("Idle", "green")
        self._on_run_done()
