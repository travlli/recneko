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

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from . import theme
from .kb import KB
from .logsetup import get_logger
from .online import config_path, research
from .recognize import load_default_recognizer
from .report import build_report, empty_report, recognition_report

logger = get_logger(__name__)

# How often the UI thread checks for a finished background recognition.
RESULT_POLL_MS = 60

# The result box grows to fit its content (the page scrolls instead), so these
# only bound the extremes: never smaller than a usable few lines, and a cap so a
# pathological paste cannot build a 10000-line widget.
MIN_OUTPUT_LINES = 14
MAX_OUTPUT_LINES = 400

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


# Placeholder support for the log box. Tk's Text widget has no placeholder, so
# the hint is inserted as tagged grey text that the app knows to ignore.
HINT_TAG = "log_hint"
LOG_HINT = (
    "把 SP Flash Tool / MiFlash / QFIL / fastboot / recovery 的报错粘到这里，"
    "例如：\nBROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"
)


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
        # Results from the recognition worker; polled on the UI thread.
        self._results: queue.Queue = queue.Queue()

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
            logger.info("知识库已加载：%d 条（%s）", len(self.kb.entries), self.kb.version)
        except Exception as exc:
            self.kb_error = str(exc)
            logger.error("知识库加载失败: %s", exc, exc_info=True)

        self.recognizer, self.recognition_error = load_default_recognizer()
        if self.recognizer is None:
            logger.error("图片识别不可用: %s", self.recognition_error)
        else:
            counts = self.recognizer.reference_counts()
            logger.info(
                "参考图库已加载：%d 类 / %d 张", len(counts), sum(counts.values())
            )
            if self.recognition_error:
                logger.warning("参考图库部分问题: %s", self.recognition_error)

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

        outer = self._build_scroll_area()
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

        # A real placeholder: grey hint text that lives in the widget but is
        # NOT treated as user input. Previously the hint was ordinary editable
        # text, so a user who pasted their log underneath it ended up searching
        # for the hint's own keywords ("SP Flash Tool / MiFlash / QFIL /
        # fastboot / recovery") - which polluted the detected platform signals
        # and dragged confidence from 100% down to 63%.
        self.log_input.tag_configure(HINT_TAG, foreground="#9aa6bd")
        self._hint_active = False
        # Text read off the last analysed screenshot, reused by the buttons when
        # the log box is empty.
        self._image_ocr_text = ""
        self._show_log_hint()
        self.log_input.bind("<FocusIn>", self._on_log_focus_in)
        self.log_input.bind("<FocusOut>", self._on_log_focus_out)
        self.log_input.bind("<Key>", self._on_log_key)

        # ---------------- actions -----------------------------------------
        actions = ttk.Frame(outer)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text=f"{theme.DECOR['cat']} 检查一下喵",
                   style="Navy.TButton", command=self.on_analyze).pack(side="left")
        ttk.Button(actions, text="清空", style="Blue.TButton",
                   command=self.on_clear).pack(side="left", padx=(8, 0))

        # Online lookup is opt-in and disabled unless configured, because the
        # app's promise is that logs never leave the machine. The button is shown
        # greyed out with an explanatory tooltip rather than hidden, so the
        # feature is discoverable without being accidentally used.
        self.online_button = ttk.Button(
            actions,
            text="联网查询",
            style="Blue.TButton",
            command=self.on_online_lookup,
        )
        self.online_button.pack(side="left", padx=(8, 0))
        self._refresh_online_button()

        ttk.Button(actions, text="设置", style="Blue.TButton",
                   command=self.open_settings).pack(side="left", padx=(8, 0))

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
            # Grown to fit its content by _autosize_output; this is just the
            # starting height before any result exists.
            height=MIN_OUTPUT_LINES,
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        out_scroll = ttk.Scrollbar(result_frame, command=self.output.yview)
        out_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=out_scroll.set)
        self.output.insert("1.0", self._initial_output())
        self.output.configure(state="disabled")
        self._autosize_output()

        footer = ttk.Frame(outer)
        footer.grid(row=8, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            footer,
            text=f"{theme.DECOR['heart']} 完全离线运行，内容不会离开本机 · "
                 f"由 {theme.CHARACTER_NAME} 陪你排查",
            style="Status.TLabel",
        ).pack(side="left")

    def _build_scroll_area(self) -> ttk.Frame:
        """Create the scrollable page and return the frame to put content in.

        Why this exists: the whole window used to be one frame packed with
        ``fill/expand``. When the window was shorter than the content - a small
        screen, or the user dragging the window small - the lower part (the
        results) was simply cut off with no way to reach it. The results box has
        its own scrollbar, but that only helps once you can see it.

        Layout: a canvas holds a single inner frame. The inner frame is forced to
        at least the viewport height, so when everything fits the ``weight`` rows
        still stretch to fill the window; when it does not fit, the canvas scrolls.
        The scrollbar hides itself whenever there is nothing to scroll.
        """
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            container, background=theme.BG, highlightthickness=0, bd=0, takefocus=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.page_scroll = ttk.Scrollbar(
            container, orient="vertical", command=self.canvas.yview
        )
        self.page_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self._on_page_scroll)

        page = ttk.Frame(self.canvas, padding=(14, 12, 14, 12))
        self.page = page
        self._page_window = self.canvas.create_window((0, 0), window=page, anchor="nw")
        self._page_height = 0
        self._page_width = 0
        self._syncing = False

        page.bind("<Configure>", self._on_page_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Re-apply the page size when the window is shown again: a canvas window
        # item reverts to the widget's requested size while unmapped, and neither
        # Configure handler fires on remap, so nothing would put it back.
        self.canvas.bind("<Map>", lambda _e: self._sync_page_size())
        self.root.bind("<Map>", lambda _e: self._sync_page_size())

        # Wheel events reach the widget under the pointer and then bubble to the
        # toplevel, so binding here catches the whole page. Text widgets scroll
        # themselves via their class binding, so the handler steps aside for them
        # to avoid scrolling twice.
        self.root.bind("<MouseWheel>", self._on_mousewheel)          # Windows/macOS
        self.root.bind("<Button-4>", self._on_mousewheel)            # X11 up
        self.root.bind("<Button-5>", self._on_mousewheel)            # X11 down
        self.root.bind("<Prior>", lambda e: self._scroll_page(-1))   # PageUp
        self.root.bind("<Next>", lambda e: self._scroll_page(1))     # PageDown
        self.root.bind("<Home>", lambda e: self.canvas.yview_moveto(0))
        self.root.bind("<End>", lambda e: self.canvas.yview_moveto(1))
        return page

    # -- page scrolling ----------------------------------------------------

    def _on_page_scroll(self, first: str, last: str) -> None:
        """Hide the scrollbar when the whole page already fits."""
        try:
            fits = float(first) <= 0.0 and float(last) >= 1.0
        except (TypeError, ValueError):
            fits = False
        if fits:
            self.page_scroll.grid_remove()
        else:
            self.page_scroll.grid()
        self.page_scroll.set(first, last)

    def _on_page_configure(self, _event=None) -> None:
        """Keep the scroll region and the page size in step with the content.

        Both dimensions are re-applied here, not only when the canvas resizes.
        When the result box grows, the page's requested size changes, and if the
        canvas window keeps its old size the grid squeezes the page back down -
        the result box then stays short and keeps its own scrollbar no matter how
        large a height it asks for. (Measured: the widget asked for 137 lines and
        was rendered at 359px.)
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_page_size()

    def _sync_page_size(self) -> None:
        """Force the page to the viewport width and at least the viewport height.

        Applied unconditionally (with a re-entrancy guard) rather than guarded by
        a cached value. The cache made this skip whenever it *thought* the size was
        already right, while the canvas item had in fact drifted back to the
        widget's requested width - which happens after the window is withdrawn and
        shown again. Measured: the page sat at 934px inside an 886px canvas and
        never converged, so the right-hand side was clipped.
        """
        if self._syncing:
            return
        self._syncing = True
        try:
            width = self.canvas.winfo_width()
            if width > 1:
                self.canvas.itemconfigure(self._page_window, width=width)
            needed = max(self.page.winfo_reqheight(), self.canvas.winfo_height())
            self.canvas.itemconfigure(self._page_window, height=needed)
        finally:
            self._syncing = False

    def _on_canvas_configure(self, event) -> None:
        """Keep the page as wide as the viewport, and at least as tall."""
        self.canvas.itemconfigure(self._page_window, width=event.width)
        self._sync_page_size()

    def _scroll_page(self, direction: int) -> None:
        self.canvas.yview_scroll(direction, "pages")

    def _on_mousewheel(self, event) -> None:
        # A Text under the pointer scrolls itself; leave it alone so the wheel
        # does not move two things at once.
        if isinstance(event.widget, (tk.Text, tk.Listbox)):
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            step = -1 if getattr(event, "delta", 0) > 0 else 1
            delta = step * 3
        self.canvas.yview_scroll(delta, "units")

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

    # -- log placeholder ---------------------------------------------------

    def _show_log_hint(self) -> None:
        if self._hint_active:
            return
        self.log_input.delete("1.0", "end")
        self.log_input.insert("1.0", LOG_HINT, HINT_TAG)
        self._hint_active = True

    def _hide_log_hint(self) -> None:
        if not self._hint_active:
            return
        self.log_input.delete("1.0", "end")
        self._hint_active = False

    def _on_log_focus_in(self, _event=None) -> None:
        self._hide_log_hint()

    def _on_log_focus_out(self, _event=None) -> None:
        if not self._get_log():
            self._show_log_hint()

    def _on_log_key(self, _event=None) -> None:
        # Any real keystroke replaces the hint.
        self._hide_log_hint()

    # -- helpers -----------------------------------------------------------

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")
        self.output.see("1.0")
        self._autosize_output()
        self._reveal_output()

    def _autosize_output(self) -> None:
        """Grow the result box until all of it is visible.

        The box used to be a fixed 8 lines with its own scrollbar, so a full
        solution report (4-6k characters, ~70 wrapped lines) was squeezed into a
        window barely a sixth of its size. The page itself scrolls now, so the
        box can simply be as tall as its content and the user scrolls the page -
        one scrollbar instead of a cramped nested one.

        ``displaylines`` counts wrapped lines, which is what ``height`` measures,
        so long lines are accounted for rather than undercounted.
        """
        try:
            self.output.update_idletasks()
            try:
                counted = self.output.count("1.0", "end-1c", "displaylines")
                if isinstance(counted, tuple):
                    counted = counted[0]
                lines = int(counted or 0)
            except Exception:
                # Fall back to logical lines if the Tk build lacks displaylines.
                lines = int(self.output.index("end-1c").split(".")[0])

            wanted = max(MIN_OUTPUT_LINES, min(lines + 2, MAX_OUTPUT_LINES))
            self.output.configure(height=wanted)
            self.output.update_idletasks()

            # Counting display lines is close but not exact - the widget's
            # internal padding eats part of a line - so nudge the height until the
            # content genuinely fits. Cheaper and more reliable than a magic
            # offset, and it stops as soon as there is nothing left to scroll.
            for _ in range(8):
                if wanted >= MAX_OUTPUT_LINES:
                    break
                if self.output.yview()[1] >= 0.999:
                    break
                wanted = min(wanted + 2, MAX_OUTPUT_LINES)
                self.output.configure(height=wanted)
                self.output.update_idletasks()

            self.page.update_idletasks()
        except Exception:
            logger.debug("调整结果框高度失败", exc_info=True)

    def _offset_in_page(self, widget) -> int:
        """Vertical position of ``widget`` inside the scrollable page."""
        offset = 0
        current = widget
        while current is not None and current is not self.page:
            offset += current.winfo_y()
            current = current.master
            if current is None:
                break
        return offset

    def _reveal_output(self) -> None:
        """Scroll the page so the result box is on screen.

        Without this the answer was written below the fold and the user saw
        nothing happen: on the development display the results box sits at
        y=509-663 while the viewport is only ~500px tall, so every button looked
        broken even though it had worked.
        """
        try:
            self._sync_page_size()
            self.page.update_idletasks()
            page_height = self.page.winfo_reqheight()
            if page_height <= 0:
                return
            top = self._offset_in_page(self.output)
            # Leave a little context above, and never scroll past the bottom.
            target = max(0.0, (top - 16) / page_height)
            self.canvas.yview_moveto(min(target, 1.0))
        except Exception:
            logger.debug("滚动到结果区失败", exc_info=True)

    def _get_log(self) -> str:
        """The user's actual log text, never the placeholder."""
        if self._hint_active:
            return ""
        return self.log_input.get("1.0", "end").strip()

    def _effective_text(self) -> tuple[str, str]:
        """The text to analyse, and where it came from.

        Returns ``(text, source)`` where source is ``"log"``, ``"image"`` or
        ``""``.

        A loaded screenshot already has readable text - OCR ran when the image
        was opened - so the buttons should use it instead of telling the user to
        paste a log. Measured: with an image loaded and the log box empty, both
        "检查一下喵" and "联网查询" replied "先粘一段报错日志" and ignored the
        screenshot entirely, which reads as "nothing happened".
        """
        log = self._get_log()
        if log:
            return log, "log"
        image_text = getattr(self, "_image_ocr_text", "")
        if image_text.strip():
            return image_text, "image"
        return "", ""

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

    def load_image(self, path: Path, *, blocking: bool = False) -> None:
        """Show an image and recognise it.

        Recognition runs on a worker thread and the result is marshalled back
        with ``after()``. Decoding a 12 MP phone photo took ~1.8 s before the
        JPEG draft optimisation, and doing that on the Tk thread froze the
        window with no feedback at all.

        ``blocking=True`` runs inline - used by tests, which need the result
        before they can assert on it.
        """
        self.current_image = Path(path)
        self._show_preview(self.current_image)
        self.image_label.configure(text=f"当前图片：{self.current_image.name}")

        if self.recognizer is None or self.kb is None:
            return

        if blocking:
            self._finish_recognition(self._analyse_image(self.current_image))
            return

        self.status.configure(text=f"{theme.DECOR['search']} 正在读图上的文字…")
        self._set_output("正在识别图片（先读文字，再比对画面），请稍候…")
        target = self.current_image

        def worker() -> None:
            try:
                analysis = self._analyse_image(target)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("图片识别线程异常")
                self._results.put(("error", str(exc)))
                return
            self._results.put(("ok", analysis))

        threading.Thread(target=worker, daemon=True).start()
        # Tk's after() must only be called from the thread running the event
        # loop, so the worker cannot schedule its own callback - it hands the
        # result over through a queue and the UI thread polls for it.
        self.root.after(RESULT_POLL_MS, self._poll_results)

    def _analyse_image(self, path):
        """Full image pipeline (runs on the worker thread)."""
        from .report import analyze_image

        return analyze_image(self.kb, self.recognizer, path)

    def _poll_results(self) -> None:
        """Drain worker results on the UI thread."""
        try:
            kind, payload = self._results.get_nowait()
        except queue.Empty:
            self.root.after(RESULT_POLL_MS, self._poll_results)
            return

        if kind == "ok":
            self._finish_recognition(payload)
        elif kind == "online":
            self._finish_online(payload)
        else:
            self._recognition_failed(str(payload))

    def _recognition_failed(self, detail: str) -> None:
        self._set_output(f"图片识别失败：{detail}")
        self.status.configure(text="图片识别：失败")

    def _finish_recognition(self, analysis) -> None:
        """Apply an image-analysis result on the UI thread."""
        if self.kb is None or analysis is None:
            return

        self._set_output(analysis.text)

        ocr = getattr(analysis, "ocr", None)
        screen = getattr(analysis, "screen", None)
        keywords = getattr(analysis, "keywords", []) or []

        # Remember the text read off the screenshot so the buttons can reuse it
        # instead of asking the user to paste a log they already gave us as an
        # image.
        self._image_ocr_text = ocr.text if (ocr is not None and ocr.ok) else ""

        if ocr is not None and getattr(ocr, "ok", False):
            detail = f"读出 {len(keywords)} 个关键词" if keywords else "读出文字"
            if analysis.entry is not None:
                self.status.configure(
                    text=f"{theme.DECOR['sparkle']} {detail}，"
                         f"命中「{analysis.entry.title}」"
                )
            else:
                self.status.configure(
                    text=f"{theme.DECOR['cat']} {detail}，但知识库没找到对应条目"
                )
        elif screen is not None and getattr(screen, "matched", False):
            self.status.configure(
                text=f"{theme.DECOR['sparkle']} 认出这是「{screen.title}」"
                     f"（置信度 {screen.confidence:.0%}）"
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
        self._image_ocr_text = ""
        try:
            self.preview.configure(image="", text="")
        except Exception:
            pass
        self.image_label.configure(text=self._image_status_text())

    def open_settings(self) -> None:
        """Open the settings dialog (currently: online lookup)."""
        SettingsDialog(self)

    def _refresh_online_button(self) -> None:
        """Enable online lookup only when it is configured and switched on."""
        from .online import AiConfig

        config = AiConfig.load()
        self._online_config = config
        if config.usable:
            self.online_button.state(["!disabled"])
        else:
            self.online_button.state(["disabled"])

    def on_online_lookup(self) -> None:
        """Ask the user for consent, then research the pasted log online.

        Consent is asked every time, and the dialog states exactly what will be
        sent. Nothing is transmitted if the user declines.
        """
        from .online import AiConfig

        config = AiConfig.load()
        if not config.usable:
            self._set_output(
                "联网查询未启用。\n\n"
                "这是刻意的默认设置：本应用承诺日志和截图不离开本机。\n"
                "要启用，需要配置一个 OpenAI 兼容的接口：\n\n"
                f"  配置文件：{config_path()}\n"
                "  内容示例：\n"
                '    {\n'
                '      "base_url": "https://api.example.com/v1",\n'
                '      "api_key": "你的 key",\n'
                '      "model": "模型名",\n'
                '      "enabled": true\n'
                '    }\n\n'
                "也可以用环境变量 RECNEKO_AI_BASE_URL / RECNEKO_AI_API_KEY / "
                "RECNEKO_AI_MODEL / RECNEKO_AI_ENABLED。\n\n"
                "启用后：只会把**脱敏后**的报错文字发给该接口"
                "（序列号/IMEI/手机号/邮箱/用户名会被替换）。\n"
                "它会先联网搜一遍，再用「搜到的来源 + 模型自身知识」给出解决方案，\n"
                "每条都会标注是 [编号] 还是 [自身知识]，前者可点开核对。"
            )
            self.status.configure(text="联网查询：未启用")
            return

        log, source = self._effective_text()
        if not log.strip():
            self._set_output(
                "还没有可以联网查询的内容。\n\n"
                "先丢一张报错截图进来（会自动读出图上的文字），"
                "或者把报错日志粘贴到上面的输入框。"
            )
            return

        origin = "图片里识别出来的文字" if source == "image" else "输入框里的日志"

        if not messagebox.askyesno(
            "联网查询",
            f"将要把{origin}发送到外部 AI 接口：\n\n"
            f"  {config.base_url}\n"
            f"  模型：{config.model}\n\n"
            "发送前会自动脱敏（序列号 / IMEI / 手机号 / 邮箱 / 用户名）。\n"
            "仍然建议你先自行确认内容可以外发。\n\n"
            "继续吗？",
        ):
            self.status.configure(text="联网查询：已取消")
            return

        self._set_output("正在联网检索，请稍候…（先搜索，再抓取正文，最后由模型整理）")
        self.status.configure(text="联网查询：检索中…")

        def worker() -> None:
            try:
                answer = research(log, config=config)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("联网查询线程异常")
                self._results.put(("error", str(exc)))
                return
            self._results.put(("online", answer))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(RESULT_POLL_MS, self._poll_results)

    def _finish_online(self, answer) -> None:
        """Show the answer, making its provenance clear in the status bar too."""
        from .online import render_answer

        body = render_answer(answer)
        self._set_output(body)
        if not answer.ok:
            self.status.configure(text=f"{theme.DECOR['cat']} 联网查询失败")
            return
        if answer.grounded:
            extra = "，含自身知识" if answer.used_own_knowledge else ""
            self.status.configure(
                text=f"{theme.DECOR['sparkle']} 联网查到 {len(answer.sources)} 条来源"
                     f"{extra}（{answer.tokens} tokens）"
            )
        else:
            self.status.configure(
                text=f"{theme.DECOR['cat']} 无联网来源，方案来自模型自身知识"
                     f"（{answer.tokens} tokens）"
            )

    def on_analyze(self) -> None:
        text, source = self._effective_text()
        if not text:
            self._set_output(
                "还没有可以分析的内容。\n\n"
                "两种用法，任选一种：\n"
                "  · 点「选择图片」丢一张报错截图进来（会自动识别）\n"
                "  · 或者把报错日志粘贴到上面的输入框"
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

        if source == "image":
            report_text = (
                "（上面的输入框是空的，这次用的是**图片里识别出来的文字**）\n\n"
                + report_text
            )
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
        self._hint_active = False
        self._show_log_hint()
        self._set_output(self._initial_output())
        self.status.configure(text=self._status_text())
        self.on_clear_image()

    # -- lifecycle ---------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


class SettingsDialog:
    """Modal settings window.

    Only online lookup is configurable today, but it is built as a small form so
    more sections can be added without reworking the layout.

    Two deliberate choices:

    * The API key is masked by default with a "显示" toggle, and is never logged.
    * "测试连接" actually calls the endpoint. Saving a typo silently is worse than
      an extra second of waiting - the user would otherwise only find out on their
      first real lookup, mid-troubleshooting.
    """

    def __init__(self, app: "MiRecoveryTkApp"):
        from .online import AiConfig, config_candidates, test_connection

        self.app = app
        self._test_connection = test_connection
        self.config = AiConfig.load()

        self.window = tk.Toplevel(app.root)
        self.window.title("设置")
        self.window.configure(background=theme.BG)
        self.window.transient(app.root)
        self.window.resizable(False, False)

        body = ttk.Frame(self.window, padding=18, style="Card.TFrame")
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="设置", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            body,
            text="联网查询：知识库查不到时，联网检索并只依据来源作答。",
            style="Quote.TLabel",
        ).pack(anchor="w", pady=(2, 12))

        # ---- enable toggle ----
        self.enabled_var = tk.BooleanVar(value=self.config.enabled)
        ttk.Checkbutton(
            body,
            text="启用联网查询（默认关闭：开启后才会把日志发送到外部接口）",
            variable=self.enabled_var,
            command=self._on_toggle,
        ).pack(anchor="w")

        # ---- fields ----
        form = ttk.Frame(body)
        form.pack(fill="x", pady=(12, 0))
        form.columnconfigure(1, weight=1)

        self.url_var = tk.StringVar(value=self.config.base_url)
        self.key_var = tk.StringVar(value=self.config.api_key)
        self.model_var = tk.StringVar(value=self.config.model)

        ttk.Label(form, text="API 地址").grid(row=0, column=0, sticky="w", pady=4)
        url_entry = ttk.Entry(form, textvariable=self.url_var, width=46)
        url_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
        ttk.Label(
            form,
            text="OpenAI 兼容接口，通常以 /v1 结尾，例如 https://api.deepseek.com/v1",
            style="Quote.TLabel",
        ).grid(row=1, column=1, sticky="w", padx=(10, 0))

        ttk.Label(form, text="API Key").grid(row=2, column=0, sticky="w", pady=4)
        key_row = ttk.Frame(form)
        key_row.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)
        key_row.columnconfigure(0, weight=1)
        self.key_entry = ttk.Entry(key_row, textvariable=self.key_var, show="●")
        self.key_entry.grid(row=0, column=0, sticky="ew")
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            key_row, text="显示", variable=self.show_key_var, command=self._toggle_key
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(form, text="模型名").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.model_var, width=46).grid(
            row=3, column=1, sticky="ew", padx=(10, 0), pady=4
        )
        ttk.Label(
            form,
            text="例如 deepseek-chat / gpt-4o-mini / qwen2.5:7b（本地 ollama）",
            style="Quote.TLabel",
        ).grid(row=4, column=1, sticky="w", padx=(10, 0))

        # ---- search backends ----
        from .online import BACKEND_LABELS, DEFAULT_BACKENDS

        ttk.Label(body, text="检索范围", style="Heading.TLabel").pack(
            anchor="w", pady=(14, 2)
        )
        ttk.Label(
            body,
            text="勾选要搜的地方。无论搜到多少，只有真正提到这个报错的资料才会被采用。",
            style="Quote.TLabel",
        ).pack(anchor="w")

        chosen = set(self.config.backends or DEFAULT_BACKENDS)
        self.backend_vars: dict[str, tk.BooleanVar] = {}
        backend_box = ttk.Frame(body)
        backend_box.pack(anchor="w", pady=(6, 0))
        for index, (name, (label, note)) in enumerate(BACKEND_LABELS.items()):
            var = tk.BooleanVar(value=name in chosen)
            self.backend_vars[name] = var
            row = ttk.Frame(backend_box)
            row.grid(row=index // 2, column=index % 2, sticky="w",
                     padx=(0, 20), pady=1)
            ttk.Checkbutton(row, text=label, variable=var).pack(side="left")
            if note:
                ttk.Label(row, text=note, style="Quote.TLabel").pack(
                    side="left", padx=(6, 0)
                )

        # ---- status line ----
        self.status_var = tk.StringVar(value="")
        ttk.Label(body, textvariable=self.status_var, style="Status.TLabel",
                  wraplength=520, justify="left").pack(anchor="w", pady=(12, 0))

        # ---- buttons ----
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(14, 0))
        self.test_button = ttk.Button(
            buttons, text="测试连接", style="Blue.TButton", command=self.on_test
        )
        self.test_button.pack(side="left")
        ttk.Button(buttons, text="保存", style="Navy.TButton",
                   command=self.on_save).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="取消", style="Blue.TButton",
                   command=self.close).pack(side="left", padx=(8, 0))

        # ---- where it will be stored ----
        candidates = config_candidates()
        ttk.Label(
            body,
            text=f"配置文件：{candidates[0]}",
            style="Quote.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))
        ttk.Label(
            body,
            text="Key 只存在本机这个文件里，不会写进日志、也不会随程序分发。",
            style="Quote.TLabel",
        ).pack(anchor="w")

        self._on_toggle()
        url_entry.focus_set()

        # Centre on the parent window, then take focus.
        self.window.update_idletasks()
        parent = app.root
        x = parent.winfo_rootx() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.window.winfo_height()) // 3
        self.window.geometry(f"+{max(0, x)}+{max(0, y)}")
        try:
            self.window.grab_set()
        except Exception:
            pass

    # -- widget behaviour --------------------------------------------------

    def _toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key_var.get() else "●")

    def _on_toggle(self) -> None:
        state = "normal" if self.enabled_var.get() else "disabled"
        for child in self.window.winfo_children():
            self._set_entry_state(child, state)
        if not self.enabled_var.get():
            self.status_var.set("联网查询已关闭（离线使用，日志不会外发）")

    def _set_entry_state(self, widget, state: str) -> None:
        if isinstance(widget, ttk.Entry):
            widget.configure(state=state)
        for child in widget.winfo_children():
            self._set_entry_state(child, state)

    # -- actions -----------------------------------------------------------

    def _current(self):
        from .online import AiConfig

        chosen = tuple(
            name for name, var in getattr(self, "backend_vars", {}).items() if var.get()
        )
        return AiConfig(
            base_url=self.url_var.get().strip(),
            api_key=self.key_var.get().strip(),
            model=self.model_var.get().strip(),
            enabled=bool(self.enabled_var.get()),
            timeout=self.config.timeout,
            max_tokens=self.config.max_tokens,
            # Falling back to the defaults beats saving an empty tuple, which
            # would silently disable searching altogether.
            backends=chosen or self.config.backends,
        )

    def on_test(self) -> None:
        config = self._current()
        self.status_var.set("正在测试连接…")
        self.test_button.state(["disabled"])
        self.window.update_idletasks()

        def worker() -> None:
            ok, message = self._test_connection(config)
            self.window.after(0, lambda: self._show_test_result(ok, message))

        threading.Thread(target=worker, daemon=True).start()

    def _show_test_result(self, ok: bool, message: str) -> None:
        try:
            self.test_button.state(["!disabled"])
        except Exception:
            return  # window closed while testing
        prefix = "✅ " if ok else "❌ "
        self.status_var.set(prefix + message)

    def on_save(self) -> None:
        config = self._current()
        # If the user ticked "enable" the three fields are mandatory; otherwise
        # partial values are kept for next time. (An earlier version silently
        # switched itself off when every field was blank, which read as "saved"
        # even though the user had asked for it to be on.)
        if config.enabled and not config.configured:
            missing = [
                name
                for name, value in (
                    ("API 地址", config.base_url),
                    ("API Key", config.api_key),
                    ("模型名", config.model),
                )
                if not value
            ]
            self.status_var.set("❌ 启用了联网查询，但还缺少：" + "、".join(missing))
            return
        if config.base_url and not config.base_url.startswith(("http://", "https://")):
            self.status_var.set("❌ API 地址需要以 http:// 或 https:// 开头")
            return

        try:
            saved = config.save()
        except Exception as exc:
            self.status_var.set(f"❌ 保存失败：{exc}")
            return

        self.app._refresh_online_button()
        logger.info("设置已保存到 %s（enabled=%s）", saved, config.enabled)
        self.close()

    def close(self) -> None:
        try:
            self.window.grab_release()
        except Exception:
            pass
        self.window.destroy()


def run() -> None:
    """Entry point."""
    MiRecoveryTkApp().run()


if __name__ == "__main__":
    run()
