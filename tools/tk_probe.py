"""Probe: can tkinter actually run inside a frozen PyInstaller build?

Tkinter is the fallback GUI option for machines where Toga's WinForms backend
cannot work (e.g. Windows on ARM, where pythonnet ships no ARM64 runtime).
This script is bundled into a throwaway console exe to confirm that Tk, its
Tcl/Tk data files and the whole stack survive packaging.

It creates a real window, renders text into it, then closes it - so a PASS means
the GUI stack genuinely works, not merely that the module imported.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(f"frozen = {getattr(sys, 'frozen', False)}")
    print(f"meipass = {getattr(sys, '_MEIPASS', '-')}")

    try:
        import tkinter
        from tkinter import ttk
    except Exception as exc:
        print(f"FAIL tkinter import: {type(exc).__name__}: {exc}")
        return 1

    print(f"tkinter = {tkinter.TkVersion}")

    try:
        root = tkinter.Tk()
    except Exception as exc:
        print(f"FAIL Tk(): {type(exc).__name__}: {exc}")
        return 1

    try:
        root.title("probe")
        root.geometry("420x220")
        frame = ttk.Frame(root, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="小米/红米 Recovery 排错助手").pack(anchor="w")
        text = tkinter.Text(frame, height=4, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", "ERROR 4032\nSahara Fail")
        ttk.Button(frame, text="按钮").pack(anchor="w")

        # Force real widget realisation, then render one frame.
        root.update_idletasks()
        root.update()

        # Confirm Tk can measure the font we rely on for Chinese labels.
        import tkinter.font as tkfont

        measured = tkfont.Font(font=("Microsoft YaHei UI", 10)).measure("测试")
        print(f"font measure = {measured}")
        print(f"root size = {root.winfo_width()}x{root.winfo_height()}")
        if measured <= 0:
            print("FAIL font measurement returned 0")
            return 1
    except Exception as exc:
        print(f"FAIL widget construction: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    print("TKINTER OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
