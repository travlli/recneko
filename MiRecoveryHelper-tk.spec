# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: **tkinter-only** single-file exe (the recommended build).

Why this is the primary artifact
--------------------------------
Toga's Windows backend (``toga-winforms``) requires ``pythonnet``, which ships
only x86/x64 ``Python.Runtime.dll``. On Windows on ARM the interpreter is
ARM64, so the native backend can never initialise there:

    RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize ...

``toga-webview2`` does not exist on PyPI and ``pywebview`` depends on pythonnet
too, so there is no Toga-based escape. Tkinter, by contrast, is part of the
standard library, is bundled with this Python (Tk 8.6), and runs on ARM64.

Leaving the Toga stack out therefore buys three things: it works on ARM64, it
starts faster, and the bundle is much smaller.

    pyinstaller --noconfirm MiRecoveryHelper-tk.spec
    # -> dist/MiRecoveryHelper.exe
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
# Original character sheet shown inside the window, plus icon assets.
for asset in ("character_sheet.jpg", "icon.png", "window_icon.png"):
    if (RES_DIR / asset).is_file():
        datas.append((str(RES_DIR / asset), "mirecovery/resources"))

# The launcher probes Toga; make sure it goes straight to tkinter.
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
        # Toga stack: unusable on ARM64 and pointless here.
        "toga",
        "toga_winforms",
        "pythonnet",
        "clr_loader",
        "WebView2",
        "dotnet_webview2_winforms",
        # Optional accelerator only; zncc() has an equivalent pure-Python path.
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
    a.binaries,
    a.datas,
    [],
    name="MiRecoveryHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON_FILE) if ICON_FILE.is_file() else None,
)
