"""Font helpers for consistent typography across all tabs."""
from PySide6.QtGui import QFont


def UI_FONT(size: int = 13, bold: bool = False) -> QFont:
    f = QFont("Rajdhani")
    if not f.exactMatch():
        f = QFont("Segoe UI")
    f.setPixelSize(size)
    f.setBold(bold)
    return f


def MONO_FONT(size: int = 12) -> QFont:
    f = QFont("JetBrains Mono")
    if not f.exactMatch():
        f = QFont("Courier New")
    f.setPixelSize(size)
    return f


def DISPLAY_FONT(size: int = 32) -> QFont:
    f = QFont("Bebas Neue")
    if not f.exactMatch():
        f = QFont("Impact")
    f.setPixelSize(size)
    return f
