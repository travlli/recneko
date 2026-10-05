#!/usr/bin/env python3
"""Research missing errors online and draft knowledge-base pages from the sources.

Why this exists
---------------
The bundled KB covers common failures but not the long tail, and every existing
page has ``sources: []`` - the content is ungrounded. This tool closes both gaps
at once:

1. look the error up online (``mirecovery.online``),
2. write the material it actually retrieved into ``kb/raw/web/`` as immutable
   evidence, with URLs,
3. draft a KB page whose ``sources:`` point at that raw file,
4. **refuse to write anything** when the research was not grounded in a real,
   fetched source.

Rule 4 is the important one. A KB page that looks authoritative but came from a
model's memory is worse than no page: the whole point of this project is to stop
people from following a wrong flashing procedure. Unverified topics are reported
as skipped, never written.

    python tools/research_kb.py --list
    python tools/research_kb.py --only antirollback
    python tools/research_kb.py --all --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mirecovery.online import AiConfig, OnlineAnswer, redact, render_answer, research  # noqa: E402

KB_ROOT = PROJECT_ROOT / "kb"
WIKI_DIR = KB_ROOT / "wiki" / "howtos"
RAW_DIR = KB_ROOT / "raw" / "web"

AUTHOR = "deepseek-agent"

# Errors measured as uncovered in the project's issue #5. Each entry names the
# slug and platform the page should have; the *content* must come from sources.
TARGETS: list[dict] = [
    {
        "key": "antirollback",
        "query": '"Antirollback check error" xiaomi',
        "slug": "fastboot-antirollback-check-error",
        "platform": "fastboot",
        "error": "error: Antirollback check error",
        "title": "fastboot 报错 Antirollback check error：防回滚校验触发",
        "tags": ["fastboot", "xiaomi", "antirollback", "rollback", "变砖"],
        "keywords": [
            "Antirollback check error", "anti-rollback", "防回滚", "回滚保护",
            "rollback index", "刷旧版本失败", "降级失败", "变砖风险",
        ],
    },
    {
        "key": "mismatch",
        "query": '"Missmatching image and device" xiaomi',
        "slug": "fastboot-mismatching-image-and-device",
        "platform": "fastboot",
        "error": "error: Missmatching image and device error",
        "title": "fastboot/MiFlash 报错 Missmatching image and device：刷错包或机型不匹配",
        "tags": ["fastboot", "miflash", "xiaomi", "rom", "机型不匹配"],
        "keywords": [
            "Missmatching image and device", "Mismatching image and device",
            "机型不匹配", "刷错包", "wrong rom", "rom 不匹配", "codename 不一致",
        ],
    },
    {
        "key": "toolinks",
        "query": '"Too many links" fastboot',
        "slug": "fastboot-data-transfer-failure-too-many-links",
        "platform": "fastboot",
        "error": "error: FAILED (data transfer failure (Too many links))",
        "title": "fastboot 报错 FAILED (data transfer failure (Too many links))：USB 链路不稳",
        "tags": ["fastboot", "usb", "cable", "hub", "传输失败"],
        "keywords": [
            "data transfer failure", "Too many links", "USB 传输失败",
            "换数据线", "USB 2.0 接口", "usb hub", "刷机中断",
        ],
    },
    {
        "key": "sparse",
        "query": '"Error reading sparse file" fastboot',
        "slug": "fastboot-error-reading-sparse-file",
        "platform": "fastboot",
        "error": "error: Sending sparse 'system' 3/5 FAILED (Error reading sparse file)",
        "title": "fastboot 报错 Error reading sparse file：镜像/磁盘读取失败",
        "tags": ["fastboot", "sparse", "image", "刷机失败"],
        "keywords": [
            "Error reading sparse file", "Sending sparse", "sparse file",
            "镜像损坏", "解压镜像", "fastboot 刷 system 失败",
        ],
    },
    {
        "key": "flashall",
        "query": '"flash_all_lock.bat" not found',
        "slug": "miflash-flash-all-lock-bat-missing",
        "platform": "fastboot",
        "error": "can not found file flash_all_lock.bat",
        "title": "MiFlash 报错 can not found file flash_all_lock.bat：线刷包缺脚本",
        "tags": ["miflash", "fastboot", "xiaomi", "线刷", "脚本缺失"],
        "keywords": [
            "flash_all_lock.bat", "can not found file", "找不到脚本",
            "线刷包不完整", "tgz 解压", "MiFlash 报错", "不是 fastboot 包",
        ],
    },
    {
        "key": "presskey",
        "query": '"press any key to shutdown" fastboot xiaomi',
        "slug": "device-press-any-key-to-shutdown",
        "platform": "unknown",
        "error": "手机屏幕显示 press any key to shutdown",
        "title": "手机显示 press any key to shutdown：不是故障，是工具让设备等待",
        "tags": ["fastboot", "usb", "windows", "驱动", "误判"],
        "keywords": [
            "press any key to shutdown", "按任意键关机", "不是手机故障",
            "USB 驱动", "fastboot 卡住", "电脑端问题",
        ],
    },
    {
        "key": "length",
        "query": '"Length cannot be less than zero" miflash',
        "slug": "miflash-length-cannot-be-less-than-zero",
        "platform": "unknown",
        "error": "加载设备提示 Length cannot be less than zero",
        "title": "MiFlash/工具报错 Length cannot be less than zero：加载设备失败",
        "tags": ["miflash", "qualcomm", "windows", "驱动", "加载设备"],
        "keywords": [
            "Length cannot be less than zero", "加载设备失败", "Length cannot be less",
            "驱动未安装", "端口识别", "电脑端问题",
        ],
    },
    {
        "key": "checkpoint",
        "query": '"Not catch checkpoint" miflash',
        "slug": "miflash-not-catch-checkpoint-flash-not-done",
        "platform": "fastboot",
        "error": "error:Not catch checkpoint ($fastboot -s .*lock), flash is not done",
        "title": "MiFlash 报错 Not catch checkpoint / flash is not done：脚本校验未通过",
        "tags": ["miflash", "fastboot", "xiaomi", "线刷", "脚本校验"],
        "keywords": [
            "Not catch checkpoint", "flash is not done", "刷机未完成",
            "flash_all_lock.bat", "MiFlash 报错", "重新线刷",
        ],
    },
]


def slugify_today() -> str:
    return dt.date.today().isoformat()


def raw_path_for(target: dict) -> Path:
    return RAW_DIR / f"{target['slug']}-{slugify_today()}.md"


def write_raw(target: dict, answer: OnlineAnswer, text: str) -> Path:
    """Persist the retrieved material as immutable evidence.

    The schema requires ``sources`` to point at ``raw/``; storing the actual
    fetched text (not just a URL) is what makes a page checkable later, and
    what makes the claim survive the source going offline.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = raw_path_for(target)
    lines = [
        "---",
        f"title: 网络检索素材：{target['error']}",
        "type: web-research",
        f"retrieved: {slugify_today()}",
        f"query: {answer.queries[0] if answer.queries else ''}",
        f"model: {answer.model}",
        f"tokens: {answer.tokens}",
        "urls:",
    ]
    for index, source in enumerate(answer.sources, start=1):
        lines.append(f"  - \"[{index}] {source.title} - {source.url}\"")
    lines += [
        "---",
        "",
        "# 检索到的原始材料（不可变，勿改）",
        "",
        "> 这是 `tools/research_kb.py` 联网检索后抓到的正文原文，作为 wiki 条目的依据。",
        "> 未经人工复核，**不是官方文档**。",
        "",
        "## 模型基于以上材料给出的整理（未经人工复核）",
        "",
        text.strip(),
        "",
        "## 抓取到的来源正文",
        "",
    ]
    for index, source in enumerate(answer.sources, start=1):
        lines += [
            f"### [{index}] {source.title}",
            "",
            f"URL: {source.url}",
            "",
            source.snippet.strip() or "(正文为空)",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def sanitize_model_text(text: str) -> str:
    """Neutralise things that would corrupt the knowledge base.

    Obsidian-style ``[[link]]`` syntax is meaningful in this KB (it is checked for
    dead links at build time). A model writing a bracketed source title such as
    ``[2.2.0] Fastboot flash failure ...`` produces ``[[2.2.0]]``, which the
    builder then reports as a dead link and fails the whole build - measured, this
    is exactly what happened on the first enrichment run.
    """
    # Only escape the opening bracket of a doubled pair, keeping the text.
    return re.sub(r"\[\[([^\]]{1,80})\]\](?!\()", lambda m: "[\\[" + m.group(1) + "\\]]", text)


def render_page(target: dict, answer: OnlineAnswer, raw_rel: str, model_text: str) -> str:
    """Build the KB page, keeping the model's structure but owning the metadata."""
    today = slugify_today()
    keywords = json.dumps(target["keywords"], ensure_ascii=False)
    tags = "[" + ", ".join(target["tags"]) + "]"
    body = sanitize_model_text(model_text.strip())

    frontmatter = [
        "---",
        f"title: {target['title']}",
        f"tags: {tags}",
        f"keywords: {keywords}",
        f"author: {AUTHOR}",
        f"created: {today}",
        f"updated: {today}",
        f"sources: [{raw_rel}]",
        f"platform: {target['platform']}",
        "---",
        "",
        f"# {target['title']}",
        "",
        "> ⚠️ 本条目的内容来自**联网检索 + 模型整理**，来源见文末，"
        "**尚未经过人工/官方核实**。",
        "> 动手前请先读「待确认」，并自行核对来源原文。",
        "",
        body,
        "",
        "## 来源",
        "",
    ]
    for index, source in enumerate(answer.sources, start=1):
        frontmatter.append(f"- [{index}] [{source.title}]({source.url})")
    frontmatter += [
        "",
        f"原始素材（抓取正文）：`{raw_rel}`",
        "",
    ]
    return "\n".join(frontmatter)


PAGE_PROMPT = """请根据【资料】写一篇中文排错条目，只使用资料里出现的信息。

必须使用以下小节标题（不要改标题、不要加别的小节）：

## 症状
（这个报错长什么样、在什么场景出现。可引用资料里的原文片段）

## 原因
（资料里给出的原因。每条后面标注来源编号，如 [1]）

## 步骤
（资料里给出的处理办法。每条后面标注来源编号。如果资料里的做法有风险或只是社区经验，必须写明）

## 验证
（怎么确认修好了）

## 待确认
（资料没有说清楚、或你需要用户补充的信息。资料不足就如实写"资料未涉及"）

硬性要求：
- 只写资料里有的内容，不要凭记忆补充刷机步骤或命令。
- 每条结论后标注来源编号。
- 如果资料整体不足以支撑某个小节，就写"资料不足，无法确认"。
- 不要编造文件名、命令、错误码、链接。
"""


def research_target(target: dict, config: AiConfig, client=None) -> OnlineAnswer:
    # An explicit per-target query beats the generic one built from the error
    # text: measured, `"Too many links"` alone surfaced unrelated projects, while
    # `"Too many links" fastboot` surfaced the TWRP thread about exactly this.
    return research(target["error"], config=config, client=client, query=target.get("query"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="列出目标条目")
    parser.add_argument("--only", action="append", default=[], help="只处理指定 key")
    parser.add_argument("--all", action="store_true", help="处理全部目标")
    parser.add_argument("--dry-run", action="store_true", help="只检索，不写文件")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的页面")
    args = parser.parse_args(argv)

    if args.list or not (args.only or args.all):
        print("目标条目：")
        for target in TARGETS:
            exists = (WIKI_DIR / f"{target['slug']}.md").is_file()
            mark = "已存在" if exists else "缺失"
            print(f"  {target['key']:<12} [{mark}] {target['error'][:56]}")
        if not (args.only or args.all):
            print("\n用 --only <key> 或 --all 开始检索。")
            return 0

    config = AiConfig.load()
    if not config.usable:
        print(
            "联网查询不可用。请先配置（环境变量或 "
            f"{Path.home() / '.dsh'}/…）：\n"
            "  RECNEKO_AI_BASE_URL / RECNEKO_AI_API_KEY / RECNEKO_AI_MODEL\n"
            "  并把 enabled 设为 true"
        )
        return 2

    selected = [
        target
        for target in TARGETS
        if (not args.only or target["key"] in args.only)
    ]
    if args.all:
        selected = TARGETS

    written: list[str] = []
    skipped: list[str] = []

    for target in selected:
        page_path = WIKI_DIR / f"{target['slug']}.md"
        if page_path.is_file() and not args.force:
            print(f"[跳过] {target['key']}：页面已存在")
            skipped.append(target["key"])
            continue

        print(f"\n=== {target['key']} : {target['error']} ===")
        answer = research_target(target, config)
        if not answer.ok:
            print(f"[跳过] 未能获得结论：{answer.error}")
            skipped.append(target["key"])
            continue

        # The runtime app happily answers from the model's own knowledge, but a
        # knowledge-base page is a lasting artefact and must stay traceable. No
        # fetched source means no page.
        if not answer.grounded:
            print(f"[跳过] 没有可核对的来源（{answer.error}），不写入知识库")
            skipped.append(target["key"])
            continue

        print(f"  来源 {len(answer.sources)} 条，{answer.tokens} tokens")
        for index, source in enumerate(answer.sources, start=1):
            print(f"    [{index}] {source.title[:60]}")

        if args.dry_run:
            print(render_answer(answer)[:1500])
            continue

        # A second, page-shaped pass over the *same* material, so the KB page has
        # the schema's sections while the citations stay tied to real sources.
        from mirecovery.online import AiClient

        client = AiClient(config)
        material = "\n\n".join(
            f"【资料 {i}】{s.title}\nURL: {s.url}\n{s.snippet}"
            for i, s in enumerate(answer.sources, start=1)
        )
        try:
            page_text, extra_tokens = client.chat(
                [
                    {"role": "system", "content": PAGE_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"报错：{target['error']}\n\n"
                            f"===== 资料开始 =====\n{material}\n===== 资料结束 =====\n\n"
                            "请按格式写条目。"
                        ),
                    },
                ]
            )
        except Exception as exc:
            print(f"[跳过] 生成条目失败：{type(exc).__name__}: {exc}")
            skipped.append(target["key"])
            continue

        if not re.search(r"\[\d+\]", page_text):
            print("[跳过] 生成的条目没有引用任何来源，按规则不写入")
            skipped.append(target["key"])
            continue

        answer.tokens += extra_tokens
        raw_path = write_raw(target, answer, page_text)
        raw_rel = raw_path.relative_to(KB_ROOT).as_posix()
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(render_page(target, answer, raw_rel, page_text), encoding="utf-8")
        print(f"[写入] {page_path.relative_to(PROJECT_ROOT)}  ← {raw_rel}")
        written.append(target["key"])

    print()
    print(f"完成：写入 {len(written)} 条，跳过 {len(skipped)} 条")
    if written:
        print("写入：" + "、".join(written))
    if skipped:
        print("跳过：" + "、".join(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
