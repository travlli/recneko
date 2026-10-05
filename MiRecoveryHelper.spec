# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: Toga single-file exe (x64 Windows only).

This build keeps the Toga/WinForms backend, so it only works where pythonnet
has a matching runtime - i.e. x64 Windows. On Windows on ARM it will fail at
startup with "Failed to resolve Python.Runtime.Loader.Initialize"; use the
tkinter build there instead (see MiRecoveryHelper-tk.spec).

The launcher probes the backend at runtime and falls back to tkinter, so even
this build degrades gracefully rather than crashing - but there is no point
shipping it to an ARM64 machine.

    pyinstaller --noconfirm MiRecoveryHelper.spec
    # -> dist/rec检查喵-toga.exe
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT / "tools"))
import spec_common  # noqa: E402

a = Analysis(  # noqa: F821
    [str(ROOT / "src" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=spec_common.data_files(ROOT),
    hiddenimports=spec_common.hidden_imports(with_toga=True),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=spec_common.excludes(with_toga=True),
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="rec检查喵-toga",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=spec_common.icon_file(ROOT),
    version=spec_common.version_file(ROOT),
)
