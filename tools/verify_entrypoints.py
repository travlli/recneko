#!/usr/bin/env python3
"""Check that the packaged entry points can actually be executed.

Why this exists: PyInstaller runs its entry script as ``__main__`` with **no
parent package**. Pointing the spec at a package module that uses relative
imports (for example ``src/mirecovery/__main__.py``, which does
``from .app import run``) builds fine and then dies at startup with:

    ImportError: attempted relative import with no known parent package

That failure is invisible to import tests and to the frozen self test, because
both import modules as members of the package rather than as ``__main__``.
This script reproduces PyInstaller's real execution mode with runpy.

    python tools/verify_entrypoints.py
"""

from __future__ import annotations

import runpy
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

# Entry points that PyInstaller must be able to execute as a top-level script.
ENTRY_POINT = SRC / "launcher.py"

# The module the app is built from.
APP_MODULE = "mirecovery.app"


def check_modules_import() -> list[str]:
    """Every module the app is built from must import cleanly."""
    import importlib

    modules = (
        "mirecovery",
        "mirecovery.app",
        "mirecovery.tkapp",
        "mirecovery.kb",
        "mirecovery.scanner",
        "mirecovery.report",
        "mirecovery.recognize",
        "mirecovery.imagefeatures",
    )
    problems: list[str] = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:
            problems.append(f"import {name} 失败: {type(exc).__name__}: {exc}")
    print(f"包导入  : 已检查 {len(modules)} 个模块")
    return problems


def check_entry_point() -> list[str]:
    """Run the frozen entry point the way PyInstaller does.

    A GUI app calls ``mainloop()`` and blocks, so instead of running the file we
    exec it with ``run_name='__main__'`` while stubbing both GUI entry points
    (Toga and tkinter). That reproduces PyInstaller's module context - the
    actual cause of the reported startup failure - without opening a window.
    """
    problems: list[str] = []

    if not ENTRY_POINT.is_file():
        return [f"入口脚本不存在: {ENTRY_POINT}"]

    source = ENTRY_POINT.read_text(encoding="utf-8")

    # 1. The launcher must not use relative imports - it has no parent package.
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("from .") or stripped.startswith("import ."):
            problems.append(
                f"launcher.py:{line_number} 使用了相对导入，"
                f"作为 __main__ 执行时会失败: {stripped}"
            )

    # 2. Exec it in __main__ context with both GUIs stubbed out.
    import mirecovery.app as toga_module
    import mirecovery.tkapp as tk_module

    reached = {"toga": False, "tk": False}
    original_toga = toga_module.run
    original_tk = tk_module.run

    toga_module.run = lambda *a, **k: reached.__setitem__("toga", True)
    tk_module.run = lambda *a, **k: reached.__setitem__("tk", True)
    try:
        runpy.run_path(str(ENTRY_POINT), run_name="__main__")
    except ImportError as exc:
        problems.append(f"以 __main__ 执行入口脚本失败（这正是打包后的启动错误）: {exc}")
    except Exception:
        problems.append("以 __main__ 执行入口脚本异常:\n" + traceback.format_exc())
    finally:
        toga_module.run = original_toga
        tk_module.run = original_tk

    if not problems and not (reached["toga"] or reached["tk"]):
        problems.append("入口脚本没有调用任何 GUI 的 run()，打包后不会启动界面")

    print(
        f"入口脚本: launcher.py 可被 __main__ 方式执行 "
        f"(toga={reached['toga']}, tk={reached['tk']})"
    )

    # 3. Guard against the primary spec regressing.
    spec = PROJECT_ROOT / "MiRecoveryHelper-tk.spec"
    if spec.is_file():
        spec_text = spec.read_text(encoding="utf-8")
        if 'src" / "mirecovery" / "__main__.py"' in spec_text:
            problems.append(
                f"{spec.name} 仍把 src/mirecovery/__main__.py 作为入口；"
                "请改为 src/launcher.py"
            )
        if "launcher.py" in spec_text:
            print(f"spec    : {spec.name} 入口指向 launcher.py（正确）")
        if "mirecovery.tkapp" not in spec_text:
            problems.append(f"{spec.name} 没有打包主界面 mirecovery.tkapp")
    else:
        problems.append("找不到 MiRecoveryHelper-tk.spec")

    return problems


def main() -> int:
    print(f"Python  : {sys.version.split()[0]}\n")

    problems: list[str] = []
    problems += check_modules_import()
    print()
    problems += check_entry_point()

    if problems:
        print("\n发现问题：")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\n入口点验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
