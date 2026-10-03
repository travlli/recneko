# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: console build of the frozen self test.

Verifies that the bundled knowledge base resolves correctly inside a frozen
executable (this is the failure mode that only shows up after packaging).

    pyinstaller --noconfirm MiRecoveryHelper.selftest.spec
    dist\\MiRecoveryHelperSelfTest.exe

`console=True` on purpose so the result can be read from stdout.
"""

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve()
DATA_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "kb.json"
REFS_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "image_refs.json"

if not DATA_FILE.is_file():
    raise SystemExit(
        f"缺少知识库数据文件 {DATA_FILE}，请先运行：python tools/build_kb.py"
    )

# Mirror the real app's data layout so this genuinely tests what ships.
datas = [(str(DATA_FILE), "mirecovery/data")]
if REFS_FILE.is_file():
    datas.append((str(REFS_FILE), "mirecovery/data"))

a = Analysis(  # noqa: F821
    [str(PROJECT_ROOT / "tools" / "frozen_selftest.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # The tkinter front-end is the primary GUI; importing it here proves the
        # frozen bundle can build the interface that actually ships.
        "mirecovery.tkapp",
        "mirecovery.recognize",
        "mirecovery.imagefeatures",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["test", "unittest", "numpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MiRecoveryHelperSelfTest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
