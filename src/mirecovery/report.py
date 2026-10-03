"""Render an analysis result + KB matches into readable report text.

Kept separate from the GUI so the same rendering can be used for the
clipboard, for console output, and for tests.
"""

from __future__ import annotations

from .kb import KB, Match
from .scanner import Finding

_HEADER = "=" * 58


def render(finding: Finding, matches: list[Match]) -> str:
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
        "也可以点「选择图片」，把手机屏幕截图或照片丢进来 —— 应用会先识别画面\n"
        "属于哪种报错，再给出对应方案。\n\n"
        "支持的内容包括：\n"
        "  · SP Flash Tool / MTK 相关报错（ERROR 4032、STATUS_BROM_* 等）\n"
        "  · 高通 Sahara / Firehose / QFIL / MiFlash 报错\n"
        "  · fastboot 命令输出（FAILED (remote: ...)）\n"
        "  · Recovery 日志（E:failed to mount ...）\n"
        "  · AVB / dm-verity 校验失败提示"
    )


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


def recognition_report(kb: KB, result) -> tuple[object, str]:
    """Look up the KB entry for a recognition result and render everything."""
    entry = None
    if result.matched and result.kb_slug:
        for candidate in kb.entries:
            if candidate.slug == result.kb_slug:
                entry = candidate
                break
    return entry, render_recognition(result, entry)


def build_report(kb: KB, text: str, limit: int = 5) -> tuple[Finding, list[Match], str]:
    """Convenience wrapper: analyse, search, render."""
    from .scanner import analyze

    finding = analyze(text)
    # If a platform was confidently identified, prefer same-platform entries
    # but never hide a clearly better cross-platform hit.
    matches = kb.search(text, limit=limit)
    if finding.platform != "unknown" and len(matches) > 1:
        platform_matches = [m for m in matches if m.entry.platform == finding.platform]
        others = [m for m in matches if m.entry.platform != finding.platform]
        if platform_matches:
            matches = platform_matches + others[:1]
    return finding, matches, render(finding, matches)
