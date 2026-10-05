# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: **tkinter-only** single-file exe (the primary build).

Why tkinter and not Toga
------------------------
Toga's Windows backend (``toga-winforms``) requires ``pythonnet``, which ships
only x86/x64 ``Python.Runtime.dll``. On Windows on ARM the interpreter is
ARM64, so the native backend can never initialise:

    RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize ...

``toga-webview2`` does not exist on PyPI and ``pywebview`` depends on pythonnet
too, so there is no Toga-based escape. Tkinter is stdlib, is bundled with this
Python, and works on ARM64 - and leaving the .NET stack out also makes the
bundle smaller and faster to start.

    pyinstaller --noconfirm MiRecoveryHelper-tk.spec
    # -> dist/rec检查喵.exe

Shared data/hidden-import/exclude lists live in tools/spec_common.py so this
file cannot drift away from the other specs.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT / "tools"))
import spec_common  # noqa: E402

a = Analysis(  # noqa: F821 - injected by PyInstaller
    [str(ROOT / "src" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=spec_common.ocr_binaries(),
    datas=spec_common.data_files(ROOT),
    hiddenimports=spec_common.hidden_imports(with_toga=False),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=spec_common.excludes(with_toga=False),
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="rec检查喵",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=spec_common.icon_file(ROOT),
    version=spec_common.version_file(ROOT),
)
