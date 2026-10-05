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


def _make_console_unicode_safe() -> None:
    """Never let console encoding kill the app.

    The packaged build runs under a GBK (codepage 936) console on Chinese
    Windows, and the UI strings contain characters GBK cannot encode (✅/❌/●).
    Writing one of those to stdout - via a print, a log record, or an exception
    traceback - raised ``UnicodeEncodeError`` and took the process down. Measured:
    the frozen self test died on the settings page's "❌ 启用了联网查询…" message.

    Tk itself renders these fine; only the console is affected, so the fix is to
    make the console tolerant rather than to strip the characters.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


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
    log_path = ""
    try:
        from mirecovery.logsetup import current_log_path

        path = current_log_path()
        log_path = f"\n\n日志文件：{path}" if path else ""
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "/rec检查喵/ 启动失败", message[-1200:] + log_path
        )
        root.destroy()
    except Exception:
        pass


def _preferred_gui() -> str:
    """Decide which GUI to try first.

    Order: explicit environment override, then the value baked in at build time
    by tools/build_exe.py (``mirecovery._buildcfg``). The build-time value is
    what makes the tkinter-only build actually prefer tkinter - setting an
    environment variable inside a PyInstaller spec, as an earlier version did,
    has no effect on the built executable at all.
    """
    choice = os.environ.get("MIRECOVERY_GUI", "").strip().lower()
    if choice in ("tk", "toga"):
        return choice
    try:
        from mirecovery._buildcfg import DEFAULT_GUI

        if DEFAULT_GUI in ("tk", "toga"):
            return DEFAULT_GUI
    except Exception:
        pass
    return "auto"


def main() -> int:
    # Before anything can print: a GBK console must not be able to kill the app.
    _make_console_unicode_safe()

    from mirecovery.logsetup import get_logger, install_excepthook, setup_logging

    log_path = setup_logging()
    install_excepthook()
    logger = get_logger("launcher")

    _install_data_hooks()

    choice = _preferred_gui()
    logger.info("GUI 选择: %s", choice)

    if choice == "tk":
        return _run_or_report(_run_tk, logger)

    if choice == "toga":
        return _run_or_report(_run_toga, logger)

    usable, reason = _toga_is_usable()
    if usable:
        try:
            _run_toga()
            return 0
        except Exception:
            logger.exception("Toga 启动失败，回退 tkinter")
            reason = "Toga 启动失败"

    logger.warning("Toga 后端不可用（%s），改用 tkinter 界面", reason)
    print(f"[launcher] Toga 后端不可用（{reason}），已改用 tkinter 界面。", file=sys.stderr)
    return _run_or_report(_run_tk, logger)


def _run_or_report(runner, logger) -> int:
    """Run a GUI entry point, reporting a startup failure usefully."""
    try:
        runner()
        return 0
    except Exception:
        detail = traceback.format_exc()
        logger.critical("界面启动失败:\n%s", detail)
        try:
            from mirecovery.logsetup import current_log_path, flush_handlers

            flush_handlers()
            path = current_log_path()
        except Exception:
            path = None
        hint = f"\n\n完整日志：{path}" if path else ""
        _show_startup_error(detail[-1200:] + hint)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
