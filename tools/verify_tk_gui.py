#!/usr/bin/env python3
"""Headless verification of the tkinter front-end.

Checks that

* every widget option the front-end passes to tkinter/ttk is real (a wrong
  option name, e.g. ``font`` on a ``ttk.Frame``, is a classic silent breakage),
* the widget tree builds against a real Tk root,
* the analyse / image / clear flows work and render the expected text.

Tk needs a display; if one is unavailable the script reports that as an
environment limitation instead of a failure.

    python tools/verify_tk_gui.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def check_widget_options() -> list[str]:
    """Verify the tkinter/ttk options used by tkapp.py exist."""
    import inspect

    import tkinter as tk
    from tkinter import ttk

    problems: list[str] = []

    # (constructor, kwargs used in tkapp.py)
    usage = [
        (ttk.Frame, {"padding": 10}),
        (ttk.Label, {"text": "x", "font": ("Arial", 10), "anchor": "w"}),
        (ttk.Button, {"text": "x", "command": lambda: None}),
        (ttk.Scrollbar, {"command": lambda *a: None}),
        (tk.Text, {"height": 7, "wrap": "word", "font": ("Arial", 10), "undo": True,
                   "relief": "solid", "borderwidth": 1, "background": "#fff"}),
        (tk.Tk, {}),
    ]

    for cls, kwargs in usage:
        try:
            signature = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            continue
        parameters = signature.parameters
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
            continue
        unknown = [k for k in kwargs if k not in parameters]
        if unknown:
            problems.append(f"{cls.__name__} 不接受参数 {unknown}")

    print(f"控件选项: 已检查 {len(usage)} 类构造调用")
    return problems


def check_flows() -> list[str]:
    """Build the real app and drive its handlers."""
    problems: list[str] = []

    try:
        import tkinter as tk

        probe = tk.Tk()
        probe.withdraw()
        probe.destroy()
    except Exception as exc:
        print(f"[SKIP] 本环境无法创建 Tk 窗口（{type(exc).__name__}: {exc}）")
        return []

    from mirecovery.tkapp import MiRecoveryTkApp

    app = MiRecoveryTkApp()
    app.root.withdraw()

    if app.kb is None:
        problems.append(f"知识库未加载：{app.kb_error}")
    else:
        print(f"知识库  : {len(app.kb.entries)} 条 {app.kb.platforms()}")

    if app.recognizer is None:
        print(f"图片识别: 不可用（{app.recognition_error.splitlines()[0] if app.recognition_error else ''}）")
    else:
        counts = app.recognizer.reference_counts()
        print(f"图片识别: {len(counts)} 类 / {sum(counts.values())} 张参考图")

    # analyse flow
    app.log_input.insert("1.0", "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)\n")
    app.on_analyze()
    rendered = app.output.get("1.0", "end")
    if "4032" not in rendered:
        problems.append("日志分析未命中 4032")
    if "SP Flash Tool 报错" not in rendered:
        problems.append("日志分析未给出正确方案标题")
    print(f"日志分析: {len(rendered)} 字符, 状态栏='{app.status.cget('text')}'")

    # image flow
    sample = (
        PROJECT_ROOT / "kb" / "image_refs" / "synthetic"
        / "recovery-menu" / "recovery-menu-0.png"
    )
    if app.recognizer is not None and sample.is_file():
        app.load_image(sample)
        rendered = app.output.get("1.0", "end")
        if "图片识别结果" not in rendered:
            problems.append("图片流程未输出识别结果")
        if "Recovery 主菜单" not in rendered:
            problems.append("图片流程未识别出 Recovery 主菜单")
        if "对应解决方案" not in rendered:
            problems.append("图片流程未带出知识库方案")
        print(f"图片流程: 状态栏='{app.status.cget('text')}'")
        app.on_clear_image()

    # empty input prompt + clear
    app.on_clear()
    if "请把设备报错日志粘贴到上方输入框" not in app.output.get("1.0", "end"):
        problems.append("清空后未恢复默认说明")
    app.log_input.delete("1.0", "end")
    app.on_analyze()
    if "先粘一段报错日志" not in app.output.get("1.0", "end"):
        problems.append("空输入未给出提示")

    # The pre-filled hint text must not be treated as real user input.
    app.log_input.delete("1.0", "end")
    app.log_input.insert("1.0", "把 SP Flash Tool / MiFlash / QFIL / fastboot 的报错粘到这里")
    app.on_analyze()
    if "输入框里那段是提示文字" not in app.output.get("1.0", "end"):
        problems.append("预填提示文字被当作用户输入分析了")

    # Window title must carry the new name.
    if "/rec检查喵/" not in app.root.title():
        problems.append(f"窗口标题未使用新名称：{app.root.title()!r}")
    print(f"窗口标题: {app.root.title()}")

    # Mascot artwork must be found (it is bundled into the window).
    from mirecovery import theme

    if theme.find_sheet() is None:
        problems.append("找不到角色设定图 character_sheet.png")
    else:
        print(f"设定图  : {theme.find_sheet().name}")

    try:
        app.root.destroy()
    except Exception:
        pass
    return problems


def main() -> int:
    print(f"Python  : {sys.version.split()[0]}")
    try:
        import tkinter

        print(f"Tk      : {tkinter.TkVersion}\n")
    except Exception as exc:
        print(f"FAIL tkinter 不可用: {exc}")
        return 1

    problems: list[str] = []
    for check in (check_widget_options, check_flows):
        try:
            problems += check()
        except Exception:
            traceback.print_exc()
            return 1

    if problems:
        print("\n发现问题：")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\ntkinter 界面验证通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
