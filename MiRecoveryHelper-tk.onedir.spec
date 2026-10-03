# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: **tkinter-only** onedir build (no %TEMP% dependency).

Same rationale as MiRecoveryHelper-tk.spec, but collected into a folder instead
of a single file. Nothing is unpacked at startup, so it is immune to both
"Could not create temporary directory!" and a nearly-full system disk.

    pyinstaller --noconfirm MiRecoveryHelper-tk.onedir.spec
    # -> dist/MiRecoveryHelper/MiRecoveryHelper.exe
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve()
DATA_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "kb.json"
REFS_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "image_refs.json"
ICON_FILE = PROJECT_ROOT / "src" / "mirecovery" / "resources" / "icon.ico"
RES_DIR = PROJECT_ROOT / "src" / "mirecovery" / "resources"

if not DATA_FILE.is_file():
    raise SystemExit(
        f"缺少知识库数据文件 {DATA_FILE}，请先运行：python tools/build_kb.py"
    )

datas = [(str(DATA_FILE), "mirecovery/data")]
if REFS_FILE.is_file():
    datas.append((str(REFS_FILE), "mirecovery/data"))
for asset in ("character_sheet.jpg", "icon.png", "window_icon.png"):
    if (RES_DIR / asset).is_file():
        datas.append((str(RES_DIR / asset), "mirecovery/resources"))

os.environ["MIRECOVERY_GUI"] = "tk"

a = Analysis(  # noqa: F821
    [str(PROJECT_ROOT / "src" / "launcher.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "mirecovery",
        "mirecovery.tkapp",
        "mirecovery.theme",
        "mirecovery.kb",
        "mirecovery.scanner",
        "mirecovery.report",
        "mirecovery.recognize",
        "mirecovery.imagefeatures",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "toga",
        "toga_winforms",
        "pythonnet",
        "clr_loader",
        "WebView2",
        "dotnet_webview2_winforms",
        "numpy",
        "test",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MiRecoveryHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON_FILE) if ICON_FILE.is_file() else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MiRecoveryHelper",
)
