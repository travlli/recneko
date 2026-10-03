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

    # Prove the GUI stack itself is packaged correctly. Importing the app
    # module pulls in toga, toga.constants, toga.style and the whole
    # mirecovery package - the imports that the "relative import with no known
    # parent package" bug used to break. Instantiation is deliberately NOT
    # attempted: that needs a live .NET/CLR runtime, which a build machine may
    # legitimately lack.
    try:
        import mirecovery.app  # noqa: F401
    except Exception as exc:
        print(f"FAIL gui import: {type(exc).__name__}: {exc}")
        return 1
    print("gui_stack = ok")

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

    # And the primary GUI module must import.
    try:
        import mirecovery.tkapp  # noqa: F401
    except Exception as exc:
        print(f"FAIL tkapp import: {type(exc).__name__}: {exc}")
        return 1
    print("tk_gui = ok")

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
