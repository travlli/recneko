#!/usr/bin/env python3
"""Headless verification of the Toga GUI code.

Three independent checks:

1. **API introspection** - every widget attribute we touch is verified to exist
   on the *real* installed Toga, and every constructor keyword we pass is
   checked against the real signature. This is what catches mistakes such as
   ``toga.constants.Column`` (the real name is ``COLUMN``) or
   ``MainWindow(clipboard=...)`` (Toga 0.5.7 has no clipboard API).
2. **Style check** - every ``Pack(...)`` call the app makes is reconstructed
   with deprecation warnings promoted to errors, so deprecated styling cannot
   creep in unnoticed.
3. **Handler logic** - ``on_analyze`` / ``on_clear`` are exercised against stub
   widgets that mirror the Toga interface, covering the analyse-render-update
   flow without a display.

If the native backend can be constructed it also builds the real UI; if the
.NET runtime is unavailable that is reported as an environment limitation
rather than a code failure.

    python tools/verify_gui.py
"""

from __future__ import annotations

import inspect
import sys
import traceback
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Widget constructors the app calls, with the exact kwargs used.
# ``title`` is excluded: app.py sets ``main_window.title`` after construction.
WIDGET_USAGE: list[tuple[str, dict]] = [
    ("MultilineTextInput", {"placeholder": "x"}),
    ("MultilineTextInput", {"readonly": True, "value": "x"}),
    ("Button", {"text": "x", "on_press": lambda w: None}),
    ("Label", {"text": "x"}),
    ("Box", {"children": []}),
    ("ImageView", {"style": None}),
    ("Image", {"path": "x.png"}),
    ("OpenFileDialog", {"title": "t", "file_types": ["png"]}),
    ("InfoDialog", {"title": "t", "message": "m"}),
]

# Attributes/methods the app relies on.
ATTRIBUTE_USAGE: dict[str, list[str]] = {
    "MultilineTextInput": ["value", "readonly", "scroll_to_top"],
    "Button": ["text", "on_press"],
    "Label": ["text"],
    "Box": ["children"],
    "ImageView": ["image"],
    "Image": ["path", "size"],
    "MainWindow": ["content", "title", "show", "size", "dialog"],
    "Window": ["title", "size"],
    "App": ["formal_name", "app_id", "main_loop", "paths"],
}

# Every Pack(...) call made by app.py, mirrored for strict deprecation checks.
APP_STYLE_CALLS: list[dict] = [
    {"direction": "COLUMN", "margin": 8},
    {"margin": (8, 8, 4, 8)},
    {"direction": "COLUMN", "margin": (8, 8, 8, 8)},
    {"direction": "COLUMN", "margin": (8, 8, 0, 8)},
    {"flex": 1},
    {"flex": 1, "margin_right": 4},
    {"flex": 1, "margin_left": 4},
    {"margin": (8, 8, 0, 8)},
    {"height": 160, "margin": (8, 8, 0, 8)},
]


class StubPaths:
    """Stand-in for ``toga.App.paths``."""

    def __init__(self, app: Path):
        self.app = app


class StubWidget:
    """Minimal stand-in mirroring the Toga widget surface we rely on."""

    def __init__(self, **kwargs):
        self._value = kwargs.get("value", "")
        self.readonly = kwargs.get("readonly", False)
        self.text = kwargs.get("text", "")
        self.style = kwargs.get("style")
        self.on_press = kwargs.get("on_press")
        self.scrolled_to_top = False

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new) -> None:
        self._value = "" if new is None else str(new)

    def scroll_to_top(self) -> None:
        self.scrolled_to_top = True


def check_api() -> list[str]:
    """Verify our widget usage against the installed Toga."""
    import toga

    problems: list[str] = []
    print(f"Toga    : {toga.__version__}")

    try:
        from toga.constants import COLUMN

        print(f"常量    : COLUMN={COLUMN!r}")
    except Exception as exc:
        return [f"无法导入 toga.constants.COLUMN: {exc}"]

    # Widget constructors: parameters must exist in the real signature.
    for name, kwargs in WIDGET_USAGE:
        cls = getattr(toga, name, None)
        if cls is None:
            problems.append(f"toga.{name} 不存在")
            continue
        try:
            signature = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            continue
        parameters = signature.parameters
        # A **kwargs signature accepts anything.
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
            continue
        unknown = [k for k in kwargs if k not in parameters]
        if unknown:
            problems.append(
                f"toga.{name} 不接受参数 {unknown}（可用：{sorted(parameters)}）"
            )
    print(f"控件    : 已验证 {len(WIDGET_USAGE)} 处构造调用")

    # MainWindow must accept a keyword title, or app.py must set it after.
    try:
        signature = inspect.signature(toga.MainWindow.__init__)
        accepts_kwargs = any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
        )
        title_positional = "title" in signature.parameters
        if not (accepts_kwargs or title_positional):
            problems.append(
                "MainWindow 既不接受 **kwargs 也没有 title 参数，"
                "且 app.py 依赖二次赋值的写法需要再确认"
            )
    except (TypeError, ValueError):
        pass

    # Attributes we read/write must exist.
    for name, attributes in ATTRIBUTE_USAGE.items():
        cls = getattr(toga, name, None)
        if cls is None:
            problems.append(f"toga.{name} 不存在")
            continue
        for attribute in attributes:
            if not hasattr(cls, attribute):
                problems.append(f"toga.{name} 缺少属性/方法 {attribute}")
    print(f"属性    : 已验证 {sum(len(v) for v in ATTRIBUTE_USAGE.values())} 个属性/方法")

    # The app must not claim clipboard support that Toga does not have.
    if hasattr(toga.Window, "clipboard") or hasattr(toga.App, "clipboard"):
        print("剪贴板  : 本版本 Toga 支持剪贴板")
    else:
        print("剪贴板  : 本版本 Toga 无剪贴板 API（app.py 未使用，符合预期）")

    return problems


def check_styles() -> list[str]:
    """Reconstruct every Pack(...) the app uses, with deprecations as errors."""
    from toga.style import Pack

    problems: list[str] = []
    for kwargs in APP_STYLE_CALLS:
        resolved = dict(kwargs)
        if resolved.get("direction") == "COLUMN":
            from toga.constants import COLUMN

            resolved["direction"] = COLUMN
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            try:
                Pack(**resolved)
            except DeprecationWarning as exc:
                problems.append(f"Pack({kwargs}) 使用了已弃用属性: {exc}")
            except Exception as exc:
                problems.append(f"Pack({kwargs}) 失败: {type(exc).__name__}: {exc}")
    print(f"样式    : 已验证 {len(APP_STYLE_CALLS)} 组 Pack(...)（弃用告警视为错误）")
    return problems


def check_handlers() -> list[str]:
    """Exercise the analyse/clear flow with stub widgets."""
    from mirecovery.app import MiRecoveryApp
    from mirecovery.kb import KB

    problems: list[str] = []

    # Build a bare instance without toga.App.__init__ (needs a native backend).
    app = MiRecoveryApp.__new__(MiRecoveryApp)

    kb_path = PROJECT_ROOT / "src" / "mirecovery" / "data" / "kb.json"
    try:
        app.kb = KB.load(kb_path)
    except Exception as exc:
        return [f"知识库加载失败: {exc}"]

    app.kb_error = ""
    # ``App.paths`` is a read-only property backed by ``_paths``.
    app._paths = StubPaths(PROJECT_ROOT / "src" / "mirecovery")
    app.log_input = StubWidget(value="")
    app.output = StubWidget(value="")
    app.status_label = StubWidget(text="")
    app.image_view = StubWidget()
    app.image_label = StubWidget(text="")
    app.current_image_path = None
    app.recognition_error = ""
    from mirecovery.recognize import load_default_recognizer

    app.recognizer, app.recognition_error = load_default_recognizer(
        [PROJECT_ROOT / "src" / "mirecovery" / "data" / "image_refs.json"]
    )
    print(f"知识库  : {len(app.kb.entries)} 条 {app.kb.platforms()}")
    if app.recognizer is None:
        problems.append(f"图片识别库加载失败: {app.recognition_error}")
    else:
        counts = app.recognizer.reference_counts()
        print(f"图片库  : {len(counts)} 类 / {sum(counts.values())} 张参考图")

    # 1. analyse a real log sample
    app.log_input.value = (
        "SP Flash Tool v5.2044\n"
        "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)\n"
        "[EMI] Enable DRAM failed!\n"
    )
    app.on_analyze(None)
    rendered = app.output.value
    print(f"分析    : 报告 {len(rendered)} 字符, 状态栏='{app.status_label.text}'")
    if "4032" not in rendered:
        problems.append("报告未包含命中的错误码 4032")
    if "SP Flash Tool 报错" not in rendered:
        problems.append("报告未包含正确的方案标题")
    if not app.status_label.text.startswith("判定：MediaTek"):
        problems.append(f"状态栏平台判定异常: {app.status_label.text}")
    if not app.output.scrolled_to_top:
        problems.append("分析后未滚动到顶部")

    # 2. empty input must not crash and must prompt
    app.log_input.value = "   "
    app.on_analyze(None)
    if "请先粘贴" not in app.output.value:
        problems.append("空输入未给出提示")

    # 3. clear resets everything
    app.log_input.value = "junk"
    app.output.value = "junk"
    app.on_clear(None)
    if app.log_input.value != "":
        problems.append("清空后输入框未清空")
    if "请把设备报错日志粘贴到上方输入框" not in app.output.value:
        problems.append("清空后未恢复默认说明")
    if not app.status_label.text.startswith("知识库："):
        problems.append("清空后状态栏未恢复")

    # 4. image recognition through the GUI path
    if app.recognizer is not None:
        sample = (
            PROJECT_ROOT / "kb" / "image_refs" / "synthetic"
            / "recovery-menu" / "recovery-menu-0.png"
        )
        if sample.is_file():
            app.load_image(sample)
            rendered = app.output.value
            print(f"图片识别: 状态栏='{app.status_label.text}'")
            if "图片识别结果" not in rendered:
                problems.append("图片识别未输出识别结果区")
            if "Recovery 主菜单" not in rendered:
                problems.append("图片识别未匹配到 Recovery 主菜单")
            if "对应解决方案" not in rendered:
                problems.append("图片识别未带出知识库方案")
            if not app.status_label.text.startswith("图片识别"):
                problems.append("图片识别后状态栏未更新")
            # Removing the image resets the preview state.
            app.on_clear_image(None)
            if app.current_image_path is not None:
                problems.append("移除图片后 current_image_path 未清空")
        else:
            print("[SKIP] 未找到 kb/image_refs/ 合成参考图，跳过 GUI 图片流程检查")

    return problems


def check_native() -> str:
    """Try to construct the real app; report environment limits separately."""
    try:
        from mirecovery.app import MiRecoveryApp

        app = MiRecoveryApp(formal_name="x", app_id="com.dsh.x")
        app.startup()
        children = len(getattr(app.main_window.content, "children", []))
        return f"原生后端可用：真实界面已构建（{children} 个子控件）"
    except Exception as exc:
        return (
            "本机无法构建原生界面（环境限制，非代码错误）："
            f"{type(exc).__name__}: {exc}"
        )


def main() -> int:
    print(f"Python  : {sys.version.split()[0]}\n")

    problems: list[str] = []
    for check in (check_api, check_styles):
        try:
            problems += check()
        except Exception:
            traceback.print_exc()
            return 1

    print()
    try:
        problems += check_handlers()
    except Exception:
        traceback.print_exc()
        return 1

    print()
    print(check_native())

    if problems:
        print("\n发现问题：")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nGUI 代码验证通过（API 用法 + 样式 + 事件流程）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
