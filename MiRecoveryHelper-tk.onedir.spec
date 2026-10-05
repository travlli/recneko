# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: **tkinter-only** onedir build (no %TEMP% dependency).

Same rationale as MiRecoveryHelper-tk.spec, but collected into a folder instead
of a single file. Nothing is unpacked at startup, so it is immune to both
"Could not create temporary directory!" and a nearly-full system disk.

    pyinstaller --noconfirm MiRecoveryHelper-tk.onedir.spec
    # -> dist/rec检查喵/rec检查喵.exe
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT / "tools"))
import spec_common  # noqa: E402

APP_NAME = "rec检查喵"

a = Analysis(  # noqa: F821
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
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=spec_common.icon_file(ROOT),
    version=spec_common.version_file(ROOT),
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
