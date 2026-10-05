"""Shared PyInstaller configuration for every spec in this project.

Why this exists
---------------
The project had three specs (onefile, onedir, self-test) that each repeated the
same data-file list, hidden imports and excludes. They drifted twice in practice
- the self-test spec was first missing ``image_refs.json`` and later still
excluded ``tkinter``, so it kept testing a bundle that no longer resembled what
ships. Specs are just Python, so the duplication is avoidable: import this
module instead.

Usage from a spec:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(SPECPATH).resolve() / "tools"))
    import spec_common

    ROOT = Path(SPECPATH).resolve()
    datas = spec_common.data_files(ROOT)
    hiddenimports = spec_common.hidden_imports(with_toga=True)
    excludes = spec_common.excludes(with_toga=True)
"""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

# Bundled resource files (character artwork + icons). Anything missing is
# skipped rather than failing the build, so a clean-licence build with no
# third-party art still works.
RESOURCE_ASSETS = ("character_sheet.jpg", "icon.png", "window_icon.png")


def include_art() -> bool:
    """Whether to bundle the third-party artwork.

    ``tools/build_exe.py --no-art`` sets ``RECNEKO_NO_ART`` so the build can be
    produced without the community-supplied character image - useful if the
    artifact has to ship under a clean licence.
    """
    return os.environ.get("RECNEKO_NO_ART", "") not in ("1", "true", "yes")


VERSION_RE = re.compile(r'__version__\s*=\s*"([^"]+)"')


def data_files(root: Path) -> list[tuple[str, str]]:
    """Data files to bundle: knowledge base, reference library, resources."""
    datas: list[tuple[str, str]] = []

    kb = root / "src" / "mirecovery" / "data" / "kb.json"
    if not kb.is_file():
        raise SystemExit(
            f"缺少知识库数据文件 {kb}\n请先运行：python tools/build_kb.py"
        )
    datas.append((str(kb), "mirecovery/data"))

    refs = root / "src" / "mirecovery" / "data" / "image_refs.json"
    if refs.is_file():
        datas.append((str(refs), "mirecovery/data"))

    if include_art():
        res = root / "src" / "mirecovery" / "resources"
        for asset in RESOURCE_ASSETS:
            candidate = res / asset
            if candidate.is_file():
                datas.append((str(candidate), "mirecovery/resources"))

    return datas


def hidden_imports(with_toga: bool) -> list[str]:
    """Modules PyInstaller cannot discover statically."""
    modules = [
        "mirecovery",
        "mirecovery.kb",
        "mirecovery.scanner",
        "mirecovery.report",
        "mirecovery.recognize",
        "mirecovery.imagefeatures",
        "mirecovery.ocr",
        "mirecovery.online",
        "mirecovery.theme",
        "mirecovery.logsetup",
    ]
    modules += ocr_hidden_imports()
    if with_toga:
        modules += [
            "mirecovery.app",
            "toga_winforms",
            "toga_winforms.libs",
        ]
    else:
        modules.append("mirecovery.tkapp")
    return modules


def include_ocr() -> bool:
    """Whether to bundle the optional OCR engines.

    ``tools/build_exe.py --no-ocr`` sets ``RECNEKO_NO_OCR``. The Windows OCR
    bindings (``winsdk``) add ~11 MB, which matters on a nearly-full disk; the
    built-in Pillow matcher and its templates are always bundled regardless, so
    the app never loses the feature entirely.
    """
    return os.environ.get("RECNEKO_NO_OCR", "") not in ("1", "true", "yes")


def ocr_hidden_imports() -> list[str]:
    """OCR backends that must be bundled when installed.

    ``mirecovery.ocr`` imports these lazily inside functions so the app starts
    without them, which also means PyInstaller cannot see them. Without this the
    frozen exe would silently lose OCR and fall back to the (much weaker) built-in
    matcher.
    """
    if not include_ocr():
        return []
    modules: list[str] = []
    optional = {
        "winsdk": [
            "winsdk",
            "winsdk.windows.media.ocr",
            "winsdk.windows.globalization",
            "winsdk.windows.graphics.imaging",
            "winsdk.windows.security.cryptography",
            "winsdk.windows.storage.streams",
        ],
        "pytesseract": ["pytesseract"],
        "rapidocr_onnxruntime": ["rapidocr_onnxruntime"],
    }
    for package, names in optional.items():
        try:
            if importlib.util.find_spec(package) is not None:
                modules += names
        except Exception:
            continue
    return modules


def ocr_binaries() -> list[tuple[str, str]]:
    """Native libraries belonging to optional OCR backends."""
    if not include_ocr():
        return []
    binaries: list[tuple[str, str]] = []
    try:
        from PyInstaller.utils.hooks import collect_dynamic_libs

        if importlib.util.find_spec("winsdk") is not None:
            binaries += collect_dynamic_libs("winsdk")
    except Exception:
        pass
    return binaries


def excludes(with_toga: bool) -> list[str]:
    """Modules to leave out.

    ``numpy`` is excluded on purpose. It is only an optional accelerator for
    ZNCC (``imagefeatures`` falls back to an equivalent pure-Python path), and
    dropping it saves ~15 MB. The two-stage prefilter in ``recognize`` brought
    the pure-Python cost from ~140 ms to ~42 ms per image, which is what makes
    that trade acceptable - do not re-add numpy without re-measuring
    ``tools/benchmark_recognition.py``.
    """
    common = ["test", "unittest", "numpy"]
    if with_toga:
        return common
    # tkinter-only build: drop the whole .NET/WinForms stack.
    return common + [
        "toga",
        "toga_winforms",
        "pythonnet",
        "clr_loader",
        "WebView2",
        "dotnet_webview2_winforms",
    ]


def icon_file(root: Path) -> str | None:
    icon = root / "src" / "mirecovery" / "resources" / "icon.ico"
    return str(icon) if icon.is_file() else None


def app_version(root: Path) -> str:
    """Read __version__ from the package (single source of truth)."""
    init = root / "src" / "mirecovery" / "__init__.py"
    try:
        match = VERSION_RE.search(init.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    except Exception:
        pass
    return "0.0.0"


def version_file(root: Path) -> str | None:
    """Write a PyInstaller VSVersionInfo file so the exe has version metadata.

    Without this the built exe has no version resource at all, so you cannot
    tell two builds apart from the file properties.
    """
    version = app_version(root)
    parts = [int(p) for p in re.findall(r"\d+", version)[:4]]
    while len(parts) < 4:
        parts.append(0)
    tuple_version = tuple(parts)

    target = root / "build" / "version_info.txt"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple_version},
    prodvers={tuple_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404B0',
        [StringStruct('CompanyName', 'DSH'),
         StringStruct('FileDescription', '/rec检查喵/ 刷机报错检查助手'),
         StringStruct('FileVersion', '{version}'),
         StringStruct('InternalName', 'recneko'),
         StringStruct('LegalCopyright', 'MIT (应用代码)'),
         StringStruct('OriginalFilename', 'recneko.exe'),
         StringStruct('ProductName', '/rec检查喵/'),
         StringStruct('ProductVersion', '{version}')])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
""",
            encoding="utf-8",
        )
        return str(target)
    except Exception:
        return None
