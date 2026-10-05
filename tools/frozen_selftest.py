"""Frozen-build self test.

Bundled as a second PyInstaller target (see MiRecoveryHelper.selftest.spec).
It verifies that the packaged executable can locate and use its bundled
knowledge base, which is the one thing that can silently break in a frozen
build.

Prints machine-readable lines; exits non-zero on failure.
"""

from __future__ import annotations

import sys


def main() -> int:
    # A GBK console cannot encode the UI's ✅/❌ characters; without this the self
    # test dies with UnicodeEncodeError while printing its own diagnostics.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    print(f"frozen = {getattr(sys, 'frozen', False)}")
    print(f"meipass = {getattr(sys, '_MEIPASS', '-')}")

    try:
        from mirecovery.kb import KB
    except Exception as exc:
        print(f"FAIL import: {type(exc).__name__}: {exc}")
        return 1

    try:
        kb = KB.load()
    except Exception as exc:
        print(f"FAIL kb load: {type(exc).__name__}: {exc}")
        return 1

    print(f"entries = {len(kb.entries)}")
    print(f"version = {kb.version}")
    print(f"platforms = {','.join(kb.platforms())}")

    if len(kb.entries) < 18:
        print(f"FAIL expected >=18 entries, got {len(kb.entries)}")
        return 1

    # Exercise retrieval end to end.
    from mirecovery.report import build_report

    finding, matches, text = build_report(
        kb, "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)", limit=3
    )
    print(f"finding = {finding.platform}")
    print(f"matches = {len(matches)}")
    print(f"report_len = {len(text)}")

    if finding.platform != "mtk" or not matches:
        print("FAIL retrieval")
        return 1
    if "4032" not in text:
        print("FAIL report content")
        return 1

    # The shipped GUI module must import. Note: this checks the tkinter
    # front-end, not mirecovery.app - the tkinter build deliberately excludes the
    # whole Toga/.NET stack, so importing it here would fail for the wrong reason
    # (an earlier version of this test did exactly that).
    try:
        import mirecovery.tkapp  # noqa: F401
    except Exception as exc:
        print(f"FAIL tkapp import: {type(exc).__name__}: {exc}")
        return 1
    print("tk_gui = ok")

    # Tk must be usable inside the frozen bundle: the shipped GUI is tkinter.
    try:
        import tkinter

        probe = tkinter.Tk()
        probe.withdraw()
        probe.update_idletasks()
        import tkinter.font as tkfont

        measured = tkfont.Font(font=("Microsoft YaHei UI", 10)).measure("测试")
        probe.destroy()
        print(f"tkinter = {tkinter.TkVersion} (font measure {measured})")
        if measured <= 0:
            print("FAIL tkinter could not measure a CJK font")
            return 1
    except Exception as exc:
        print(f"FAIL tkinter unusable in frozen build: {type(exc).__name__}: {exc}")
        return 1

    # Build-time GUI preference must have travelled with the app (a spec that
    # sets os.environ instead would leave this at None and silently fall back).
    try:
        from mirecovery import _buildcfg

        print(f"buildcfg = {_buildcfg.DEFAULT_GUI}")
    except Exception as exc:
        print(f"FAIL buildcfg import: {type(exc).__name__}: {exc}")
        return 1

    # Logging must be able to create its file, otherwise field failures are
    # invisible (the original build wrote no logs at all).
    try:
        from mirecovery.logsetup import current_log_path, setup_logging

        setup_logging()
        log_path = current_log_path()
        print(f"logfile = {log_path if log_path else '(不可用)'}")
    except Exception as exc:
        print(f"FAIL logging setup: {type(exc).__name__}: {exc}")
        return 1

    # Text recognition must work in the frozen build. The Windows OCR backend is
    # imported lazily, so it is exactly the kind of thing PyInstaller drops
    # silently - and without it the app falls back to the much weaker built-in
    # matcher.
    try:
        from mirecovery.ocr import available_backends, recognize_text

        backends = available_backends()
        print(f"ocr_backends = {backends}")
        if "windows" not in backends:
            print("FAIL 打包后缺少 Windows OCR 后端（winsdk 未被收集？）")
            return 1

        # End-to-end: render a log line, read it back.
        from PIL import Image, ImageDraw, ImageFont

        canvas = Image.new("RGB", (900, 90), (255, 255, 255))
        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font = ImageFont.load_default()
        ImageDraw.Draw(canvas).text((20, 26), "ERROR 4032", font=font, fill=(20, 20, 20))
        ocr = recognize_text(canvas)
        print(f"ocr_read = {ocr.backend!r} -> {ocr.text.strip()!r}")
        if "4032" not in ocr.text:
            print("FAIL OCR 未能读出测试文字 ERROR 4032")
            return 1
    except Exception as exc:
        print(f"FAIL OCR 自检异常: {type(exc).__name__}: {exc}")
        return 1

    # The settings page must exist and be usable in the frozen build. Importing
    # the module is not enough: SettingsDialog is only referenced when the button
    # is pressed, so a packaging mistake (or a broken widget call) would not show
    # up until a user clicked it. Build the window for real.
    try:
        from mirecovery.tkapp import MiRecoveryTkApp, SettingsDialog

        settings_app = MiRecoveryTkApp()
        settings_app.root.withdraw()

        # The page must be scrollable: on a short screen the results were
        # previously cut off with no way to reach them. Verify the content really
        # lives in a canvas and that the canvas has a scrollable region.
        scroll_ok = False
        try:
            scroll_app = settings_app
            scroll_app.root.deiconify()
            scroll_app.root.geometry("900x400")
            for _ in range(6):
                scroll_app.root.update()
                scroll_app.root.update_idletasks()
            region = scroll_app.canvas.cget("scrollregion").split()
            canvas_h = scroll_app.canvas.winfo_height()
            page_h = scroll_app.page.winfo_reqheight()
            # Content taller than the viewport, and a real scroll region for it.
            scroll_ok = (
                len(region) == 4
                and page_h > canvas_h
                and scroll_app.page_scroll.winfo_ismapped()
            )
            print(
                f"page_scroll = canvas={canvas_h} content={page_h} "
                f"region={region} bar={bool(scroll_app.page_scroll.winfo_ismapped())}"
            )
        except Exception as exc:
            print(f"FAIL 页面滚动不可用: {type(exc).__name__}: {exc}")
            return 1
        if not scroll_ok:
            print("FAIL 内容没有放进可滚动区域（窗口变矮时会被裁掉）")
            return 1

        dialog = SettingsDialog(settings_app)
        dialog.window.update_idletasks()
        title = dialog.window.title()
        has_url = bool(hasattr(dialog, "url_var"))

        # Drive the validation path with empty fields so the result does not
        # depend on whether the machine happens to have a working config: a valid
        # one would save and close, leaving nothing to assert. This also means the
        # check never rewrites the user's real settings file.
        dialog.enabled_var.set(True)
        dialog._on_toggle()
        dialog.url_var.set("")
        dialog.key_var.set("")
        dialog.model_var.set("")
        dialog.on_save()
        validation = dialog.status_var.get()
        still_open = bool(dialog.window.winfo_exists())
        dialog.window.destroy()
        settings_app.root.destroy()
        print(
            f"settings = {title!r} url_field={has_url} "
            f"validation={validation[:26]!r} blocked_save={still_open}"
        )
        if not has_url or "缺少" not in validation or not still_open:
            print("FAIL 设置页未按预期工作")
            return 1
    except Exception as exc:
        print(f"FAIL 设置页不可用: {type(exc).__name__}: {exc}")
        return 1

    # Online lookup must be bundled AND must default to off.
    #
    # This checks the *default* rather than whatever is in the user's config file:
    # a user who has deliberately enabled online lookup would otherwise make the
    # build fail. The property that matters is "a fresh install cannot send
    # anything anywhere".
    try:
        from mirecovery.online import AiConfig, redact

        fresh = AiConfig()
        print(f"online_default = enabled:{fresh.enabled} usable:{fresh.usable}")
        if fresh.enabled or fresh.usable:
            print("FAIL 联网查询的默认值应当是关闭且不可用")
            return 1
        loaded = AiConfig.load()
        print(f"online_configured = enabled:{loaded.enabled} usable:{loaded.usable}")
        masked = redact("Serial number: HO70390000000355")
        if "HO70390000000355" in masked:
            print("FAIL 脱敏未生效")
            return 1
        print(f"redact = {masked!r}")
    except Exception as exc:
        print(f"FAIL 联网模块自检异常: {type(exc).__name__}: {exc}")
        return 1

    # The screen-recognition reference library must survive packaging too.
    try:
        from mirecovery.recognize import load_default_recognizer

        recognizer, error = load_default_recognizer()
    except Exception as exc:
        print(f"FAIL recognizer import: {type(exc).__name__}: {exc}")
        return 1

    if recognizer is None:
        # Fatal in the frozen build: the reference library must ship with the
        # app, otherwise the image feature silently disappears after packaging.
        first_line = error.splitlines()[0] if error else ""
        print(f"FAIL image_refs unavailable ({first_line})")
        print(f"  meipass = {getattr(sys, '_MEIPASS', '-')}")
        from pathlib import Path

        import mirecovery.recognize as rec

        print(f"  bundled = {rec.BUNDLED_LIBRARY} exists={rec.BUNDLED_LIBRARY.is_file()}")
        if getattr(sys, "_MEIPASS", None):
            candidate = Path(sys._MEIPASS) / "mirecovery" / "data" / "image_refs.json"
            print(f"  meipass candidate = {candidate} exists={candidate.is_file()}")
        return 1
    else:
        counts = recognizer.reference_counts()
        total = sum(counts.values())
        print(f"image_refs = {len(counts)} classes / {total} images")
        if total < 8:
            print(f"FAIL expected at least 8 reference images, got {total}")
            return 1

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
