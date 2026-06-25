"""Generate Excel Tab — scan source tree for .c file metrics."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from ui.widgets         import SectionBanner, SectionSep, FieldRow, ConsoleWidget
from ui.animated_button import AnimatedRunButton
from ui.button_styles   import BTN_SECONDARY
from ui.runner          import ScriptRunner
from ui.style_helpers   import UI_FONT
from ui.dark_bg         import apply_dark_animated_bg
from app_paths          import scripts_dir

C_MUTED = "#94a3b8"
C_GREEN = "#4ade80"
C_ERR   = "#f87171"

_DEFAULT_SCRIPT = os.path.join(scripts_dir(), "generate_c_metrics_excel.py")


class GenerateExcelTab(QWidget):
    status_changed = Signal(str, str)
    IMG = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=70"

    def __init__(self):
        super().__init__()
        self._runner = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(SectionBanner(
            "GENERATE EXCEL",
            "Scan Source Tree · Module & .c File Inventory · Line & Statement Metrics",
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

        v.addWidget(SectionSep("Source"))
        self.f_root = FieldRow(
            "Source root path",
            "Base path to scan for .c files",
            browse=True, browse_dir=True,
        )
        v.addWidget(self.f_root)

        v.addWidget(SectionSep("Output"))
        self.f_output = FieldRow(
            "Output directory (optional)",
            "Leave empty to save Excel in source root path",
            browse=True, browse_dir=True,
        )
        v.addWidget(self.f_output)

        info = QLabel(
            "Scans every folder under the source root (same logic as the metrics script) "
            "and creates Project_report.xlsx with two sheets: Module Summary and report. "
            "The report sheet columns are: S NO, UT, IT, Path, C File, "
            "No. of Lines, Statements, Compilation, Actual Sloc, Remarks, Engineer Name. "
            "Line and statement counts are filled automatically; UT / Compilation / "
            "Actual Sloc / Remarks / Engineer Name are left blank for manual entry."
        )
        info.setFont(UI_FONT(12))
        info.setWordWrap(True)
        info.setStyleSheet(
            "color:#94a3b8; background:rgba(0,180,216,0.05);"
            "border:1px solid rgba(0,180,216,0.2); border-radius:3px;"
            "padding:10px 14px; margin:12px 0 16px 0;"
        )
        v.addWidget(info)

        v.addSpacing(8)
        self.console = ConsoleWidget("GENERATION OUTPUT")
        v.addWidget(self.console)

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

        clr_btn = QPushButton("Clear Console")
        clr_btn.setStyleSheet(BTN_SECONDARY)
        clr_btn.setCursor(Qt.PointingHandCursor)
        clr_btn.setFixedHeight(46)
        clr_btn.clicked.connect(self.console.clear)
        btn_row.addWidget(clr_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        self.status_lbl = QLabel("Ready — enter source root path and click Generate Excel.")
        self.status_lbl.setFont(UI_FONT(12))
        self.status_lbl.setStyleSheet(f"color:{C_MUTED}; padding-top:12px; border:none;")
        v.addWidget(self.status_lbl)
        v.addStretch()

        # Apply dark gradient + neural field animation background
        apply_dark_animated_bg(self)

    def _generate(self):
        if self._runner and self._runner.isRunning():
            return

        root_path = self.f_root.value().strip()
        if not root_path:
            QMessageBox.warning(self, "Missing Field", "Source root path is required.")
            return
        if not os.path.isdir(root_path):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Source root path does not exist:\n{root_path}",
            )
            return

        output_dir = self.f_output.value().strip()
        if output_dir and not os.path.isdir(output_dir):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Output directory does not exist:\n{output_dir}",
            )
            return

        overrides = {
            "ROOT_PATH": root_path,
            "OUTPUT_DIR": output_dir,
        }

        self.console.clear()
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("  Generating...")
        self.stop_btn.setEnabled(True)
        self.status_lbl.setText("Scanning source tree...")
        self.status_lbl.setStyleSheet(f"color:#fbbf24; padding-top:12px; border:none;")
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
            self.status_lbl.setText("Generation cancelled.")
            self.status_lbl.setStyleSheet(f"color:{C_ERR}; padding-top:12px; border:none;")
            self.status_changed.emit("Idle", "green")
            return

        if passed:
            out_dir = self.f_output.value().strip() or self.f_root.value().strip()
            out_file = os.path.join(out_dir, "Project_report.xlsx")
            self.status_lbl.setText(f"Excel generated: {out_file}")
            self.status_lbl.setStyleSheet(f"color:{C_GREEN}; padding-top:12px; border:none;")
            QMessageBox.information(
                self, "Excel Generated",
                f"Excel saved successfully:\n\n{out_file}\n\n"
                f"Completed in {elapsed:.1f}s",
            )
        else:
            self.status_lbl.setText("Generation failed — see console for details.")
            self.status_lbl.setStyleSheet(f"color:{C_ERR}; padding-top:12px; border:none;")

        self.status_changed.emit("Idle", "green")
