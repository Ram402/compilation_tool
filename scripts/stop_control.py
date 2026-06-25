"""Cooperative cancellation for long-running VectorCAST compilation scripts."""

import os
import sys

_stop_file: str = ""


def configure(stop_file: str) -> None:
    """Set the stop-flag file path and clear any previous request."""
    global _stop_file
    _stop_file = stop_file or ""
    clear()


def clear() -> None:
    if _stop_file and os.path.isfile(_stop_file):
        try:
            os.remove(_stop_file)
        except OSError:
            pass


def is_requested() -> bool:
    return bool(_stop_file) and os.path.isfile(_stop_file)


def check(label: str = "") -> None:
    """Raise SystemExit(2) when the UI has requested a stop."""
    if is_requested():
        msg = "[STOPPED] Compilation cancelled by user"
        if label:
            msg += f" ({label})"
        print(msg, flush=True)
        raise SystemExit(2)
