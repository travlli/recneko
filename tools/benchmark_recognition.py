#!/usr/bin/env python3
"""Benchmark the screen recogniser on the synthetic image set.

This measures robustness to photo-like distortion (scale, perspective, rotation,
lighting, blur, noise, JPEG) and reports:

  * top-1 accuracy      - the correct class had the highest similarity
  * accepted accuracy   - of the images the recogniser *accepted*, how many were right
  * abstain rate        - how often it correctly declined to answer
  * a confusion matrix  - where mistakes happen

Run after tools/make_reference_images.py:

    python tools/make_reference_images.py
    python tools/benchmark_recognition.py
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mirecovery.imagefeatures import Reference, ReferenceLibrary, extract_path  # noqa: E402
from mirecovery.recognize import ScreenRecognizer  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from make_reference_images import SCREENS  # noqa: E402

REFERENCE_DIR = PROJECT_ROOT / "kb" / "image_refs" / "synthetic"
BENCHMARK_DIR = PROJECT_ROOT / "kb" / "image_refs" / "benchmark"


def build_library() -> ReferenceLibrary:
    references: list[Reference] = []
    for spec in SCREENS:
        label = spec["label"]
        directory = REFERENCE_DIR / label
        if not directory.is_dir():
            continue
        for image_path in sorted(directory.glob("*")):
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                continue
            references.append(
                Reference(
                    label=label,
                    title=spec["title"],
                    kb_slug=spec["kb_slug"],
                    source="synthetic",
                    path=str(image_path.relative_to(PROJECT_ROOT)),
                    features=extract_path(image_path),
                )
            )
    return ReferenceLibrary(references=references)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--min-margin", type=float, default=None)
    parser.add_argument("--sweep", action="store_true",
                        help="扫描阈值组合，输出推荐值")
    args = parser.parse_args(argv)

    if not REFERENCE_DIR.is_dir() or not BENCHMARK_DIR.is_dir():
        print("缺少图片集，请先运行：python tools/make_reference_images.py", file=sys.stderr)
        return 1

    library = build_library()
    if not library.references:
        print("参考图为空", file=sys.stderr)
        return 1

    print(f"参考图：{len(library.references)} 张，类别 {len(library.labels())} 个")

    # Pre-extract benchmark features once (extraction is the slow part).
    samples: list[tuple[str, str, object]] = []
    for label_dir in sorted(BENCHMARK_DIR.iterdir()):
        if not label_dir.is_dir():
            continue
        for image_path in sorted(label_dir.glob("*")):
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                continue
            samples.append((label_dir.name, image_path.name, extract_path(image_path)))
    print(f"基准图：{len(samples)} 张（含缩放/透视/旋转/光照/模糊/噪点/JPEG 干扰）\n")

    if args.sweep:
        return sweep(library, samples)

    kwargs = {}
    if args.min_score is not None:
        kwargs["min_score"] = args.min_score
    if args.min_margin is not None:
        kwargs["min_margin"] = args.min_margin
    recognizer = ScreenRecognizer(library, **kwargs)
    return evaluate(recognizer, samples)


def evaluate(recognizer: ScreenRecognizer, samples) -> int:
    correct_top1 = 0
    accepted = 0
    accepted_correct = 0
    accepted_wrong = 0
    abstained = 0
    abstained_wrong = 0     # abstained even though top-1 was right (missed opportunity)
    confusion: dict[str, Counter] = defaultdict(Counter)
    wrong_accepted: list[tuple[str, str, object]] = []

    for expected, filename, features in samples:
        result = recognizer.recognize_features(features)
        top1 = result.candidates[0].label if result.candidates else "<none>"
        if top1 == expected:
            correct_top1 += 1
        confusion[expected][top1] += 1

        if result.matched:
            accepted += 1
            if result.label == expected:
                accepted_correct += 1
            else:
                accepted_wrong += 1
                wrong_accepted.append((expected, filename, result))
        else:
            abstained += 1
            if top1 == expected:
                abstained_wrong += 1

    total = len(samples)
    print(f"top-1 准确率      : {correct_top1}/{total} = {correct_top1 / total:.1%}")
    print(f"接受(有结论)      : {accepted}/{total} = {accepted / total:.1%}")
    if accepted:
        print(f"接受中正确        : {accepted_correct}/{accepted} = "
              f"{accepted_correct / accepted:.1%}   <-- 关键指标")
        print(f"接受但错误        : {accepted_wrong}（这些会误导用户，越少越好）")
    print(f"拒绝(不下结论)    : {abstained}/{total} = {abstained / total:.1%}")
    print(f"  其中本可答对    : {abstained_wrong}")

    print("\n混淆矩阵（行=真实，列=top1 判定）:")
    labels = sorted(confusion)
    header = "  " + " " * 26 + "".join(f"{label[:8]:>10}" for label in labels)
    print(header)
    for expected in labels:
        row = confusion[expected]
        cells = "".join(f"{row.get(label, 0):>10}" for label in labels)
        print(f"  {expected:<26}{cells}")

    if wrong_accepted:
        print("\n被接受但判错的样本:")
        for expected, name, result in wrong_accepted[:10]:
            runner = result.candidates[1] if len(result.candidates) > 1 else None
            extra = f"，第二名 {runner.label} {runner.score:.2f}" if runner else ""
            print(f"  {name}: 期望 {expected} -> 判为 {result.label} "
                  f"({result.confidence:.2f}{extra})")
    return 0


def sweep(library: ReferenceLibrary, samples) -> int:
    """Grid-search thresholds and report the best operating point."""
    print(f"{'min_score':>9} {'min_margin':>10} {'接受率':>8} {'接受准确率':>10} {'错误接受':>8}")
    best = None
    for min_score in [0.60, 0.65, 0.70, 0.75, 0.78, 0.80, 0.82, 0.85, 0.88]:
        for min_margin in [0.0, 0.02, 0.03, 0.05, 0.08]:
            recognizer = ScreenRecognizer(
                library, min_score=min_score, min_margin=min_margin
            )
            accepted = accepted_correct = accepted_wrong = 0
            for expected, _, features in samples:
                result = recognizer.recognize_features(features)
                if result.matched:
                    accepted += 1
                    if result.label == expected:
                        accepted_correct += 1
                    else:
                        accepted_wrong += 1
            rate = accepted / len(samples)
            accuracy = accepted_correct / accepted if accepted else 0.0
            print(f"{min_score:>9.2f} {min_margin:>10.2f} {rate:>7.1%} "
                  f"{accuracy:>9.1%} {accepted_wrong:>8}")
            # Prefer: zero wrong accepts, then highest accepted accuracy, then coverage.
            key = (accepted_wrong, -accuracy, -rate)
            if best is None or key < best[0]:
                best = (key, min_score, min_margin, rate, accuracy, accepted_wrong)

    if best:
        _, min_score, min_margin, rate, accuracy, wrong = best
        print(f"\n推荐：min_score={min_score}, min_margin={min_margin} "
              f"(接受率 {rate:.1%}, 接受准确率 {accuracy:.1%}, 错误接受 {wrong})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
