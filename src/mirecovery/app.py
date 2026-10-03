"""/rec检查喵/ —— Toga 界面（x64 桌面 / Android 用）.

用户在输入框粘贴设备报错日志，点击[检测并给出方案]，
应用判定平台（MTK / 高通 / fastboot / recovery / AVB），
再从本地知识库检索最匹配的解决方案并展示完整排查步骤。

也可以[选择图片]：用纯 Pillow 的画面识别判断截图属于哪种报错，再打开对应
知识库条目（见 mirecovery/recognize.py）。

注意：Windows on ARM 上 Toga 后端不可用（toga-winforms 依赖的 pythonnet 没有
ARM64 运行时），那种机器会自动回退到 mirecovery/tkapp.py 的 tkinter 界面。

知识库数据来自 ``data/kb.json``（由 tools/build_kb.py 从 dsh-kb wiki 生成），
参考图特征来自 ``data/image_refs.json``（由 tools/build_references.py 生成），
两者都打包进 exe / apk，运行时不需要网络。

Toga API 说明（0.5.7 实测）：
* ``toga.MainWindow(title=...)`` 无法通过关键字传 title（MainWindow 的
  ``__init__`` 是 ``*args, **kwargs`` 透传），因此构造后再赋值 ``.title``。
* Toga 0.5.7 **没有剪贴板 API**（toga 与 toga_winforms 中均无 clipboard），
  所以结果区只提供可选中文本 + 手动复制提示，不做「复制」按钮。
* ``Pack.padding*`` 在 0.5.7 已弃用，统一用 ``margin*``。
* ``toga.Image`` 用 ``path=`` 加载本地文件；``ImageView.image`` 可后赋值。
"""

from __future__ import annotations

from pathlib import Path

import toga
from toga.constants import COLUMN
from toga.style import Pack

from .kb import KB
from .recognize import load_default_recognizer
from .report import build_report, empty_report, recognition_report
from . import theme

APP_TITLE = theme.APP_DISPLAY_NAME

# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

_PAD = 8

_PAGE_STYLE = Pack(direction=COLUMN, margin=_PAD)
_LABEL_STYLE = Pack(margin=(_PAD, _PAD, 4, _PAD))
_BUTTON_ROW_STYLE = Pack(direction=COLUMN, margin=(_PAD, _PAD, _PAD, _PAD))
_IMAGE_ROW_STYLE = Pack(direction=COLUMN, margin=(_PAD, _PAD, 0, _PAD))
_INPUT_STYLE = Pack(flex=1)
_OUTPUT_STYLE = Pack(flex=1)
_STATUS_STYLE = Pack(margin=(_PAD, _PAD, 0, _PAD))
_PREVIEW_STYLE = Pack(height=160, margin=(_PAD, _PAD, 0, _PAD))

IMAGE_FILTERS = ["png", "jpg", "jpeg", "webp", "bmp"]


class MiRecoveryApp(toga.App):
    """Main application."""

    def startup(self) -> None:
        self.kb: KB | None = None
        self.kb_error: str = ""
        self.recognizer = None
        self.recognition_error: str = ""
        self.current_image_path: Path | None = None

        # ---- load the bundled knowledge base -----------------------------
        # BeeWare lays apps out differently on every platform (and Android is
        # not a filesystem we can guess at), so consult the app's own resource
        # directory as well as the package directory.
        try:
            self.kb = KB.load(extra_paths=self._kb_search_paths())
        except Exception as exc:  # pragma: no cover - depends on packaging
            self.kb_error = str(exc)

        # ---- load the screen-recognition reference library ---------------
        self.recognizer, self.recognition_error = load_default_recognizer(
            self._reference_search_paths()
        )

        # ---- widgets -----------------------------------------------------
        self.image_view = toga.ImageView(style=_PREVIEW_STYLE)

        self.pick_image_button = toga.Button(
            "选择图片识别画面",
            on_press=self.on_pick_image,
            style=Pack(flex=1, margin_right=4),
        )
        self.clear_image_button = toga.Button(
            "移除图片",
            on_press=self.on_clear_image,
            style=Pack(flex=1, margin_left=4),
        )

        self.image_label = toga.Label(
            self._image_status_text(), style=_LABEL_STYLE
        )

        self.log_input = toga.MultilineTextInput(
            placeholder=(
                "把设备报错日志粘贴到这里。\n\n"
                "例如：\n"
                "  BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)\n"
                "  ERROR: Sahara Fail / Failed to get sahara mode\n"
                "  Writing 'boot' FAILED (remote: 'not allowed in locked state')\n"
                "  E:failed to mount /data\n"
                "  dm-verity corruption"
            ),
            style=_INPUT_STYLE,
        )

        self.output = toga.MultilineTextInput(
            readonly=True,
            value=self._initial_output(),
            style=_OUTPUT_STYLE,
        )

        self.analyze_button = toga.Button(
            "检测并给出方案",
            on_press=self.on_analyze,
            style=Pack(flex=1, margin_right=4),
        )
        self.clear_button = toga.Button(
            "清空",
            on_press=self.on_clear,
            style=Pack(flex=1, margin_left=4),
        )

        self.status_label = toga.Label(self._status_text(), style=_STATUS_STYLE)

        hint_label = toga.Label(
            "提示：结果可以直接用鼠标/手指选中后复制；本应用完全离线，"
            "日志与图片都不会离开本机。",
            style=_LABEL_STYLE,
        )

        # ---- layout ------------------------------------------------------
        main_box = toga.Box(
            children=[
                toga.Label("[1] 选择报错截图（可选）", style=_LABEL_STYLE),
                toga.Box(
                    children=[self.pick_image_button, self.clear_image_button],
                    style=_IMAGE_ROW_STYLE,
                ),
                self.image_label,
                self.image_view,
                toga.Label(
                    "[2] 或粘贴设备日志"
                    "（SP Flash Tool / MiFlash / QFIL / fastboot / recovery 输出均可）",
                    style=_LABEL_STYLE,
                ),
                self.log_input,
                toga.Box(
                    children=[self.analyze_button, self.clear_button],
                    style=_BUTTON_ROW_STYLE,
                ),
                self.status_label,
                toga.Label("[3] 诊断结果与解决方案", style=_LABEL_STYLE),
                self.output,
                hint_label,
            ],
            style=_PAGE_STYLE,
        )

        self.main_window = toga.MainWindow()
        self.main_window.title = self.formal_name
        self.main_window.content = main_box
        self._fit_window()
        self.main_window.show()

    # -- helpers -----------------------------------------------------------

    def _kb_search_paths(self) -> list:
        """Candidate locations for kb.json, given how BeeWare packaged us."""
        candidates = []
        # toga.App.paths.app points at the packaged app resource directory.
        try:
            candidates.append(self.paths.app / "mirecovery" / "data" / "kb.json")
            candidates.append(self.paths.app / "data" / "kb.json")
            candidates.append(self.paths.app / "kb.json")
        except Exception:
            pass
        return candidates

    def _fit_window(self, width: int = 1000, height: int = 780) -> None:
        """Size the window, tolerating backends without pixel sizes."""
        try:
            from toga.constants import Size

            self.main_window.size = Size(width, height)
        except Exception:
            pass  # mobile backends are always full-screen

    def _reference_search_paths(self) -> list:
        """Candidate locations for the image reference library."""
        candidates = []
        try:
            candidates.append(self.paths.app / "mirecovery" / "data" / "image_refs.json")
            candidates.append(self.paths.app / "data" / "image_refs.json")
            candidates.append(self.paths.app / "image_refs.json")
        except Exception:
            pass
        return candidates

    def _image_status_text(self) -> str:
        if self.current_image_path is None:
            if self.recognizer is None:
                return f"图片识别不可用：{self.recognition_error}"
            counts = self.recognizer.reference_counts()
            total = sum(counts.values())
            real = sum(
                1 for r in self.recognizer.library.references if r.source == "user"
            )
            note = "（含真实照片）" if real else "（仅合成示意图，真机准确率未知）"
            return (
                f"图片识别：已就绪，{len(counts)} 类 / {total} 张参考图{note}"
            )
        return f"当前图片：{self.current_image_path.name}"

    def _initial_output(self) -> str:
        if self.kb is None:
            return (
                "[!] 知识库加载失败，无法提供方案。\n\n"
                f"{self.kb_error}\n\n"
                "如果你是从源码运行，请先执行：\n"
                "    python tools/build_kb.py"
            )
        return empty_report()

    def _status_text(self) -> str:
        if self.kb is None:
            return "知识库：加载失败"
        return f"知识库：已加载 {len(self.kb.entries)} 条（{', '.join(self.kb.platforms())}）"

    def _show_message(self, title: str, message: str) -> None:
        """Show an info dialog; silently ignore backends without dialogs."""
        try:
            self.main_window.dialog(toga.InfoDialog(title, message))
        except Exception:
            pass

    # -- event handlers ----------------------------------------------------

    def on_pick_image(self, widget: toga.Widget | None = None) -> None:
        """Pick an image file, show it, and try to recognise the screen."""
        if self.recognizer is None:
            self.output.value = (
                "图片识别不可用。\n\n"
                f"{self.recognition_error}\n\n"
                "仍然可以粘贴报错文字来检索方案。"
            )
            return

        try:
            selection = self.main_window.dialog(
                toga.OpenFileDialog(
                    "选择报错截图或照片",
                    file_types=IMAGE_FILTERS,
                )
            )
        except Exception as exc:
            self._show_message(
                "无法打开文件选择器",
                f"{type(exc).__name__}: {exc}\n\n"
                "可以直接把报错文字粘贴到日志框里检索。",
            )
            return

        if not selection:
            return  # user cancelled

        # Toga returns a single Path for a single selection.
        path = selection[0] if isinstance(selection, (list, tuple)) else selection
        self.load_image(Path(path))

    def load_image(self, path: Path) -> None:
        """Show an image and run recognition on it. Also used by tests."""
        self.current_image_path = Path(path)

        # Preview first: it should appear even if recognition fails.
        try:
            self.image_view.image = toga.Image(path=str(self.current_image_path))
        except Exception:
            self.image_view.image = None

        self.image_label.text = self._image_status_text()

        if self.recognizer is None:
            return

        result = self.recognizer.recognize_path(self.current_image_path)

        if self.kb is None:
            self.output.value = result.reason or "知识库不可用。"
            return

        entry, report_text = recognition_report(self.kb, result)
        self.output.value = report_text

        if result.matched:
            self.status_label.text = (
                f"图片识别：{result.title}（置信度 {result.confidence:.0%}）"
            )
        else:
            self.status_label.text = "图片识别：未能确定画面类型，请补充文字"

        try:
            self.output.scroll_to_top()
        except Exception:
            pass

    def on_clear_image(self, widget: toga.Widget | None = None) -> None:
        self.current_image_path = None
        try:
            self.image_view.image = None
        except Exception:
            pass
        self.image_label.text = self._image_status_text()

    def on_analyze(self, widget: toga.Widget | None = None) -> None:
        text = self.log_input.value or ""
        if not text.strip():
            self.output.value = "请先粘贴设备报错日志，再点击[检测并给出方案]。"
            return

        if self.kb is None:
            self.output.value = self._initial_output()
            return

        try:
            finding, matches, report_text = build_report(self.kb, text, limit=5)
        except Exception as exc:  # pragma: no cover - defensive
            self.output.value = f"检索时出错：{exc}"
            return

        self.output.value = report_text

        if matches:
            self.status_label.text = (
                f"判定：{finding.platform_label}（置信度 {finding.confidence:.0%}）"
                f"　命中 {len(matches)} 条方案"
            )
        else:
            self.status_label.text = f"判定：{finding.platform_label}　知识库中未找到匹配条目"

        # Put the user at the top of the freshly rendered report.
        try:
            self.output.scroll_to_top()
        except Exception:
            pass

    def on_clear(self, widget: toga.Widget | None = None) -> None:
        self.log_input.value = ""
        self.output.value = self._initial_output()
        self.status_label.text = self._status_text()
        self.on_clear_image()


def main() -> MiRecoveryApp:
    return MiRecoveryApp(
        formal_name=theme.APP_DISPLAY_NAME,
        app_id=theme.APP_ID,
    )


def run() -> None:
    """Entry point used by ``python -m mirecovery`` and by Briefcase."""
    main().main_loop()


if __name__ == "__main__":
    run()
