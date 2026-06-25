"""
Centralised button style strings — applied inline so they work
regardless of stylesheet loading order.
"""

# ── colours ──────────────────────────────────────────────────────────────────
_RED    = "#ef4444"
_RED_DK = "#dc2626"
_BLUE   = "#38bdf8"
_BLUE_DK= "#0ea5e9"
_DARK3  = "#2e3f56"
_BORDER = "#3d5472"
_METAL  = "#cbd5e1"
_MUTED  = "#94a3b8"
_BLACK  = "#1e293b"
_ERRCLR = "#f87171"

# ── style strings ─────────────────────────────────────────────────────────────
BTN_PRIMARY = f"""
    QPushButton {{
        background: {_RED};
        border: none;
        border-radius: 4px;
        color: #ffffff;
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 12px 32px;
        min-height: 46px;
    }}
    QPushButton:hover  {{ background: {_RED_DK}; }}
    QPushButton:pressed{{ background: #dc2626; border: 2px solid #ffffff; }}
    QPushButton:disabled {{ background: #7f1d1d; color: #fca5a5; }}
"""

BTN_BLUE = f"""
    QPushButton {{
        background: {_BLUE};
        border: none;
        border-radius: 4px;
        color: {_BLACK};
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 10px 28px;
        min-height: 36px;
    }}
    QPushButton:hover  {{ background: {_BLUE_DK}; }}
    QPushButton:pressed{{ background: #0ea5e9; border: 2px solid #ffffff; }}
    QPushButton:disabled {{ background: #075985; color: #bae6fd; }}
"""

BTN_BROWSE = f"""
    QPushButton {{
        background: {_DARK3};
        border: 1px solid {_BORDER};
        border-radius: 3px;
        color: {_BLUE};
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 11px;
        padding: 6px 12px;
        min-height: 28px;
    }}
    QPushButton:hover  {{ background: rgba(0,180,216,0.14); border-color: {_BLUE}; }}
    QPushButton:pressed{{ background: rgba(0,180,216,0.25); }}
"""

BTN_ADD = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid #0369a1;
        border-radius: 3px;
        color: {_BLUE};
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 11px;
        padding: 5px 12px;
    }}
    QPushButton:hover  {{ background: rgba(0,180,216,0.1); border-color: {_BLUE}; }}
    QPushButton:pressed{{ background: rgba(0,180,216,0.2); }}
"""

BTN_DEL = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid rgba(255,77,109,0.35);
        border-radius: 3px;
        color: {_ERRCLR};
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 11px;
        padding: 3px 7px;
    }}
    QPushButton:hover  {{ background: rgba(255,77,109,0.14); border-color: {_ERRCLR}; }}
    QPushButton:pressed{{ background: rgba(255,77,109,0.28); }}
"""

BTN_CLEAR_RED = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid rgba(230,57,70,0.35);
        border-radius: 3px;
        color: #7f1d1d;
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        font-size: 13px;
        font-weight: 600;
        padding: 7px 16px;
    }}
    QPushButton:hover  {{ border-color: {_RED}; color: {_RED}; }}
    QPushButton:pressed{{ background: rgba(230,57,70,0.1); }}
"""

BTN_CLEAR_LOGS = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid rgba(255,77,109,0.35);
        border-radius: 3px;
        color: {_ERRCLR};
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 13px;
    }}
    QPushButton:hover  {{ background: rgba(255,77,109,0.12); border-color: {_ERRCLR}; }}
    QPushButton:pressed{{ background: rgba(255,77,109,0.25); }}
"""

BTN_SECONDARY = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {_BORDER};
        border-radius: 3px;
        color: {_METAL};
        font-family: 'Rajdhani', 'Segoe UI', sans-serif;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 1px;
        padding: 10px 20px;
        min-height: 46px;
    }}
    QPushButton:hover  {{ border-color: {_BLUE}; color: {_BLUE}; background: rgba(0,180,216,0.06); }}
    QPushButton:pressed{{ background: rgba(0,180,216,0.14); }}
"""
