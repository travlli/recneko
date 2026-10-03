#!/usr/bin/env python3
"""Build the image reference library (image_refs.json) for screen recognition.

Reference images live under ``kb/image_refs/``:

    kb/image_refs/
      synthetic/<label>/...   generated stand-ins (tools/make_reference_images.py)
      user/<label>/...        REAL photos you add by hand  <-- these matter most

Every ``<label>`` directory becomes a class. Labels are mapped to knowledge-base
pages and titles below.

Adding real photos
------------------
1. Make a folder ``kb/image_refs/user/<label>/`` (any label from the table below,
   or a new one you add to LABELS).
2. Drop in photos/screenshots of that screen. 2-5 per class is plenty; they may
   be phone photos at any resolution or rotation.
3. Re-run this script and re-run tools/benchmark_recognition.py.

Real photos are the only way this feature becomes trustworthy on real devices:
the synthetic set proves the pipeline works, not that it recognises your phone.

Usage
-----
    python tools/build_references.py
    python tools/build_references.py --check     # 只报告不写文件
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mirecovery.imagefeatures import (  # noqa: E402
    FEATURE_VERSION,
    Reference,
    ReferenceLibrary,
    extract_path,
)

REF_ROOT = PROJECT_ROOT / "kb" / "image_refs"
OUTPUT = PROJECT_ROOT / "src" / "mirecovery" / "data" / "image_refs.json"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}

# label -> (human title, knowledge-base page slug)
LABELS: dict[str, tuple[str, str]] = {
    "recovery-menu": (
        "Recovery 主菜单（原厂 recovery 列表界面）",
        "recovery-cant-load-android-system",
    ),
    "recovery-data-corrupt": (
        "Can't load Android system（数据损坏提示）",
        "recovery-cant-load-android-system",
    ),
    "recovery-mount-failed": (
        "Recovery 挂载失败（failed to mount /data）",
        "recovery-cant-load-android-system",
    ),
    "fastboot-mode": (
        "Fastboot / Bootloader 界面",
        "fastboot-devices-not-detected",
    ),
    "edl-9008-mode": (
        "EDL / 9008 下载模式（黑屏）",
        "qualcomm-edl-9008-enter",
    ),
    "spflash-error-dialog": (
        "SP Flash Tool 报错弹窗（BROM ERROR）",
        "mtk-spflash-error-4032-4004-4008",
    ),
    "miflash-error": (
        "MiFlash 刷机报错窗口",
        "miflash-flash-script-errors",
    ),
    "sideload-error": (
        "adb sideload 失败（PC 终端红字）",
        "recovery-adb-sideload-errors",
    ),
    "avb-corrupt-warning": (
        "AVB / dm-verity 完整性警告",
        "avb-verified-boot-corruption",
    ),
    "fastboot-locked": (
        "fastboot 报错（锁定/不允许刷写）",
        "fastboot-flash-errors",
    ),
    "fastboot-unlock-failed": (
        "解锁失败 / Token verify failed",
        "fastboot-unlock-token-verify-failed",
    ),
}


def collect(source: str) -> tuple[list[Reference], list[str]]:
    """Collect references from ``kb/image_refs/<source>/<label>/*``."""
    references: list[Reference] = []
    warnings: list[str] = []
    base = REF_ROOT / source
    if not base.is_dir():
        return references, warnings

    for label_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        label = label_dir.name
        if label not in LABELS:
            warnings.append(
                f"跳过未知类别目录 {label_dir}（{label} 不在 LABELS 表中）"
            )
            continue
        title, kb_slug = LABELS[label]
        images = sorted(
            p for p in label_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        )
        if not images:
            warnings.append(f"类别 {label} 没有图片")
            continue
        for image_path in images:
            try:
                features = extract_path(image_path)
            except Exception as exc:
                warnings.append(f"提取特征失败 {image_path.name}: {exc}")
                continue
            references.append(
                Reference(
                    label=label,
                    title=title,
                    kb_slug=kb_slug,
                    source=source,
                    path=str(image_path.relative_to(PROJECT_ROOT)),
                    features=features,
                )
            )
    return references, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="只报告，不写文件")
    args = parser.parse_args(argv)

    synthetic, warnings = collect("synthetic")
    user, user_warnings = collect("user")
    warnings += user_warnings

    references = synthetic + user

    if not references:
        print("没有找到任何参考图。请先运行：python tools/make_reference_images.py",
              file=sys.stderr)
        for warning in warnings:
            print(f"  ! {warning}", file=sys.stderr)
        return 1

    library = ReferenceLibrary(version=FEATURE_VERSION, references=references)

    counts: dict[str, int] = {}
    sources: dict[str, int] = {}
    for reference in references:
        counts[reference.label] = counts.get(reference.label, 0) + 1
        sources[reference.source] = sources.get(reference.source, 0) + 1

    print(f"参考图合计 {len(references)} 张")
    print(f"  来源：{', '.join(f'{k}={v}' for k, v in sorted(sources.items()))}")

    for label in sorted(counts):
        marker = "  " if "user" in sources else "  "
        title = LABELS.get(label, ("?", "?"))[0]
        print(f"  {marker}{label:<26} {counts[label]:>2} 张   {title}")

    missing = [label for label in LABELS if label not in counts]
    if missing:
        print(f"尚无参考图的类别（{len(missing)}）：{', '.join(missing)}")

    if not user:
        print()
        print("注意：当前没有任何 __真实__ 参考照片（kb/image_refs/user/ 为空）。")
        print("      识别能力目前只验证过合成图，真机准确率未知。")
        print("      建议每个类别放 2~5 张真机截图/拍照后再重新构建。")

    for warning in warnings:
        print(f"  ! {warning}", file=sys.stderr)

    if args.check:
        print("\n(--check：未写文件)")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    library.save(OUTPUT)
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\n已写出 {OUTPUT}（{size_kb:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
