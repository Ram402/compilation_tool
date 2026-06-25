"""
Resolve application root and bundled resource paths for dev and PyInstaller builds.
"""

import os
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> str:
    """Directory containing application resources (theme, scripts, etc.)."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    return os.path.join(app_root(), *parts)


def scripts_dir() -> str:
    return resource_path("scripts")
