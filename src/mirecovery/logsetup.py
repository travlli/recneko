"""Logging setup and crash capture.

Why this exists
---------------
The first version of this app wrote no logs at all. When it failed on a user's
machine the only diagnostic was a traceback they had to copy by hand, and the
GUI build ships with ``console=False`` so stderr goes nowhere. Anything that
goes wrong in the field was effectively invisible.

Logs go to a per-user directory so they survive the app being a single file:

    Windows : %LOCALAPPDATA%/rec检查喵/logs/app.log
    Linux   : ~/.local/state/rec检查喵/logs/app.log
    macOS   : ~/Library/Logs/rec检查喵/app.log

The file is rotated (3 x 1 MB) so it cannot grow without bound.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path

APP_DIR_NAME = "rec检查喵"
LOGGER_NAME = "mirecovery"

_configured = False


def log_directory() -> Path:
    """Preferred per-user log directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Logs"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        root = Path(base) if base else Path.home() / ".local" / "state"
    return root / APP_DIR_NAME / "logs"


def _candidate_directories() -> list[Path]:
    """Where we are willing to put the log file, best first.

    A single hard-coded location means the app silently logs nothing whenever
    that path is unwritable - a locked-down profile, a read-only share, a
    sandbox. Falling back keeps diagnostics available.
    """
    candidates = [log_directory()]

    for var in ("TEMP", "TMP"):
        value = os.environ.get(var)
        if value:
            candidates.append(Path(value) / APP_DIR_NAME / "logs")

    # Beside the executable / project, as a last resort.
    try:
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "logs")
        else:
            candidates.append(Path.cwd() / "logs")
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a logger; safe to call before setup_logging()."""
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO) -> Path | None:
    """Configure file logging. Returns the log path, or None if unavailable.

    Never raises: a read-only or missing directory must not stop the app from
    starting. If logging cannot be set up, that is recorded and the app runs
    without it.
    """
    global _configured
    logger = get_logger()
    if _configured:
        return getattr(logger, "_mirecovery_log_path", None)

    logger.setLevel(level)
    logger.propagate = False
    _configured = True

    path: Path | None = None
    handler = None
    tried: list[str] = []
    for directory in _candidate_directories():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            candidate = directory / "app.log"
            handler = logging.handlers.RotatingFileHandler(
                candidate, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
            path = candidate
            break
        except Exception as exc:
            tried.append(f"{directory} ({type(exc).__name__})")
            handler = None
            continue

    if handler is not None:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    # A console handler helps when run from source; harmless when frozen
    # (stderr is discarded for windowed builds).
    try:
        if sys.stderr is not None:
            console = logging.StreamHandler(sys.stderr)
            console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(console)
    except Exception:
        pass

    logger._mirecovery_log_path = path  # type: ignore[attr-defined]

    if path is None:
        logger.warning(
            "无法创建日志文件，本次运行不记录日志。已尝试：%s", "; ".join(tried)
        )
    else:
        logger.info("=== 启动 %s ===", " ".join(sys.argv[1:]) or "(无参数)")
        logger.info("frozen=%s python=%s", getattr(sys, "frozen", False), sys.version.split()[0])
        logger.info("日志文件: %s", path)
    return path


def current_log_path() -> Path | None:
    return getattr(get_logger(), "_mirecovery_log_path", None)


def flush_handlers() -> None:
    """Force buffered log records to disk.

    Needed before a process dies: without it the crash record can be lost, which
    defeats the point of capturing it.
    """
    for handler in get_logger().handlers:
        try:
            handler.flush()
        except Exception:
            pass


def install_excepthook() -> None:
    """Log uncaught exceptions instead of losing them."""
    logger = get_logger()
    previous = sys.excepthook

    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc_value, exc_tb)
            return
        logger.critical(
            "未捕获异常:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        flush_handlers()
        previous(exc_type, exc_value, exc_tb)

    sys.excepthook = hook
