"""/rec检查喵/ —— tkinter 界面（二次元风）.

为什么用 tkinter 而不是 Toga
----------------------------
Toga 的 Windows 后端（``toga-winforms``）依赖 ``pythonnet``，而 pythonnet 官方
只提供 x86 / x64 运行时，没有 ARM64 版本。在 Windows on ARM 上解释器是 ARM64，
加载该 DLL 必然失败：

    RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize ...

这是位数/架构不匹配，属环境不兼容，任何打包方式都绕不过去；备选方案
（``toga-webview2`` 不存在、``pywebview`` 同样依赖 pythonnet）也都不通。
因此界面用 **tkinter**（Python 标准库自带，完全不碰 .NET）。

外观是「樱花粉 + DeepSeek 蓝」的二次元风：圆角卡片、粉蓝配色、内置吉祥物
「大肥鱼喵」。业务逻辑（知识库检索 / 日志分析 / 图片识别 / 报告渲染）与 Toga
版完全共用，一行未改。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import theme
from .kb import KB
from .recognize import load_default_recognizer
from .report import build_report, empty_report, recognition_report

IMAGE_FILETYPES = [
    ("图片", "*.png *.jpg *.jpeg *.webp *.bmp"),
    ("所有文件", "*.*"),
]


def pick_font(root: tk.Misc, candidates, size: int, weight: str = "normal") -> tuple:
    """Return the first installed font family from ``candidates``."""
    try:
        available = {name.lower() for name in tkfont.families(root)}
    except Exception:
        available = set()
    for name in candidates:
        if name.lower() in available:
            return (name, size, weight)
    return (tkfont.nametofont("TkDefaultFont").actual("family"), size, weight)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def load_photo(path, max_size, background: str):
    """Load an image for Tk, flattened onto ``background``.

    Tk's PhotoImage has no alpha compositing against the parent widget, so a
    transparent PNG would render with a white plate behind it. Flattening the
    image onto the window colour in Pillow avoids that entirely.
    """
    from PIL import Image, ImageTk

    with Image.open(path) as handle:
        handle.load()
        image = handle.convert("RGBA")

    image.thumbnail(max_size, Image.LANCZOS)
    plate = Image.new("RGBA", image.size, hex_to_rgb(background) + (255,))
    plate.alpha_composite(image)
    return ImageTk.PhotoImage(plate.convert("RGB"))


class Card(tk.Frame):
    """A white rounded-ish card with a soft border."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            background=theme.CARD,
            highlightbackground=theme.LINE,
            highlightthickness=1,
            bd=0,
            **kwargs,
        )


class MiRecoveryTkApp:
    """tkinter front-end. Shares all business logic with the Toga version."""

    def __init__(self) -> None:
        self.kb: KB | None = None
        self.kb_error = ""
        self.recognizer = None
        self.recognition_error = ""
        self.current_image: Path | None = None
        self._preview_image = None      # keep a reference or Tk drops the image
        self._sheet_image = None

        self.root = tk.Tk()
        self.root.title(theme.APP_DISPLAY_NAME)
        self.root.minsize(640, 460)
        self.root.configure(background=theme.BG)
        self._set_window_icon()
        self._fit_to_screen()

        self.ui_font = pick_font(self.root, theme.CJK_FONTS, 10)
        self.body_font = pick_font(self.root, theme.CJK_FONTS, 10)
        self.title_font = pick_font(self.root, theme.ROUND_FONTS, 17, "bold")
        self.heading_font = pick_font(self.root, theme.ROUND_FONTS, 11, "bold")
        self.quote_font = pick_font(self.root, theme.ROUND_FONTS, 10)
        self.mono_font = pick_font(self.root, theme.MONO_FONTS, 10)

        self._load_data()
        self._build_ui()

    # -- data --------------------------------------------------------------

    def _load_data(self) -> None:
        try:
            self.kb = KB.load()
        except Exception as exc:
            self.kb_error = str(exc)

        self.recognizer, self.recognition_error = load_default_recognizer()

    def _set_window_icon(self) -> None:
        """Set the title-bar icon from the small generated PNG.

        Tk's PhotoImage only reads PNG in recent versions and dislikes very
        large files, so the 64px window icon is preferred over the 512px one.
        """
        for candidate in (theme.WINDOW_ICON_PNG, theme.ICON_PNG):
            try:
                if candidate.is_file():
                    self._icon_image = tk.PhotoImage(file=str(candidate))
                    self.root.iconphoto(True, self._icon_image)
                    return
            except Exception:
                continue

    def _fit_to_screen(self, width: int = 1000, height: int = 760) -> None:
        """Choose a window size that actually fits this display.

        Hardcoding a large geometry means the window overflows a smaller screen
        (or the taskbar covers the bottom), which clips the right-hand side of
        the layout and makes it look broken.
        """
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
        except Exception:
            self.root.geometry(f"{width}x{height}")
            return

        # Leave room for window chrome and the taskbar.
        usable_w = max(640, screen_w - 80)
        usable_h = max(460, screen_h - 120)
        chosen_w = min(width, usable_w)
        chosen_h = min(height, usable_h)

        x = max(0, (screen_w - chosen_w) // 2)
        y = max(0, (screen_h - chosen_h) // 3)
        self.root.geometry(f"{chosen_w}x{chosen_h}+{x}+{y}")

    # -- ui ----------------------------------------------------------------

    def _style(self) -> ttk.Style:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")   # clam honours custom colours best
        except Exception:
            pass

        style.configure(".", font=self.ui_font, background=theme.BG,
                        foreground=theme.INK)
        style.configure("TFrame", background=theme.BG)
        style.configure("Card.TFrame", background=theme.CARD)

        # Primary action button: 深蓝底 + 白字（对齐鲸鱼娘设定图的深蓝主调）
        style.configure(
            "Navy.TButton",
            font=self.heading_font,
            background=theme.NAVY,
            foreground="#ffffff",
            borderwidth=0,
            focuscolor=theme.NAVY,
            padding=(16, 9),
        )
        style.map(
            "Navy.TButton",
            background=[("active", theme.NAVY_DEEP), ("pressed", theme.NAVY_DEEP)],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        )

        # Secondary button: pale blue.
        style.configure(
            "Blue.TButton",
            font=self.ui_font,
            background=theme.BLUE_PALE,
            foreground=theme.NAVY,
            borderwidth=0,
            focuscolor=theme.BLUE_PALE,
            padding=(12, 8),
        )
        style.map(
            "Blue.TButton",
            background=[("active", theme.BLUE_LIGHT), ("pressed", theme.BLUE_LIGHT)],
        )

        style.configure("Title.TLabel", font=self.title_font,
                        background=theme.BG, foreground=theme.NAVY_DEEP)
        style.configure("Heading.TLabel", font=self.heading_font,
                        background=theme.BG, foreground=theme.NAVY)
        style.configure("Quote.TLabel", font=self.quote_font,
                        background=theme.BG, foreground=theme.INK_SOFT)
        style.configure("Status.TLabel", font=self.ui_font,
                        background=theme.BG, foreground=theme.INK_SOFT)
        style.configure("CardText.TLabel", font=self.ui_font,
                        background=theme.CARD, foreground=theme.INK_SOFT)
        style.configure("Vertical.TScrollbar", background=theme.BLUE_PALE,
                        troughcolor=theme.BG, borderwidth=0)
        return style

    def _build_ui(self) -> None:
        self._style()

        outer = ttk.Frame(self.root, padding=(14, 12, 14, 12))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)   # log input grows
        outer.rowconfigure(7, weight=2)   # results grow more
        outer.rowconfigure(6, weight=0)

        # ---------------- header: character sheet + title + greeting ----------------
        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self._load_sheet(header)

        text_col = ttk.Frame(header)
        text_col.grid(row=0, column=1, sticky="w", padx=(12, 0))
        text_col.columnconfigure(0, weight=1)
        ttk.Label(text_col, text=theme.APP_DISPLAY_NAME, style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            text_col,
            text="小米 / 红米 刷机报错检查助手 · 内置知识库离线检索",
            style="Quote.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        self.greeting_label = ttk.Label(
            text_col, text=theme.greeting(), style="Quote.TLabel", wraplength=560
        )
        self.greeting_label.pack(anchor="w", pady=(4, 0))

        # ---------------- image section -----------------------------------
        image_card = Card(outer)
        image_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        image_card.columnconfigure(1, weight=1)

        ttk.Label(image_card, text=f"{theme.DECOR['image']} [1] 丢一张报错截图进来（可选）",
                  style="Heading.TLabel", background=theme.CARD).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 6)
        )

        buttons = ttk.Frame(image_card, style="Card.TFrame")
        buttons.grid(row=1, column=0, sticky="w", padx=12)
        ttk.Button(buttons, text="选择图片", style="Navy.TButton",
                   command=self.on_pick_image).pack(side="left")
        ttk.Button(buttons, text="移除", style="Blue.TButton",
                   command=self.on_clear_image).pack(side="left", padx=(8, 0))
        self.image_label = ttk.Label(
            image_card, text=self._image_status_text(), style="CardText.TLabel"
        )
        self.image_label.grid(row=1, column=1, sticky="w", padx=(12, 12))

        self.preview = tk.Label(image_card, background=theme.CARD, bd=0)
        self.preview.grid(row=2, column=0, columnspan=3, sticky="w", padx=12,
                          pady=(8, 12))

        # ---------------- log input ---------------------------------------
        ttk.Label(outer, text=f"{theme.DECOR['search']} [2] 或者把日志粘在这里",
                  style="Heading.TLabel").grid(row=2, column=0, sticky="w",
                                               pady=(14, 4))

        text_frame = ttk.Frame(outer)
        text_frame.grid(row=3, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.log_input = tk.Text(
            text_frame, height=5, wrap="word", font=self.mono_font, undo=True,
            relief="flat", bd=0, background=theme.CODE_BG, foreground=theme.INK,
            insertbackground=theme.NAVY, highlightthickness=1,
            highlightbackground=theme.LINE, highlightcolor=theme.BLUE,
            padx=10, pady=8,
        )
        self.log_input.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(text_frame, command=self.log_input.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_input.configure(yscrollcommand=log_scroll.set)
        self.log_input.insert(
            "1.0",
            "把 SP Flash Tool / MiFlash / QFIL / fastboot / recovery 的报错粘到这里，"
            "例如：\nBROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)",
        )

        # ---------------- actions -----------------------------------------
        actions = ttk.Frame(outer)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text=f"{theme.DECOR['cat']} 检查一下喵",
                   style="Navy.TButton", command=self.on_analyze).pack(side="left")
        ttk.Button(actions, text="清空", style="Blue.TButton",
                   command=self.on_clear).pack(side="left", padx=(8, 0))

        self.status = ttk.Label(actions, text=self._status_text(), style="Status.TLabel")
        self.status.pack(side="left", padx=(14, 0))

        # ---------------- results -----------------------------------------
        ttk.Label(outer, text=f"{theme.DECOR['sparkle']} [3] 诊断结果与解决方案",
                  style="Heading.TLabel").grid(row=5, column=0, sticky="w",
                                               pady=(8, 4))

        result_frame = ttk.Frame(outer)
        result_frame.grid(row=7, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.output = tk.Text(
            result_frame, wrap="word", font=self.mono_font, relief="flat", bd=0,
            background=theme.CODE_BG, foreground=theme.INK, padx=10, pady=8,
            highlightthickness=1, highlightbackground=theme.LINE,
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        out_scroll = ttk.Scrollbar(result_frame, command=self.output.yview)
        out_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=out_scroll.set)
        self.output.insert("1.0", self._initial_output())
        self.output.configure(state="disabled")

        footer = ttk.Frame(outer)
        footer.grid(row=8, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            footer,
            text=f"{theme.DECOR['heart']} 完全离线运行，内容不会离开本机 · "
                 f"由 {theme.CHARACTER_NAME} 陪你排查",
            style="Status.TLabel",
        ).pack(side="left")

    def _load_sheet(self, parent) -> None:
        """Show the user-provided character sheet in the header.

        The sheet is displayed **whole** - it is not cropped down to a face
        because the user asked for the original artwork to be used as-is. The
        full 4:3 sheet is scaled to fit the header slot.
        """
        path = theme.find_sheet()
        if path is None:
            return
        try:
            self._sheet_image = load_photo(path, (176, 132), theme.BG)
            tk.Label(parent, image=self._sheet_image, background=theme.BG, bd=0).grid(
                row=0, column=0, sticky="nw"
            )
        except Exception:
            self._sheet_image = None

    # -- helpers -----------------------------------------------------------

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")
        self.output.see("1.0")

    def _get_log(self) -> str:
        return self.log_input.get("1.0", "end").strip()

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

    def _image_status_text(self) -> str:
        if self.recognizer is None:
            first = self.recognition_error.splitlines()[0] if self.recognition_error else ""
            return f"图片识别不可用：{first}"
        counts = self.recognizer.reference_counts()
        total = sum(counts.values())
        real = sum(1 for r in self.recognizer.library.references if r.source == "user")
        note = "（含真实照片）" if real else "（仅合成示意图，真机准确率未知）"
        return f"图片识别就绪：{len(counts)} 类 / {total} 张参考图{note}"

    def _show_error(self, title: str, message: str) -> None:
        try:
            messagebox.showerror(title, message, parent=self.root)
        except Exception:
            pass

    # -- event handlers ----------------------------------------------------

    def on_pick_image(self) -> None:
        if self.recognizer is None:
            self._set_output(
                "图片识别不可用。\n\n"
                f"{self.recognition_error}\n\n"
                "仍然可以把报错文字粘贴到日志框检索。"
            )
            return
        try:
            chosen = filedialog.askopenfilename(
                title="选一张报错截图或照片",
                filetypes=IMAGE_FILETYPES,
                parent=self.root,
            )
        except Exception as exc:
            self._show_error("无法打开文件选择器", f"{type(exc).__name__}: {exc}")
            return
        if not chosen:
            return
        self.load_image(Path(chosen))

    def load_image(self, path: Path) -> None:
        """Show an image and recognise it. Also used by tests."""
        self.current_image = Path(path)
        self._show_preview(self.current_image)
        self.image_label.configure(text=f"当前图片：{self.current_image.name}")

        if self.recognizer is None or self.kb is None:
            return

        result = self.recognizer.recognize_path(self.current_image)
        _, report_text = recognition_report(self.kb, result)
        self._set_output(report_text)

        if result.matched:
            self.status.configure(
                text=f"{theme.DECOR['sparkle']} 认出这是「{result.title}」"
                     f"（置信度 {result.confidence:.0%}）"
            )
        else:
            self.status.configure(text=theme.not_found())

    def _show_preview(self, path: Path) -> None:
        try:
            self._preview_image = load_photo(path, (300, 150), theme.CARD)
            self.preview.configure(image=self._preview_image, text="")
        except Exception as exc:
            self._preview_image = None
            self.preview.configure(image="", text=f"（预览不可用：{type(exc).__name__}）")

    def on_clear_image(self) -> None:
        self.current_image = None
        self._preview_image = None
        try:
            self.preview.configure(image="", text="")
        except Exception:
            pass
        self.image_label.configure(text=self._image_status_text())

    def on_analyze(self) -> None:
        text = self._get_log()
        # Ignore the placeholder we pre-fill, so a stray click does not "analyse"
        # the hint text.
        if not text or text.startswith("把 SP Flash Tool"):
            self._set_output(
                "先粘一段报错日志进来，或者放一张截图，喵～\n\n"
                "（输入框里那段是提示文字，会被忽略）"
            )
            return
        if self.kb is None:
            self._set_output(self._initial_output())
            return

        self.status.configure(text=theme.analyzing())
        self.root.update_idletasks()

        try:
            finding, matches, report_text = build_report(self.kb, text, limit=5)
        except Exception as exc:
            self._set_output(f"检索时出错：{exc}")
            return

        self._set_output(report_text)
        if matches:
            self.status.configure(
                text=f"{theme.found(len(matches))} 判定：{finding.platform_label}"
                     f"（置信度 {finding.confidence:.0%}）"
            )
        else:
            self.status.configure(
                text=f"{theme.DECOR['cat']} 判定：{finding.platform_label}"
                     f"，但知识库没找到匹配条目"
            )

    def on_clear(self) -> None:
        self.log_input.delete("1.0", "end")
        self._set_output(self._initial_output())
        self.status.configure(text=self._status_text())
        self.on_clear_image()

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    """Entry point."""
    MiRecoveryTkApp().run()


if __name__ == "__main__":
    run()
