"""Render an analysis result + KB matches into readable report text.

Kept separate from the GUI so the same rendering can be used for the
clipboard, for console output, and for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .kb import KB, Entry, Match
from .logsetup import get_logger
from .scanner import Finding

logger = get_logger(__name__)

_HEADER = "=" * 58


def render(finding: Finding, matches: list[Match]) -> str:
    """Build the plain-text solution report shown to the user."""
    from .kb import MIN_RELEVANCE

    if not matches:
        return render_no_match(finding)
    return _render_matches(finding, matches)


def render_no_match(finding: Finding) -> str:
    """Say plainly that nothing relevant was found.

    Text search previously had no relevance floor, so an error the knowledge base
    does not cover still produced five unrelated "solutions" under a heading that
    read like a conclusion. Image recognition has always refused in that
    situation; text search now does too.
    """
    from .kb import MIN_RELEVANCE

    lines = [
        _HEADER,
        " 检测结果",
        _HEADER,
        f"平台判定 : {finding.platform_label}",
    ]
    if finding.signals:
        lines.append(f"判定依据 : {'、'.join(finding.signals[:6])}")
    if finding.mode:
        lines.append(f"当前模式 : {finding.mode}")
    if finding.error_codes:
        lines.append(f"错误码   : {'、'.join(finding.error_codes)}")
    lines += [
        "",
        _HEADER,
        " 没有找到足够相关的条目",
        _HEADER,
        "",
        f"知识库里没有匹配度达到 {MIN_RELEVANCE:.0f} 分的条目，所以不给出方案 ——",
        "套用不相关的刷机步骤可能让设备变砖，比不回答更糟。",
        "",
        "建议：",
        "  · 把报错原文完整粘贴进来，尤其是错误码、工具名和状态串",
        "  · 说明是哪个工具报的错（SP Flash Tool / MiFlash / QFIL / fastboot）",
        "  · 如果这是少见报错，可以在设置里开启「联网查询」补充检索",
        "",
        "-" * 58,
    ]
    return "\n".join(lines)


def _render_matches(finding: Finding, matches: list[Match]) -> str:
    """Build the plain-text solution report shown to the user."""
    lines: list[str] = []

    lines.append(_HEADER)
    lines.append(" 诊断结果")
    lines.append(_HEADER)

    if finding.platform != "unknown":
        lines.append(f"平台判定 : {finding.platform_label}")
        lines.append(f"置信度   : {finding.confidence:.0%}")
    else:
        lines.append("平台判定 : 未能判定（日志中未见明确平台特征）")

    if finding.mode:
        lines.append(f"当前模式 : {finding.mode}")

    if finding.signals:
        lines.append("判定依据 : " + "、".join(finding.signals[:6]))

    if finding.device_hints:
        lines.append("设备线索 : " + "；".join(finding.device_hints))

    if finding.error_codes:
        lines.append("识别到错误码：")
        for code in finding.error_codes:
            lines.append(f"  · {code}")

    if finding.platform == "unknown" and not matches:
        lines.append("")
        lines.append("建议：粘贴更完整的报错输出（包含工具名、错误码、模式字样），")
        lines.append("例如 SP Flash Tool / MiFlash / QFIL 的完整日志行。")
        return "\n".join(lines)

    lines.append("")
    lines.append(_HEADER)
    lines.append(f" 匹配到的解决方案（{len(matches)} 条）")
    lines.append(_HEADER)

    if not matches:
        lines.append("知识库中没有匹配条目。")
        lines.append("可尝试补充日志中的关键错误原文后重新检测。")
        return "\n".join(lines)

    for index, match in enumerate(matches, start=1):
        lines.append("")
        lines.append(f"【{index}】{match.entry.title}")
        lines.append(f"     平台: {match.entry.platform}   匹配度: {match.score}   {match.reason}")

        if match.entry.symptom:
            lines.append("")
            lines.append("  -- 症状 --")
            lines.extend(_indent(match.entry.symptom))

        if match.entry.cause:
            lines.append("")
            lines.append("  -- 原因 --")
            lines.extend(_indent(match.entry.cause))

        if match.entry.steps:
            lines.append("")
            lines.append("  -- 处理步骤 --")
            lines.extend(_indent(match.entry.steps))

        if match.entry.verify:
            lines.append("")
            lines.append("  -- 验证 --")
            lines.extend(_indent(match.entry.verify))

        if match.entry.todo:
            lines.append("")
            lines.append("  -- 待确认 --")
            lines.extend(_indent(match.entry.todo))

        lines.append("-" * 58)

    lines.append("")
    lines.append("提示：以上内容来自本地知识库，风险操作前请先备份数据。")
    return "\n".join(lines)


def _indent(block: str, prefix: str = "  ") -> list[str]:
    """Indent a markdown block, keeping code fences readable."""
    out: list[str] = []
    for line in block.strip().splitlines():
        out.append((prefix + line).rstrip())
    return out


def empty_report() -> str:
    return (
        "请把设备报错日志粘贴到上方输入框，然后点击「检测并给出方案」。\n\n"
        "也可以点「选择图片」，把手机屏幕截图或照片丢进来 —— 应用会先读出图上的\n"
        "文字（OCR），再用文字检索知识库；同时识别画面属于哪种报错作为补充。\n\n"
        "支持的内容包括：\n"
        "  · SP Flash Tool / MTK 相关报错（ERROR 4032、STATUS_BROM_* 等）\n"
        "  · 高通 Sahara / Firehose / QFIL / MiFlash 报错\n"
        "  · fastboot 命令输出（FAILED (remote: ...)）\n"
        "  · Recovery 日志（E:failed to mount ...）\n"
        "  · AVB / dm-verity 校验失败提示"
    )


# --------------------------------------------------------------------------
# Full image pipeline: OCR first, screen matching second
# --------------------------------------------------------------------------


# A knowledge-base match must clear this score before it is presented as the
# answer. Measured on real screenshots: an update-progress screen scored 16.6 and
# a plain fastboot screen 10.6 against unrelated pages - both pure noise.
MIN_IMAGE_MATCH_SCORE = 30.0


@dataclass
class ImageAnalysis:
    """Everything derived from one image."""

    screen: object | None = None          # RecognitionResult
    ocr: object | None = None             # OcrResult
    keywords: list[str] = field(default_factory=list)
    matches: list = field(default_factory=list)   # list[Match]
    finding: object | None = None         # Finding, when OCR text was analysed
    text: str = ""
    entry: object | None = None           # Entry presented as the answer
    suggestion: object | None = None      # best guess, shown only as a hint
    error_like: bool = False
    error_hits: list[str] = field(default_factory=list)


def analyze_image(kb: KB, recognizer, image_path, ocr_backend: str | None = None) -> ImageAnalysis:
    """Run the whole image path: read text, then fall back to screen matching.

    Text comes first because it is far more precise: OCR can read the literal
    ``ERROR 4032``, whereas pixel matching can only say "this looks like an MTK
    error dialog". Screen matching still runs, because it works when OCR returns
    nothing (a photo too blurry to read) and it supplies the KB entry when OCR
    finds words but no page matches them.

    A solution is only *presented* when the image actually reports a fault (see
    ``looks_like_error``) **and** the match clears ``MIN_IMAGE_MATCH_SCORE``.
    Otherwise the best candidate is demoted to a clearly-labelled suggestion.
    """
    from .ocr import keywords_from_text, looks_like_error, normalize_confusions, recognize_text
    from .scanner import analyze

    analysis = ImageAnalysis()

    # ---- 1. text ----
    ocr_result = None
    try:
        ocr_result = recognize_text(image_path_to_image(image_path), backend=ocr_backend)
    except Exception as exc:  # pragma: no cover - defensive
        ocr_result = None
        logger.debug("OCR 失败: %s", exc)
    analysis.ocr = ocr_result

    search_text = ""
    if ocr_result is not None and ocr_result.ok:
        analysis.keywords = keywords_from_text(ocr_result.text)
        analysis.error_like, analysis.error_hits = looks_like_error(ocr_result.text)

        # Search with the recognised text; the confusion-normalised form is what
        # usually matches, but the raw text can match too, so try both.
        search_text = normalize_confusions(ocr_result.text) or ocr_result.text
        analysis.finding = analyze(search_text)
        analysis.matches = kb.search(search_text, limit=5)

        if not analysis.matches and analysis.keywords:
            # Retry with just the salient words (drops OCR noise and punctuation).
            joined = " ".join(analysis.keywords)
            analysis.matches = kb.search(joined, limit=5)
            if analysis.matches:
                analysis.finding = analyze(joined)

    # ---- 2. screen type ----
    if recognizer is not None:
        analysis.screen = recognizer.recognize_path(image_path)

    # ---- 3. decide what to present ----
    best = analysis.matches[0] if analysis.matches else None
    screen_matched = analysis.screen is not None and getattr(analysis.screen, "matched", False)

    if analysis.error_like and best is not None and best.score >= MIN_IMAGE_MATCH_SCORE:
        analysis.entry = best.entry
    elif analysis.error_like and screen_matched:
        # No confident text match, but the picture is a recognisable fault screen.
        slug = analysis.screen.kb_slug
        analysis.entry = next((e for e in kb.entries if e.slug == slug), None)

    # Whatever is left over becomes a hint, never the answer.
    if analysis.entry is None:
        if best is not None:
            analysis.suggestion = best.entry
        elif screen_matched:
            slug = analysis.screen.kb_slug
            analysis.suggestion = next((e for e in kb.entries if e.slug == slug), None)

    analysis.text = render_image_analysis(analysis)
    return analysis


def image_path_to_image(path):
    """Open an image file for OCR (kept small: OCR upscales as needed)."""
    from PIL import Image

    with Image.open(path) as handle:
        try:
            handle.draft("RGB", (1024, 1024))
        except Exception:
            pass
        handle.load()
        return handle.convert("RGB")


def render_image_analysis(analysis: ImageAnalysis) -> str:
    """Render the combined OCR + screen-type result."""
    lines: list[str] = []
    screen = analysis.screen
    ocr = analysis.ocr

    lines.append(_HEADER)
    lines.append(" 图片识别结果")
    lines.append(_HEADER)

    # ---- OCR section ----
    if ocr is not None and ocr.ok:
        lines.append(f"识别文字 : 已读出（后端 {ocr.backend}）")
        if analysis.finding is not None:
            lines.append(f"平台判定 : {analysis.finding.platform_label}")
        if analysis.keywords:
            lines.append("关键词   : " + "、".join(analysis.keywords[:12]))
        lines.append("")
        lines.append("  -- 图上文字 --")
        for line in ocr.text.splitlines():
            if line.strip():
                lines.append(f"  {line.strip()}")
    else:
        reason = ""
        if ocr is not None:
            reason = ocr.error or ""
        lines.append("识别文字 : 未能读出图上文字" + (f"（{reason}）" if reason else ""))
        lines.append(
            "          可以把报错文字直接粘贴到日志框，那比图片可靠得多。"
        )

    # ---- screen type section ----
    if screen is not None:
        lines.append("")
        if getattr(screen, "matched", False):
            lines.append(
                f"画面类型 : {screen.title}（置信度 {screen.confidence:.0%}）"
            )
        else:
            lines.append("画面类型 : 未能确定")
            if getattr(screen, "title", ""):
                lines.append(
                    f"           最接近的候选：{screen.title}"
                    f"（{screen.confidence:.0%}）"
                )
        source = getattr(screen, "source", "")
        if source == "synthetic":
            lines.append(
                "           注意：参考图是程序生成的示意图，真机画面可能不同。"
            )

    # ---- no-fault case: say so instead of inventing a repair ----
    if analysis.entry is None:
        lines.append("")
        lines.append(_HEADER)
        if ocr is not None and ocr.ok and not analysis.error_like:
            lines.append(" 结论：图中没有发现报错信息")
            lines.append(_HEADER)
            lines.append("")
            lines.append("  读到的文字里没有出现任何报错特征（如 ERROR / FAILED /")
            lines.append("  无法 / 失败 / 损坏 / 错误码）。**所以不给出刷机方案** ——")
            lines.append("  对一张没有报错的截图套用刷机步骤，比不回答危险得多。")
            lines.append("")
            lines.append("  如果设备其实有问题，请把报错那一屏截图发来，或者把报错")
            lines.append("  文字直接粘到日志框。")
        elif ocr is not None and ocr.ok:
            lines.append(" 结论：读到了文字，但知识库没有匹配到条目")
            lines.append(_HEADER)
            lines.append("")
            lines.append(f"  识别到的报错特征：{'、'.join(analysis.error_hits[:8])}")
            lines.append("  可以补充更多报错文字，或换个说法再试。")
        else:
            lines.append(" 结论：未能从图中读出可用信息")
            lines.append(_HEADER)
            lines.append("")
            lines.append("  请把报错文字粘贴到日志框，或换一张更清晰的截图。")

        if analysis.suggestion is not None:
            lines.append("")
            lines.append(
                f"  参考（仅供参考，不代表就是这个问题）：{analysis.suggestion.title}"
            )
        lines.append("")
        lines.append("-" * 58)
        lines.append("提示：文字识别优先，画面识别作为补充。")
        return "\n".join(lines)

    # ---- matches / solution ----
    lines.append("")
    lines.append(_HEADER)
    lines.append(f" 对应解决方案：{analysis.entry.title}")
    lines.append(_HEADER)
    for heading, block in (
        ("症状", analysis.entry.symptom),
        ("原因", analysis.entry.cause),
        ("步骤", analysis.entry.steps),
        ("验证", analysis.entry.verify),
        ("待确认", analysis.entry.todo),
    ):
        if not block:
            continue
        lines.append("")
        lines.append(f"  -- {heading} --")
        lines.extend(_indent(block))
    if analysis.matches:
        others = [m for m in analysis.matches[1:4] if m.entry is not analysis.entry]
        if others:
            lines.append("")
            lines.append("其它可能相关的条目：")
            for match in others:
                lines.append(f"  · {match.entry.title}（{match.score}）")

    lines.append("")
    lines.append("-" * 58)
    lines.append("提示：文字识别优先，画面识别作为补充。")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Image recognition reporting
# --------------------------------------------------------------------------


def render_recognition(result, entry=None) -> str:
    """Render the outcome of image recognition.

    Args:
        result: a ``mirecovery.recognize.RecognitionResult``.
        entry: the matched knowledge-base entry, if one was found.
    """
    lines: list[str] = []
    lines.append(_HEADER)
    lines.append(" 图片识别结果")
    lines.append(_HEADER)

    if result.matched:
        lines.append(f"识别画面 : {result.title}")
        lines.append(f"置信度   : {result.confidence:.0%}")
        lines.append(f"判定依据 : {result.reason}")
    else:
        lines.append("未能确定画面类型")
        if result.title:
            lines.append(f"最接近的候选 : {result.title}（{result.confidence:.0%}）")
        if result.reason:
            lines.append("")
            lines.append(result.reason)

    if result.source == "synthetic":
        lines.append("")
        lines.append(
            "注意：当前参考图是程序生成的示意图（source=synthetic），真机画面"
            "可能与它不一致，结论仅供参考；请把报错文字贴进日志框复核。"
        )

    if result.explanations:
        lines.append("")
        lines.append("特征相似度（越接近 100% 越像）：")
        for name, score in result.explanations[:5]:
            lines.append(f"  · {name:<14} {score:.0%}")

    others = [c for c in result.top_n(4) if c.label != result.label]
    if others:
        lines.append("")
        lines.append("其它候选：")
        for candidate in others[:3]:
            lines.append(f"  · {candidate.title}  {candidate.score:.0%}")

    if entry is not None:
        lines.append("")
        lines.append(_HEADER)
        lines.append(f" 对应解决方案：{entry.title}")
        lines.append(_HEADER)
        for heading, block in (
            ("症状", entry.symptom),
            ("原因", entry.cause),
            ("步骤", entry.steps),
            ("验证", entry.verify),
            ("待确认", entry.todo),
        ):
            if not block:
                continue
            lines.append("")
            lines.append(f"  -- {heading} --")
            lines.extend(_indent(block))
    elif result.matched:
        lines.append("")
        lines.append(f"（知识库中未找到页面 {result.kb_slug}，请确认知识库已同步）")

    lines.append("")
    lines.append("-" * 58)
    lines.append("提示：图片识别只判断画面类型，读不出图里的具体错误码。")
    lines.append("      能把报错文字粘贴到日志框的话，检索会准确得多。")
    return "\n".join(lines)


def recognition_report(kb: KB, result) -> tuple[Entry | None, str]:
    """Look up the KB entry for a recognition result and render everything.

    Returns ``(entry, text)``; ``entry`` is ``None`` when the matched slug is not
    in the knowledge base (e.g. the reference library is newer than the KB).
    """
    entry: Entry | None = None
    if result.matched and result.kb_slug:
        for candidate in kb.entries:
            if candidate.slug == result.kb_slug:
                entry = candidate
                break
    return entry, render_recognition(result, entry)


def build_report(kb: KB, text: str, limit: int = 5) -> tuple[Finding, list[Match], str]:
    """Convenience wrapper: analyse, search, render.

    When a platform is confidently identified its pages are promoted, but the
    ordering stays a re-rank rather than a truncation. An earlier version kept
    ``platform_matches + others[:1]``, which could drop a genuinely better
    cross-platform hit entirely - the platform preference is a tie-breaker, not
    a filter.
    """
    from .scanner import analyze

    finding = analyze(text)
    matches = kb.search(text, limit=limit)

    if finding.platform != "unknown" and len(matches) > 1:
        def rank(match: Match) -> tuple[int, float]:
            same = 0 if match.entry.platform == finding.platform else 1
            return (same, -match.score)

        matches = sorted(matches, key=rank)

    return finding, matches, render(finding, matches)
