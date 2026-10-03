#!/usr/bin/env python3
"""Build every Windows deliverable and verify each one actually starts.

Produces, in ``dist/``:

  * ``MiRecoveryHelper.exe``              tkinter build, single file, no .NET needed
  * ``MiRecoveryHelper/``                 tkinter build, folder (nothing unpacked at startup)
  * ``MiRecoveryHelper-portable.zip``     the folder, zipped for handing over
  * ``MiRecoveryHelper-toga.exe``         Toga build (only useful on x64 Windows)

Why two GUI builds: Toga's Windows backend needs ``pythonnet``, which has no
ARM64 runtime, so on Windows on ARM it can never start. The tkinter build is
therefore the primary deliverable anywhere; the Toga build is kept for x64
machines and for parity with the Android (Briefcase) build. See README 4.6.

Every build ends with a frozen self test so a missing data file is caught here
rather than by the user.

Usage
-----
    python tools/build_exe.py              # everything + self test
    python tools/build_exe.py --tk-only    # just the tkinter deliverables
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST = PROJECT_ROOT / "dist"
BUILD = PROJECT_ROOT / "build"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

# theme.py is stdlib-only, so importing it is safe here.
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from mirecovery import theme  # noqa: E402

TK_ONEFILE_SPEC = "MiRecoveryHelper-tk.spec"
TK_ONEDIR_SPEC = "MiRecoveryHelper-tk.onedir.spec"
TOGA_ONEFILE_SPEC = "MiRecoveryHelper.spec"
SELFTEST_SPEC = "MiRecoveryHelper.selftest.spec"

# The window title keeps the full display name (slash-wrapped). The executable
# is named without the slashes: Windows filenames cannot contain "/".
EXE_NAME = theme.EXE_BASENAME
TOGA_EXE_NAME = f"{theme.EXE_BASENAME}-toga"


def python_executable() -> str:
    if VENV_PYTHON.is_file():
        return str(VENV_PYTHON)
    return sys.executable


def run_pyinstaller(spec: str, workpath: str, extra: list[str] | None = None) -> int:
    command = [
        python_executable(), "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--distpath", str(DIST),
        "--workpath", str(BUILD / workpath),
        *(extra or []),
        str(PROJECT_ROOT / spec),
    ]
    print(f"[build] {spec}")
    return subprocess.run(command, cwd=PROJECT_ROOT).returncode


def prepare_data() -> None:
    """Regenerate kb.json and image_refs.json so the build is never stale."""
    for script in ("build_kb.py", "build_references.py"):
        result = subprocess.run(
            [python_executable(), str(PROJECT_ROOT / "tools" / script)],
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            raise SystemExit(f"{script} 失败，构建中止")


def verify_frozen() -> bool:
    print("[verify] 冻结自检")
    if run_pyinstaller(SELFTEST_SPEC, "selftest") != 0:
        return False
    self_test = DIST / "MiRecoveryHelperSelfTest.exe"
    if not self_test.is_file():
        print("[verify] 找不到自检程序")
        return False
    result = subprocess.run(
        [str(self_test)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(output.strip())
    return result.returncode == 0 and "SELFTEST OK" in output


def zip_folder(folder: Path, archive: Path) -> Path | None:
    if not folder.is_dir():
        return None
    if archive.is_file():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as handle:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(DIST))
    return archive


def human(size: int) -> str:
    return f"{size / 1024 / 1024:.1f} MB"


def folder_size(folder: Path) -> int:
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tk-only", action="store_true",
                        help="只构建 tkinter 版（跳过 Toga 版）")
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args(argv)

    prepare_data()
    results: list[str] = []

    # ---- 1. Toga build FIRST, then renamed -------------------------------
    # Both specs emit the same exe name, so the Toga build must be moved out of
    # the way *before* the tkinter build runs - otherwise it silently
    # overwrites the primary deliverable.
    toga_target = DIST / f"{TOGA_EXE_NAME}.exe"
    if not args.tk_only:
        if run_pyinstaller(TOGA_ONEFILE_SPEC, "toga-onefile") == 0:
            toga = DIST / "MiRecoveryHelper.exe"
            if toga.is_file():
                if toga_target.is_file():
                    toga_target.unlink()
                shutil.move(str(toga), str(toga_target))
                results.append(
                    f"Toga 版      : {toga_target.name}  "
                    f"{human(toga_target.stat().st_size)}（仅 x64 可用，见 README 4.6）"
                )
        else:
            print("[build] Toga 版构建失败（不影响 tkinter 版）")

    # ---- 2. tkinter single file (PRIMARY) --------------------------------
    if run_pyinstaller(TK_ONEFILE_SPEC, "tk-onefile") != 0:
        return 1
    built = DIST / "MiRecoveryHelper.exe"
    if not built.is_file():
        print("[build] tkinter 单文件 exe 未生成")
        return 1
    tk_exe = DIST / f"{EXE_NAME}.exe"
    if tk_exe.is_file():
        tk_exe.unlink()
    shutil.move(str(built), str(tk_exe))
    results.append(
        f"单文件 exe   : {tk_exe.name}  "
        f"{human(tk_exe.stat().st_size)}（tkinter，主交付物）"
    )

    # ---- 3. tkinter folder (safest) --------------------------------------
    if run_pyinstaller(TK_ONEDIR_SPEC, "tk-onedir") != 0:
        return 1
    raw_folder = DIST / "MiRecoveryHelper"
    if not raw_folder.is_dir():
        print("[build] tkinter 目录版未生成")
        return 1
    # The spec name drives the folder name; rename it to match the app.
    folder = DIST / f"{EXE_NAME}"
    if folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
    os.replace(raw_folder, folder)
    inner = folder / "MiRecoveryHelper.exe"
    if not inner.is_file():
        print("[build] tkinter 目录版缺少主程序")
        return 1
    results.append(
        f"目录版       : {folder.name}/  {human(folder_size(folder))}（{inner.name}）"
    )

    archive = zip_folder(folder, DIST / f"{EXE_NAME}-portable.zip")
    if archive:
        results.append(f"便携压缩包   : {archive.name}  {human(archive.stat().st_size)}")

    # ---- 4. verification -------------------------------------------------
    if not args.skip_verify:
        if not verify_frozen():
            print("\n[build] 冻结自检失败：打包结果不可用")
            return 1
        results.append("冻结自检     : 通过（知识库 + 图片参考库 + tkinter 均可用）")

    # ---- 5. assert the primary deliverables survived ---------------------
    # Guard against a future reordering silently clobbering what we hand over.
    if not tk_exe.is_file():
        print(f"\n[build] 严重错误：主交付物 {tk_exe.name} 在构建结束时不存在")
        return 1
    if not (folder / "MiRecoveryHelper.exe").is_file():
        print("\n[build] 严重错误：目录版在构建结束时不存在")
        return 1

    print("\n构建完成：")
    for line in results:
        print(f"  {line}")
    print("\n提示：dist/使用说明.txt 里有给最终用户的版本选择与报错排查说明。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
