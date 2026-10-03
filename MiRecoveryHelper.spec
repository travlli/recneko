# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build a single-file Windows .exe.

Usage (from the project root, inside a venv with pyinstaller + toga-winforms):

    pyinstaller --noconfirm MiRecoveryHelper.spec

Output: dist/MiRecoveryHelper.exe

The knowledge base (src/mirecovery/data/kb.json) is bundled as data; the app
resolves it at runtime via sys._MEIPASS (see src/mirecovery/kb.py).
"""

from pathlib import Path

# PyInstaller executes this spec with its own globals; `SPECPATH` is provided.
PROJECT_ROOT = Path(SPECPATH).resolve()
DATA_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "kb.json"
REFS_FILE = PROJECT_ROOT / "src" / "mirecovery" / "data" / "image_refs.json"
ICON_FILE = PROJECT_ROOT / "src" / "mirecovery" / "resources" / "icon.ico"

if not DATA_FILE.is_file():
    raise SystemExit(
        f"缺少知识库数据文件 {DATA_FILE}，请先运行：python tools/build_kb.py"
    )

datas = [(str(DATA_FILE), "mirecovery/data")]
# The screen-recognition reference library is optional: without it the image
# feature reports itself as unavailable while text search keeps working.
if REFS_FILE.is_file():
    datas.append((str(REFS_FILE), "mirecovery/data"))

a = Analysis(  # noqa: F821 - injected by PyInstaller
    # NOTE: must be src/launcher.py, not src/mirecovery/__main__.py.
    # PyInstaller runs its entry script as __main__ with no parent package, so
    # the package's own __main__.py (which uses relative imports) fails with
    # "attempted relative import with no known parent package".
    [str(PROJECT_ROOT / "src" / "launcher.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "mirecovery",
        "mirecovery.app",
        "mirecovery.kb",
        "mirecovery.scanner",
        "mirecovery.report",
        "mirecovery.recognize",
        "mirecovery.imagefeatures",
        # Toga backends are discovered dynamically.
        "toga_winforms",
        "toga_winforms.libs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "test",
        "unittest",
        # numpy is an optional accelerator only: imagefeatures.zncc() falls back
        # to an equivalent pure-Python path. Excluding it keeps the bundle much
        # smaller, which matters because onefile unpacks into %TEMP% on every
        # launch (a full disk there causes
        # "Could not create temporary directory!").
        "numpy",
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
    console=False,          # GUI app: no console window
    disable_windowed_traceback=False,
    icon=str(ICON_FILE) if ICON_FILE.is_file() else None,
)
