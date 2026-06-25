"""Safe UTF-8 stdout/stderr setup for Windows consoles and subprocess pipes."""

import io
import sys


def ensure_utf8_stdio() -> None:
    """Re-encode stdout/stderr as UTF-8 without double-wrapping.

    Wrapping an already-wrapped TextIOWrapper closes the shared underlying
    buffer when the old wrapper is garbage-collected, which causes
    ``ValueError: I/O operation on closed file`` on later print() calls.
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding == "utf8":
            continue
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue
        setattr(
            sys,
            name,
            io.TextIOWrapper(
                buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            ),
        )
