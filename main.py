"""
VectorCAST — Automotive Software Verification Suite
PySide6 Desktop Application
"""

import multiprocessing
import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

from app_paths import resource_path
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VectorCAST")
    app.setOrganizationName("Automotive Verification Suite")

    for font_name in ("Rajdhani.ttf", "BebasNeue.ttf", "JetBrainsMono.ttf"):
        font_file = resource_path("assets", font_name)
        if os.path.exists(font_file):
            QFontDatabase.addApplicationFont(font_file)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
