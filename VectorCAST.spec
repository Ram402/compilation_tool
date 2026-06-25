# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — VectorCAST Automotive Compilation Tool

import os

block_cipher = None
project_dir = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(project_dir, "theme.qss"), "."),
    (os.path.join(project_dir, "scripts"), "scripts"),
    (os.path.join(project_dir, "c_backtrace.py"), "."),
]

assets_dir = os.path.join(project_dir, "assets")
if os.path.isdir(assets_dir):
    datas.append((assets_dir, "assets"))

hiddenimports = [
    "openpyxl",
    "openpyxl.styles",
    "c_backtrace",
    "app_paths",
]

a = Analysis(
    [os.path.join(project_dir, "main.py")],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VectorCAST",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='vcast_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VectorCAST",
)
