"""GUI tests (tkinter front-end).

One Tk root is created for the whole session and reused. Creating and destroying
a root per test made Tcl intermittently fail to source its own ``init.tcl``
("Can't find a usable init.tcl ..."), which surfaced as flaky errors rather than
real failures - Tk does not support multiple independent interpreters well in
one process. State is reset between tests via ``on_clear()``.

These tests skip cleanly when no display is available. The packaged app's Tk
stack is verified separately by the frozen self test
(``MiRecoveryHelper.selftest.spec``), which builds a real window inside the exe.

Regression covered here: the log hint used to live in the editable buffer, so a
user pasting their log underneath it ended up searching the hint's own keywords
("SP Flash Tool / MiFlash / QFIL / fastboot / recovery") - which polluted the
platform signals and dropped confidence from 100% to 63%.
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture(scope="session")
def app():
    """A single application instance shared by every GUI test."""
    try:
        from mirecovery.tkapp import MiRecoveryTkApp

        instance = MiRecoveryTkApp()
    except Exception as exc:
        pytest.skip(f"本环境无法创建 Tk 窗口：{type(exc).__name__}: {exc}")
    instance.root.withdraw()
    yield instance
    try:
        instance.root.destroy()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_app(app):
    """Return the shared app to a clean state before each test."""
    app.on_clear()
    yield


def test_window_title_uses_display_name(app):
    from mirecovery import theme

    assert theme.APP_DISPLAY_NAME in app.root.title()


def test_data_loaded(app):
    assert app.kb is not None, f"知识库未加载：{app.kb_error}"
    assert len(app.kb.entries) >= 15


def test_placeholder_is_not_user_input(app):
    """The hint must not be returned as the user's log."""
    assert app._hint_active is True
    assert app._get_log() == ""


def test_typing_replaces_placeholder(app):
    app._hide_log_hint()
    app.log_input.insert("1.0", "ERROR 4032")
    assert app._get_log() == "ERROR 4032"


def test_analyze_with_placeholder_shows_prompt(app):
    app._image_ocr_text = ""
    app.on_analyze()
    assert "还没有可以分析的内容" in app.output.get("1.0", "end")


def test_analyze_renders_solution(app):
    app._hide_log_hint()
    app.log_input.insert("1.0", "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)")
    app.on_analyze()
    text = app.output.get("1.0", "end")
    assert "4032" in text
    assert "SP Flash Tool 报错" in text


def test_clear_restores_placeholder(app):
    app._hide_log_hint()
    app.log_input.insert("1.0", "junk")
    app.on_clear()
    assert app._get_log() == ""
    assert app._hint_active is True


def test_image_flow_blocking(app, synthetic_references):
    if app.recognizer is None:
        pytest.skip(f"图片识别不可用：{app.recognition_error}")
    _, path = synthetic_references[0]
    app.load_image(path, blocking=True)
    assert "图片识别结果" in app.output.get("1.0", "end")
    app.on_clear_image()
    assert app.current_image is None


def test_recognition_off_main_thread(app, synthetic_references):
    """Recognition must not block the Tk thread (it used to freeze the window).

    The worker hands its result over through a queue; the UI thread polls with
    ``after``. Tk's ``after`` is not thread-safe, so a worker calling it directly
    raises "main thread is not in main loop".
    """
    if app.recognizer is None:
        pytest.skip("图片识别不可用")
    _, path = synthetic_references[0]
    app.load_image(path)  # non-blocking path
    assert app.status.cget("text")

    deadline = time.time() + 30
    while time.time() < deadline:
        app.root.update()
        if "图片识别结果" in app.output.get("1.0", "end"):
            break
        time.sleep(0.05)  # let the poll timer actually fire
    assert "图片识别结果" in app.output.get("1.0", "end")


# --------------------------------------------------------------------------
# Online lookup must stay opt-in
# --------------------------------------------------------------------------


def test_online_button_disabled_without_config(app, monkeypatch):
    """The app must not be able to send logs anywhere by default."""
    from mirecovery.online import AiConfig

    monkeypatch.setattr(AiConfig, "load", classmethod(lambda cls, path=None: AiConfig()))
    app._refresh_online_button()
    assert "disabled" in app.online_button.state()


def test_online_lookup_explains_how_to_enable(app, monkeypatch):
    from mirecovery.online import AiConfig

    monkeypatch.setattr(AiConfig, "load", classmethod(lambda cls, path=None: AiConfig()))
    app.on_online_lookup()
    text = app.output.get("1.0", "end")
    assert "未启用" in text
    assert "不离开本机" in text
    assert "RECNEKO_AI_BASE_URL" in text


def test_online_lookup_needs_something_to_look_up(app, monkeypatch):
    from mirecovery.online import AiConfig

    configured = AiConfig(
        base_url="http://example.invalid/v1", api_key="k", model="m", enabled=True
    )
    monkeypatch.setattr(AiConfig, "load", classmethod(lambda cls, path=None: configured))
    app.on_clear()  # placeholder active -> no user log
    app._image_ocr_text = ""
    app.on_online_lookup()
    assert "还没有可以联网查询的内容" in app.output.get("1.0", "end")


# --------------------------------------------------------------------------
# Page scrolling
# --------------------------------------------------------------------------
#
# The window used to be one frame packed with fill/expand, so on a short screen
# the lower half (the results) was cut off with no way to reach it. Measured on
# the development display (1337x617) the content needs ~706px, so it genuinely
# does not fit - scrolling is not cosmetic here.


def test_page_lives_in_a_scrollable_canvas(app):
    import tkinter as tk

    assert isinstance(app.canvas, tk.Canvas)
    # The content frame is a canvas item, i.e. it can be scrolled.
    items = app.canvas.find_all()
    assert items, "内容没有放进画布"
    assert app.canvas.type(items[0]) == "window"


@pytest.fixture
def visible_app(app):
    """The shared app with its window actually mapped.

    The session fixture keeps the window withdrawn, and a withdrawn window never
    gets a real canvas height - unit-based scrolling then moves a fraction of a
    pixel and looks like "nothing happened". Scrolling tests need a mapped window.

    The window is left mapped afterwards on purpose: withdrawing and re-showing it
    makes Tk reset the canvas window item to the widget's requested width, and
    because the canvas size does not change in between, no Configure event fires to
    put it back. That is an artefact of repeatedly hiding the window, not
    something a real user hits.
    """
    app.root.deiconify()
    app.root.update()
    yield app


def _settle(widget, rounds: int = 6) -> None:
    for _ in range(rounds):
        widget.update()
        widget.update_idletasks()


def _settle_until(widget, predicate, rounds: int = 30) -> bool:
    """Pump the event loop until ``predicate()`` holds.

    Layout changes ripple through several Configure events, so a fixed number of
    ``update()`` calls is not always enough - and the count needed depends on what
    the previous test left behind. Waiting for the condition keeps the test
    deterministic without weakening the assertion.
    """
    for _ in range(rounds):
        widget.update()
        widget.update_idletasks()
        if predicate():
            return True
    return predicate()


def _content_overflows(application) -> bool:
    """Whether the page is taller than the viewport.

    Compares heights rather than ``yview()[1] >= 1.0``: that fraction also
    reaches 1.0 when the page is simply scrolled to the bottom, which made an
    earlier version of these tests skip whenever a previous test had left the
    page scrolled down.
    """
    return application.page.winfo_reqheight() > application.canvas.winfo_height()


def test_short_window_becomes_scrollable(visible_app):
    """Shrinking the window must expose a scrollbar instead of hiding content."""
    visible_app.root.geometry("900x400")
    _settle(visible_app.root)

    if not _content_overflows(visible_app):
        pytest.skip("本机窗口足够高，内容放得下")
    assert visible_app.page_scroll.winfo_ismapped(), "内容超出窗口却没有滚动条"

    visible_app.canvas.yview_moveto(1.0)
    visible_app.root.update_idletasks()
    assert visible_app.canvas.yview()[1] == pytest.approx(1.0, abs=0.01), "滚不到底部"
    visible_app.canvas.yview_moveto(0.0)


def test_page_width_follows_the_viewport(visible_app):
    """The page must not stay at its initial width after a resize."""
    visible_app.root.geometry("900x400")
    settled = _settle_until(
        visible_app.root,
        lambda: abs(
            visible_app.page.winfo_width() - visible_app.canvas.winfo_width()
        ) <= 2,
    )
    assert settled, (
        f"页面宽度 {visible_app.page.winfo_width()} 没跟上画布 "
        f"{visible_app.canvas.winfo_width()}"
    )


def test_wheel_scrolls_the_page(visible_app):
    visible_app.root.geometry("900x400")
    _settle(visible_app.root)
    if not _content_overflows(visible_app):
        pytest.skip("本机窗口足够高，内容放得下")

    # Start from the top so "did it move down?" is unambiguous.
    visible_app.canvas.yview_moveto(0.0)
    visible_app.root.update_idletasks()

    class FakeEvent:
        widget = visible_app.canvas
        delta = -120
        num = None

    before = visible_app.canvas.yview()[0]
    visible_app._on_mousewheel(FakeEvent())
    visible_app.root.update_idletasks()
    assert visible_app.canvas.yview()[0] > before, "滚轮没有滚动页面"


def test_wheel_over_text_does_not_scroll_the_page(visible_app):
    """Text widgets scroll themselves; the page must not move as well."""
    visible_app.root.geometry("900x400")
    _settle(visible_app.root)

    class FakeEvent:
        widget = visible_app.output
        delta = -120
        num = None

    before = visible_app.canvas.yview()[0]
    visible_app._on_mousewheel(FakeEvent())
    visible_app.root.update_idletasks()
    assert visible_app.canvas.yview()[0] == pytest.approx(before, abs=1e-6)


def test_scrollbar_hides_when_everything_fits(visible_app):
    """No scrollbar when there is nothing to scroll."""
    needed = visible_app.page.winfo_reqheight()
    screen_h = visible_app.root.winfo_screenheight()
    if needed + 40 > screen_h - 60:
        pytest.skip("本机屏幕放不下全部内容，无法验证隐藏行为")
    visible_app.root.geometry(f"1000x{needed + 40}")
    _settle(visible_app.root)
    assert not visible_app.page_scroll.winfo_ismapped()


# --------------------------------------------------------------------------
# "Loading an image does nothing" - the two bugs behind it
# --------------------------------------------------------------------------
#
# Measured on the development display: the results box sits at y=509-663 while
# the viewport is only ~500px tall, so the answer was written entirely below the
# fold and the user saw nothing happen. Separately, both buttons read only the
# log box, so with a screenshot loaded they replied "先粘一段报错日志" and ignored
# the image completely.


def test_output_is_scrolled_into_view(app):
    """Producing a result must reveal it, not write it below the fold."""
    app.root.geometry("900x420")
    for _ in range(6):
        app.root.update()
        app.root.update_idletasks()

    app.canvas.yview_moveto(0.0)
    app.root.update_idletasks()
    assert app.canvas.yview()[0] == pytest.approx(0.0, abs=0.01)

    app._set_output("=" * 40 + "\n 结果\n" + "=" * 40)
    app.root.update_idletasks()

    page_h = app.page.winfo_reqheight()
    first, last = app.canvas.yview()
    visible_from, visible_to = first * page_h, last * page_h
    top = app._offset_in_page(app.output)
    bottom = top + app.output.winfo_height()
    assert top < visible_to and bottom > visible_from, (
        f"结果框 {top}-{bottom} 不在可见范围 {visible_from:.0f}-{visible_to:.0f} 内"
    )


def test_effective_text_prefers_the_log(app):
    app._hide_log_hint()
    app.log_input.insert("1.0", "ERROR 4032")
    app._image_ocr_text = "从图片读到的文字"
    assert app._effective_text() == ("ERROR 4032", "log")


def test_effective_text_falls_back_to_the_image(app):
    """A loaded screenshot already has text; the buttons must use it."""
    app.on_clear()  # placeholder active -> empty log
    app._image_ocr_text = "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"
    text, source = app._effective_text()
    assert source == "image"
    assert "4032" in text


def test_effective_text_empty_when_nothing_available(app):
    app.on_clear()
    app._image_ocr_text = ""
    assert app._effective_text() == ("", "")


def test_analyze_uses_the_image_when_the_log_is_empty(app):
    """Regression: this used to answer "先粘一段报错日志" with an image loaded."""
    app.on_clear()
    app._image_ocr_text = "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"
    app.on_analyze()
    text = app.output.get("1.0", "end")
    assert "先粘一段报错日志" not in text
    assert "图片里识别出来的文字" in text
    assert "4032" in text


def test_analyze_says_so_when_there_is_nothing(app):
    app.on_clear()
    app._image_ocr_text = ""
    app.on_analyze()
    assert "还没有可以分析的内容" in app.output.get("1.0", "end")


def test_online_lookup_uses_the_image_when_the_log_is_empty(app, monkeypatch):
    """It must reach the consent dialog, not refuse for lack of a pasted log."""
    from mirecovery.online import AiConfig
    import mirecovery.tkapp as tkapp

    configured = AiConfig(
        base_url="http://example.invalid/v1", api_key="k", model="m", enabled=True
    )
    monkeypatch.setattr(AiConfig, "load", classmethod(lambda cls, path=None: configured))
    monkeypatch.setattr(tkapp, "config_path", lambda: "X:/ai.json")
    # Decline the confirmation: proves we got past the "no text" guard without
    # actually sending anything.
    monkeypatch.setattr(tkapp.messagebox, "askyesno", lambda *a, **k: False)

    app.on_clear()
    app._image_ocr_text = "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"
    app.on_online_lookup()
    text = app.output.get("1.0", "end")
    assert "先粘贴一段报错日志" not in text
    assert "已取消" in app.status.cget("text")


def test_online_lookup_says_so_when_there_is_nothing(app, monkeypatch):
    from mirecovery.online import AiConfig

    configured = AiConfig(
        base_url="http://example.invalid/v1", api_key="k", model="m", enabled=True
    )
    monkeypatch.setattr(AiConfig, "load", classmethod(lambda cls, path=None: configured))
    app.on_clear()
    app._image_ocr_text = ""
    app.on_online_lookup()
    assert "还没有可以联网查询的内容" in app.output.get("1.0", "end")


def test_clearing_the_image_forgets_its_text(app):
    app._image_ocr_text = "BROM ERROR 4032"
    app.on_clear_image()
    assert app._image_ocr_text == ""
    assert app._effective_text() == ("", "")


# --------------------------------------------------------------------------
# The result box must expand to fit its content
# --------------------------------------------------------------------------
#
# It used to be a fixed 8 lines with its own scrollbar, so a full solution report
# (~4-6k characters, ~120 wrapped lines) was crammed into a sixth of its size.
# The page scrolls now, so the box should simply be as tall as the content.


def _output_lines(app) -> int:
    counted = app.output.count("1.0", "end-1c", "displaylines")
    return int(counted[0] if isinstance(counted, tuple) else counted)


def test_short_output_stays_at_the_minimum(app):
    from mirecovery.tkapp import MIN_OUTPUT_LINES

    app._set_output("短内容")
    app.root.update_idletasks()
    assert int(app.output.cget("height")) == MIN_OUTPUT_LINES


def test_long_output_expands_and_hides_nothing(app):
    """Nothing may be left hidden behind the box's own scrollbar."""
    from mirecovery.tkapp import MIN_OUTPUT_LINES

    app.root.geometry("1000x497")
    _settle(app.root)
    app._set_output("\n".join(f"第 {i} 行：这是一段用来撑高结果框的文字" for i in range(120)))
    _settle(app.root)

    height = int(app.output.cget("height"))
    shown = _output_lines(app)
    assert height > MIN_OUTPUT_LINES, "长内容没有把结果框撑开"
    assert height > shown, f"结果框 {height} 行装不下 {shown} 行内容"
    # The decisive check: the widget itself must not need scrolling any more.
    assert app.output.yview()[1] >= 0.999, "结果框内部仍在滚动，内容没有全部展开"


def test_output_height_is_capped(app):
    from mirecovery.tkapp import MAX_OUTPUT_LINES

    app._set_output("X" * 40 + "\n" * (MAX_OUTPUT_LINES * 2))
    _settle(app.root)
    assert int(app.output.cget("height")) == MAX_OUTPUT_LINES


def test_page_grows_with_the_result_box(app):
    """The canvas window must follow the content, or the box gets squeezed."""
    app.root.geometry("1000x497")
    _settle(app.root)
    before = app.page.winfo_reqheight()
    app._set_output("\n".join(f"行 {i}" for i in range(100)))
    _settle(app.root, rounds=10)
    assert app.page.winfo_reqheight() > before
    # The page must actually be rendered at its requested height, not clipped.
    assert app.page.winfo_height() >= app.page.winfo_reqheight() - 2, (
        "页面被压扁了，结果框会被挤回去"
    )


# --------------------------------------------------------------------------
# Settings dialog
# --------------------------------------------------------------------------


@pytest.fixture
def dialog(app, monkeypatch, tmp_path):
    """A settings dialog isolated from the real config file."""
    from mirecovery.online import AiConfig

    monkeypatch.setattr(
        AiConfig, "load", classmethod(lambda cls, path=None: AiConfig())
    )
    from mirecovery.tkapp import SettingsDialog

    instance = SettingsDialog(app)
    instance.window.update_idletasks()
    yield instance
    try:
        instance.window.destroy()
    except Exception:
        pass


def test_settings_dialog_has_api_fields(dialog):
    """The whole point: the API address must be editable in the UI."""
    assert dialog.window.title() == "设置"
    assert hasattr(dialog, "url_var")
    assert hasattr(dialog, "key_var")
    assert hasattr(dialog, "model_var")
    assert dialog.enabled_var.get() is False


def test_api_key_is_masked_by_default(dialog):
    assert dialog.key_entry.cget("show") == "●"
    dialog.show_key_var.set(True)
    dialog._toggle_key()
    assert dialog.key_entry.cget("show") == ""


def test_settings_defaults_to_disabled_with_explanation(dialog):
    assert "关闭" in dialog.status_var.get()


def test_settings_rejects_enabled_but_incomplete(dialog):
    dialog.enabled_var.set(True)
    dialog._on_toggle()
    dialog.on_save()
    text = dialog.status_var.get()
    assert "缺少" in text
    assert "API 地址" in text
    # Must not close: nothing was saved.
    assert dialog.window.winfo_exists()


def test_settings_rejects_bad_scheme(dialog):
    dialog.enabled_var.set(True)
    dialog._on_toggle()
    dialog.url_var.set("ftp://example.com/v1")
    dialog.key_var.set("k")
    dialog.model_var.set("m")
    dialog.on_save()
    assert "http" in dialog.status_var.get()
    assert dialog.window.winfo_exists()


def test_settings_lists_search_backends(dialog):
    """The search scope must be visible and adjustable, not GitHub-only."""
    from mirecovery.online import BACKEND_LABELS, DEFAULT_BACKENDS

    assert set(dialog.backend_vars) == set(BACKEND_LABELS)
    for name in DEFAULT_BACKENDS:
        assert dialog.backend_vars[name].get(), f"默认后端 {name} 没有被勾选"
    # The ones that do not work reliably here are available but off by default.
    assert not dialog.backend_vars["bing"].get()
    assert not dialog.backend_vars["xda"].get()


def test_settings_saves_the_chosen_backends(dialog, monkeypatch):
    from mirecovery.online import AiConfig

    saved: dict = {}
    monkeypatch.setattr(
        AiConfig, "save", lambda self, path=None: saved.update(backends=self.backends)
    )
    dialog.enabled_var.set(True)
    dialog._on_toggle()
    dialog.url_var.set("http://x/v1")
    dialog.key_var.set("k")
    dialog.model_var.set("m")
    dialog.backend_vars["bilibili"].set(False)
    dialog.backend_vars["xda"].set(True)
    dialog.on_save()

    assert "xda" in saved["backends"]
    assert "bilibili" not in saved["backends"]


def test_settings_never_saves_an_empty_backend_list(dialog, monkeypatch):
    """Unticking everything must not silently disable searching."""
    from mirecovery.online import AiConfig

    saved: dict = {}
    monkeypatch.setattr(
        AiConfig, "save", lambda self, path=None: saved.update(backends=self.backends)
    )
    dialog.enabled_var.set(True)
    dialog._on_toggle()
    dialog.url_var.set("http://x/v1")
    dialog.key_var.set("k")
    dialog.model_var.set("m")
    for var in dialog.backend_vars.values():
        var.set(False)
    dialog.on_save()
    assert saved["backends"], "后端被清空了"


def test_settings_saves_and_enables_online(app, monkeypatch, tmp_path):
    """Saving must persist and immediately unlock the 联网查询 button."""
    from mirecovery.online import AiConfig

    saved: dict = {}

    def fake_save(self, path=None):
        saved.update(
            base_url=self.base_url, model=self.model, enabled=self.enabled
        )
        return tmp_path / "ai.json"

    monkeypatch.setattr(AiConfig, "save", fake_save)
    monkeypatch.setattr(
        AiConfig, "load", classmethod(lambda cls, path=None: AiConfig())
    )
    from mirecovery.tkapp import SettingsDialog

    instance = SettingsDialog(app)
    instance.enabled_var.set(True)
    instance._on_toggle()
    instance.url_var.set("http://localhost:1234/v1")
    instance.key_var.set("secret")
    instance.model_var.set("m")
    instance.on_save()

    assert saved["base_url"] == "http://localhost:1234/v1"
    assert saved["enabled"] is True
    assert not instance.window.winfo_exists()
