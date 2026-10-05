# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: console build of the frozen self test.

Verifies that the bundled knowledge base, reference library and GUI stack all
resolve correctly inside a frozen executable - the failures that only appear
after packaging.

It deliberately mirrors the tkinter build's data files, hidden imports and
excludes (via tools/spec_common.py) so it tests what actually ships. Earlier
versions duplicated that configuration by hand and drifted twice: the self test
was first missing image_refs.json, then still excluded tkinter.

    pyinstaller --noconfirm MiRecoveryHelper.selftest.spec
    dist/rec检查喵-selftest.exe

``console=True`` on purpose so the result can be read from stdout.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(ROOT / "tools"))
import spec_common  # noqa: E402

a = Analysis(  # noqa: F821
    [str(ROOT / "tools" / "frozen_selftest.py")],
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

# Deliberately **onedir**, not onefile.
#
# A onefile self test has to unpack the whole bundle into %TEMP% before it can
# run, which made it fail on a nearly-full disk with
# "Failed to extract winsdk\_winrt.pyd: decompression resulted in return code -1".
# The self test exists to check packaging, not to stress the temp directory, so
# it uses the layout that needs no extraction.
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="rec检查喵-selftest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="rec检查喵-selftest",
)
