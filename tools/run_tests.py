#!/usr/bin/env python3
"""Run the test suite, splitting the GUI tests into their own process.

Why this exists
---------------
Running the whole suite in one process crashes with an access violation
(``0xC0000005``) **after every test has passed**, during interpreter shutdown.
It is reproducible:

    pytest tests/test_gui.py tests/test_ocr.py tests/test_recognize.py \\
           tests/test_report_and_entrypoints.py     -> exit -1073741819
    pytest tests/test_gui.py tests/test_ocr.py tests/test_kb.py          -> exit 0
    pytest <everything except test_gui.py>                               -> exit 0

So it needs the tkinter tests *and* the OCR tests *and* more of the image path in
one process. The likely cause is that Tk initialises COM as a single-threaded
apartment while Windows OCR (WinRT) needs its own apartment model, and tearing
both down together is what fails.

This is a **test-harness** problem, not an application one: the frozen self test
does Tk *and* OCR in one process and exits 0, and the GUI app runs normally.

Running the GUI tests in a separate process makes the suite reliable, and keeps
the failure honest rather than hidden behind a tolerant exit code.

    python tools/run_tests.py            # everything
    python tools/run_tests.py -k ocr     # pass extra args to pytest
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

GUI_TESTS = "tests/test_gui.py"


def python_executable() -> str:
    return str(VENV_PYTHON) if VENV_PYTHON.is_file() else sys.executable


def run(label: str, args: list[str]) -> int:
    command = [python_executable(), "-m", "pytest", *args]
    print(f"\n=== {label} ===")
    print(" ".join(command[2:]))
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    print(f"--- {label}: exit {result.returncode} ---")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("extra", nargs="*", help="额外的 pytest 参数")
    args = parser.parse_args(argv)
    extra = list(args.extra)

    # Group 1: everything except the GUI tests (library, OCR, packaging).
    code_a = run(
        "库 / OCR / 打包契约测试",
        [f"--ignore={GUI_TESTS}", "-q", *extra],
    )

    # Group 2: the tkinter tests on their own.
    code_b = run("tkinter 界面测试（独立进程）", [GUI_TESTS, "-q", *extra])

    print()
    if code_a == 0 and code_b == 0:
        print("全部测试通过。")
        return 0
    print(f"测试失败：第一组 exit={code_a}，第二组 exit={code_b}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
