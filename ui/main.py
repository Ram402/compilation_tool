"""
VectorCAST — Automotive Software Verification Suite
PySide6 Desktop Application
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VectorCAST")
    app.setOrganizationName("Automotive Verification Suite")

    # High-DPI (attribute removed in Qt6 — it's always on)
    # app.setAttribute(Qt.AA_UseHighDpiPixmaps)  # deprecated, skip

    # Load bundled fonts if present — silently skip if missing
    import os
    for font_file in ("assets/Rajdhani.ttf", "assets/BebasNeue.ttf", "assets/JetBrainsMono.ttf"):
        if os.path.exists(font_file):
            QFontDatabase.addApplicationFont(font_file)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
