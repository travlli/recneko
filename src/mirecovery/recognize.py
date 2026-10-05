"""Screen recognition: match a user's photo against reference screens.

Design notes
------------
* Recognition is **nearest-neighbour over per-class maxima**: several reference
  images can describe the same screen (different ROM versions, layouts), so all
  references of a class are compared and the best one represents that class.
* A match is only reported when it is both **strong enough** (absolute
  similarity) and **clearly ahead** of the runner-up (relative margin).
  Otherwise the honest answer is "not sure" — a wrong repair route is worse than
  asking the user to paste the text.
* Every reference carries a `source` field (`synthetic` / `user`). Synthetic
  references are generated drawings used to validate the pipeline; they are
  kept distinguishable so nobody mistakes benchmark results for real-world
  accuracy.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .imagefeatures import (
    FEATURE_VERSION,
    Features,
    Reference,
    ReferenceLibrary,
    cheap_score,
    explain,
    extract,
    similarity,
)

# Similarity thresholds. Re-derived from the synthetic distortion benchmark
# (tools/benchmark_recognition.py --sweep) after the rgb_hist normalisation fix,
# which changed the score scale:
#
#     min_score  min_margin   accepted   accepted-and-correct
#       0.60        0.00        58.3%          96.4%  (1 wrong)
#       0.65        0.00        56.2%         100.0%  (0 wrong)
#       0.70        0.02        54.2%         100.0%  (0 wrong)  <-- chosen
#       0.75        0.02        54.2%         100.0%  (0 wrong)
#       0.85        0.00        37.5%         100.0%  (0 wrong)
#
# 0.70 matches 0.65 on coverage but demands a higher absolute similarity, which
# is the safer bias given the benchmark is synthetic. Precision is deliberately
# favoured over coverage: telling a user to reflash the wrong thing is worse
# than declining to answer.
#
# NOTE: measured on synthetic images against synthetic references. Real-camera
# accuracy is unknown until real photos are added to kb/image_refs/user/ and the
# benchmark is re-run.
DEFAULT_MIN_SCORE = 0.70
DEFAULT_MIN_MARGIN = 0.02

# Below this structure score the image is essentially flat (lens cap, black
# frame, plain blank screen) and there is nothing meaningful to match. ZNCC
# cannot tell such frames apart, so they are declined outright instead of being
# force-matched to whichever reference happens to be darkest.
MIN_STRUCTURE = 0.06

# Two-stage matching budget: how many labels survive the cheap prefilter, and
# how many of each surviving label's references get exact ZNCC. 4 x 2 = at most
# 8 exact comparisons instead of one per reference.
RERANK_LABELS = 4
RERANK_PER_LABEL = 2


@dataclass
class Candidate:
    """One reference screen considered for a match."""

    label: str
    title: str
    kb_slug: str
    source: str
    path: str
    score: float


@dataclass
class RecognitionResult:
    """Outcome of recognising one image."""

    matched: bool
    confidence: float = 0.0
    label: str = ""
    title: str = ""
    kb_slug: str = ""
    source: str = ""
    path: str = ""
    reason: str = ""
    candidates: list[Candidate] = field(default_factory=list)
    explanations: list[tuple[str, float]] = field(default_factory=list)
    error: str = ""

    @property
    def is_certain(self) -> bool:
        return self.matched and self.confidence >= 0.75

    def top_n(self, count: int = 3) -> list[Candidate]:
        return self.candidates[:count]


class RecognizerError(RuntimeError):
    """Raised when recognition cannot run at all (no library, bad image)."""


class ScreenRecognizer:
    """Recognise phone screens from images using a reference library."""

    def __init__(
        self,
        library: ReferenceLibrary,
        min_score: float = DEFAULT_MIN_SCORE,
        min_margin: float = DEFAULT_MIN_MARGIN,
    ) -> None:
        self.library = library
        self.min_score = min_score
        self.min_margin = min_margin

    # -- construction ------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path, **kwargs) -> "ScreenRecognizer":
        path = Path(path)
        if not path.is_file():
            raise RecognizerError(f"参考图特征库不存在：{path}")
        return cls(ReferenceLibrary.load(path), **kwargs)

    @property
    def has_references(self) -> bool:
        return bool(self.library.references)

    def reference_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for reference in self.library.references:
            counts[reference.label] = counts.get(reference.label, 0) + 1
        return counts

    # -- recognition -------------------------------------------------------

    def recognize_features(self, features: Features) -> RecognitionResult:
        """Match pre-computed features (used by benchmarks)."""
        if not self.library.references:
            return RecognitionResult(
                matched=False,
                reason="参考图库为空，无法识别。",
                error="empty library",
            )

        # Reject flat images before matching: a black frame has no structure to
        # correlate, and its degenerate hashes would otherwise "match" any dark
        # reference.
        if features.structure < MIN_STRUCTURE:
            return RecognitionResult(
                matched=False,
                confidence=0.0,
                reason=(
                    "图片几乎没有任何可见内容（纯色/全黑/过曝），无法判断是什么画面。\n"
                    "建议：重新拍一张能看清屏幕内容的照片，或直接把报错文字粘贴到日志框。"
                ),
                error="low structure",
            )

        # Two-stage matching.
        #
        # Stage 1 scores every reference with `cheap_score` (hashes +
        # histograms, no per-pixel work) and keeps the best few *labels*.
        # Stage 2 pays for exact ZNCC only on those labels' references.
        #
        # Without this the pure-Python ZNCC path costs ~140 ms per image
        # against 24 references; with it the work drops roughly 3x, which is
        # what lets the shipped exe omit numpy (~15 MB) and stay responsive.
        # Note the shortlist must be limited by LABEL: an earlier version kept
        # the top 3 references of every label, which selected all 24 and saved
        # nothing at all.
        by_label: dict[str, list[tuple[float, Reference]]] = {}
        for reference in self.library.references:
            by_label.setdefault(reference.label, []).append(
                (cheap_score(features, reference.features), reference)
            )

        label_rank = sorted(
            by_label.items(), key=lambda kv: -max(score for score, _ in kv[1])
        )

        shortlist: list[Reference] = []
        for _, bucket in label_rank[:RERANK_LABELS]:
            bucket.sort(key=lambda item: -item[0])
            shortlist.extend(reference for _, reference in bucket[:RERANK_PER_LABEL])

        # Best reference per label, after re-scoring the shortlist precisely.
        best_per_label: dict[str, tuple[float, Reference]] = {}
        for reference in shortlist:
            score = similarity(features, reference.features)
            current = best_per_label.get(reference.label)
            if current is None or score > current[0]:
                best_per_label[reference.label] = (score, reference)

        ranked = sorted(best_per_label.values(), key=lambda item: -item[0])

        candidates = [
            Candidate(
                label=reference.label,
                title=reference.title,
                kb_slug=reference.kb_slug,
                source=reference.source,
                path=reference.path,
                score=round(score, 4),
            )
            for score, reference in ranked
        ]

        top_score, top_reference = ranked[0]
        # A margin only means something when there is a rival to compare with.
        # With a single candidate (e.g. a library holding one class) the
        # difference would read as "infinitely better", so treat it as unknown
        # and let the confidence collapse toward the absolute score instead.
        has_rival = len(ranked) > 1
        runner_up = ranked[1][0] if has_rival else 0.0
        margin = (top_score - runner_up) if has_rival else 0.0

        # Confidence blends absolute similarity with how far ahead the winner is.
        confidence = top_score * (1.0 - 0.5 * math.exp(-margin / 0.05))

        base = RecognitionResult(
            matched=False,
            confidence=round(confidence, 4),
            label=top_reference.label,
            title=top_reference.title,
            kb_slug=top_reference.kb_slug,
            source=top_reference.source,
            path=top_reference.path,
            candidates=candidates,
            explanations=explain(features, top_reference.features),
        )

        if top_score < self.min_score:
            base.reason = (
                f"最接近的是「{top_reference.title}」，但相似度只有 {top_score:.0%}，"
                f"低于判定阈值 {self.min_score:.0%}，不足以给出结论。\n"
                "建议：把图里的报错文字直接粘贴到日志框，文字检索比图片可靠得多。"
            )
            return base

        if margin < self.min_margin:
            if has_rival:
                base.reason = (
                    f"「{top_reference.title}」和 "
                    f"「{ranked[1][1].title}」差别太小（{top_score:.0%} vs "
                    f"{runner_up:.0%}），无法确定是哪一种。\n"
                    "建议：补充图里的文字，或换一张更清晰的截图。"
                )
            else:
                # Only one class was available to compare against, so there is
                # no evidence that this is the *right* one rather than the only
                # one. Decline rather than guess.
                base.reason = (
                    f"只匹配到「{top_reference.title}」一个候选（相似度 "
                    f"{top_score:.0%}），没有其它类别可对照，无法确认。\n"
                    "建议：补充参考图库，或把图里的报错文字粘贴到日志框。"
                )
            return base

        base.matched = True
        base.reason = (
            f"匹配到「{top_reference.title}」，相似度 {top_score:.0%}"
            f"（领先第二名 {margin:.0%}）"
        )
        return base

    def recognize_image(self, image: Image.Image) -> RecognitionResult:
        """Recognise a PIL image."""
        try:
            features = extract(image)
        except Exception as exc:  # pragma: no cover - defensive
            return RecognitionResult(
                matched=False, reason=f"图片解析失败：{exc}", error=str(exc)
            )
        return self.recognize_features(features)

    def recognize_path(self, path: str | Path) -> RecognitionResult:
        """Recognise an image file."""
        path = Path(path)
        if not path.is_file():
            return RecognitionResult(
                matched=False,
                reason=f"找不到图片文件：{path}",
                error="missing file",
            )
        try:
            with Image.open(path) as handle:
                handle.load()
                return self.recognize_image(handle)
        except Exception as exc:
            return RecognitionResult(
                matched=False,
                reason=f"无法读取图片（格式不支持或文件损坏）：{exc}",
                error=str(exc),
            )


# --------------------------------------------------------------------------
# Loading helper used by the GUI
# --------------------------------------------------------------------------

# Shipped with the app; regenerated by tools/build_references.py.
BUNDLED_LIBRARY = Path(__file__).resolve().parent / "data" / "image_refs.json"


def load_default_recognizer(
    extra_paths: list[Path] | None = None,
) -> tuple[ScreenRecognizer | None, str]:
    """Load the bundled reference library plus any user-supplied ones.

    Returns ``(recognizer, error_message)``. ``recognizer`` is ``None`` when no
    library could be loaded at all.
    """
    candidates: list[Path] = []
    for extra in extra_paths or []:
        candidates.append(Path(extra))
    candidates.append(BUNDLED_LIBRARY)
    # Frozen (PyInstaller) builds unpack data into sys._MEIPASS, which is not
    # necessarily the directory this module lives in - the same trap kb.json
    # has to avoid.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "mirecovery" / "data" / "image_refs.json")
        candidates.append(Path(meipass) / "data" / "image_refs.json")
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "image_refs.json")

    merged: list[Reference] = []
    seen_labels: set[tuple[str, str]] = set()
    loaded_from: list[str] = []
    problems: list[str] = []

    seen_paths: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)
        if not path.is_file():
            continue
        try:
            library = ReferenceLibrary.load(path)
        except Exception as exc:
            problems.append(f"{path.name}: 无法解析（{type(exc).__name__}）")
            continue

        # Refuse a library whose feature layout does not match this code.
        # Loading one silently is worse than failing: missing thumbnails make
        # ZNCC return a constant 0.5, so 68% of the weighting degenerates and
        # the recogniser still answers - confidently, and for the wrong reasons.
        if library.version != FEATURE_VERSION:
            problems.append(
                f"{path.name}: 特征版本不匹配（库={library.version}，"
                f"程序={FEATURE_VERSION}），已跳过。请重新运行 "
                f"tools/build_references.py"
            )
            continue

        loaded_from.append(str(path))
        for reference in library.references:
            # User references win over synthetic ones for the same label+path.
            label_key = (reference.label, reference.path)
            if label_key in seen_labels:
                continue
            seen_labels.add(label_key)
            merged.append(reference)

    if not merged:
        detail = ("\n" + "\n".join(f"  · {p}" for p in problems)) if problems else ""
        return None, (
            "未找到可用的参考图特征库（image_refs.json）。\n"
            "请运行：python tools/build_references.py" + detail
        )

    recognizer = ScreenRecognizer(ReferenceLibrary(references=merged))
    return recognizer, ("\n".join(problems) if problems else "")
