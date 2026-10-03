"""Frozen-build entry point for the Windows executable.

Two jobs.

1. **Data path fix-up.** In a frozen app the package data does not sit next to
   the module, so the knowledge base and image reference library locations are
   injected before anything tries to load them.

2. **GUI backend selection.** Toga's Windows backend needs ``pythonnet``, whose
   only shipped runtimes are x86/x64. On Windows on ARM the interpreter is
   ARM64, so loading ``Python.Runtime.dll`` always fails:

       RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize ...

   That is an architecture mismatch, not a packaging bug, and it cannot be
   packaged around (``toga-webview2`` does not exist on PyPI and ``pywebview``
   depends on pythonnet as well). So the launcher probes Toga and silently
   falls back to the tkinter front-end (``mirecovery.tkapp``), which is
   stdlib-only and works on ARM64.

   Force a choice with ``MIRECOVERY_GUI=toga`` or ``MIRECOVERY_GUI=tk``.

PyInstaller runs this file as ``__main__`` with no parent package, so it must
use absolute imports only - ``from .app import run`` would fail with
"attempted relative import with no known parent package".
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

REASON = ""


def _data_search_dirs() -> list[Path]:
    """Where bundled package data may live, in priority order."""
    directories: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        directories.append(base / "mirecovery" / "data")
        directories.append(base / "data")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        directories.append(exe_dir / "mirecovery" / "data")
        directories.append(exe_dir / "data")
        directories.append(exe_dir / "_internal" / "mirecovery" / "data")
    return directories


def _install_data_hooks() -> None:
    """Point the KB and recogniser loaders at frozen-friendly locations."""
    global REASON

    directories = _data_search_dirs()

    kb_path = next((d / "kb.json" for d in directories if (d / "kb.json").is_file()), None)
    if kb_path is not None:
        os.environ.setdefault("MIRECOVERY_KB", str(kb_path))

    refs = [d / "image_refs.json" for d in directories]
    refs = [path for path in refs if path.is_file()]
    if not refs:
        return

    try:
        import mirecovery.recognize as recognize_module
    except Exception:
        return

    original = recognize_module.load_default_recognizer

    def patched(extra_paths=None):
        merged = list(refs)
        for extra in extra_paths or []:
            merged.append(extra)
        return original(merged)

    recognize_module.load_default_recognizer = patched


def _toga_is_usable() -> tuple[bool, str]:
    """Probe whether Toga's native backend can actually initialise."""
    try:
        from toga.platform import get_platform_factory

        get_platform_factory()
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _run_tk() -> None:
    from mirecovery.tkapp import run as run_tk

    run_tk()


def _run_toga() -> None:
    from mirecovery.app import run as run_toga

    run_toga()


def _show_startup_error(message: str) -> None:
    """Last-resort report when even tkinter fails to start."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("/rec检查喵/ 启动失败", message)
        root.destroy()
    except Exception:
        pass


def main() -> int:
    _install_data_hooks()

    choice = os.environ.get("MIRECOVERY_GUI", "").strip().lower()
    if choice == "tk":
        _run_tk()
        return 0
    if choice == "toga":
        _run_toga()
        return 0

    usable, reason = _toga_is_usable()
    if usable:
        try:
            _run_toga()
            return 0
        except Exception:
            traceback.print_exc()
            reason = "Toga 启动失败"

    print(
        f"[launcher] Toga 后端不可用（{reason}），已改用 tkinter 界面。",
        file=sys.stderr,
    )
    try:
        _run_tk()
    except Exception:
        detail = traceback.format_exc()
        traceback.print_exc()
        _show_startup_error(detail[-1500:])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
