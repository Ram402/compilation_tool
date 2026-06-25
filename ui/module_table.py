"""ModuleTable — editable two-column table: UUT_NAME | UUT_FILE"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QLineEdit, QPushButton, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt

from ui.button_styles   import BTN_DEL
from ui.style_helpers   import UI_FONT

C_DARK2  = "#263347"
C_BORDER = "#3d5472"
C_TEXT   = "#f1f5f9"
C_METAL  = "#cbd5e1"


class ModuleTable(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"background:#1e293b; border:1px solid {C_BORDER}; border-radius:4px;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            f"background:{C_DARK2}; border-bottom:1px solid {C_BORDER}; border-radius:0;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(14, 0, 14, 0)
        hh.setSpacing(8)
        for col_name in ("UUT_NAME", "UUT_FILE", ""):
            lbl = QLabel(col_name)
            lbl.setFont(UI_FONT(11, bold=True))
            lbl.setStyleSheet(
                f"color:{C_METAL}; letter-spacing:2px; background:transparent; border:none;")
            if col_name == "":
                lbl.setFixedWidth(40)
            else:
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            hh.addWidget(lbl)
        outer.addWidget(hdr)

        # Scrollable rows
        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("background:transparent; border:none;")
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidget(self._rows_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setMinimumHeight(200)
        scroll.setMaximumHeight(480)
        outer.addWidget(scroll)

        self.add_row()

    def add_row(self, name: str = "", file: str = ""):
        row = _ModuleRow(name, file, on_delete=self._remove_row)
        self._rows_layout.addWidget(row)

    def _remove_row(self, row):
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        if self._rows_layout.count() == 0:
            self.add_row()

    def clear_all(self):
        if QMessageBox.question(self, "Clear Modules", "Remove all modules?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            while self._rows_layout.count():
                item = self._rows_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.add_row()

    def get_values(self):
        rows = []
        for i in range(self._rows_layout.count()):
            item = self._rows_layout.itemAt(i)
            if item and item.widget():
                n, f = item.widget().values()
                if n or f:
                    rows.append((n, f))
        return rows


class _ModuleRow(QWidget):
    def __init__(self, name: str, file: str, on_delete):
        super().__init__()
        self.setFixedHeight(48)
        self.setStyleSheet(
            "background:transparent; border:none;"
            f"border-bottom:1px solid {C_BORDER};")
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(8)

        _field_style = (
            f"background:rgba(0,0,0,0.15); border:1px solid {C_BORDER}; border-radius:3px; padding: 0 8px;"
            f"color:{C_TEXT}; font-family:'Rajdhani','Segoe UI',sans-serif; font-size:14px;"
        )
        from PySide6.QtGui import QPalette, QColor as _QC
        _ph_color = _QC(C_METAL)

        self._name = QLineEdit(name)
        self._name.setPlaceholderText("ABS_Control")
        self._name.setStyleSheet(_field_style)
        _p1 = self._name.palette(); _p1.setColor(QPalette.PlaceholderText, _ph_color)
        self._name.setPalette(_p1)

        self._file = QLineEdit(file)
        self._file.setPlaceholderText("ABS_Control.c")
        self._file.setStyleSheet(_field_style)
        _p2 = self._file.palette(); _p2.setColor(QPalette.PlaceholderText, _ph_color)
        self._file.setPalette(_p2)

        del_btn = QPushButton("X")
        del_btn.setStyleSheet(BTN_DEL)
        del_btn.setFixedSize(28, 24)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda: on_delete(self))

        h.addWidget(self._name, 1)
        h.addWidget(self._file, 1)
        h.addWidget(del_btn)

    def values(self):
        return self._name.text().strip(), self._file.text().strip()
