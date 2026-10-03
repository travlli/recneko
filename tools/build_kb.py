#!/usr/bin/env python3
"""Build ``kb.json`` (and a browsable ``index.md``) from the Obsidian wiki.

The knowledge base lives as Markdown pages under ``kb/wiki/howtos/`` and is
authored/published through the dsh-kb plugin. The Toga app cannot parse
Markdown at runtime (and should not ship a Markdown renderer), so this script
flattens every page into a single JSON document that is bundled into the
executable / APK.

Usage
-----
    python tools/build_kb.py                 # build into src/mirecovery/data/
    python tools/build_kb.py --kb-root <dir> --out <file>

Run it whenever pages are added or edited under ``kb/wiki/``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Frontmatter / Markdown handling
# --------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)

# Map the canonical Chinese section headings onto JSON fields.
SECTION_ALIASES: dict[str, str] = {
    "症状": "symptom",
    "原因": "cause",
    "步骤": "steps",
    "验证": "verify",
    "待确认": "todo",
}


def parse_scalar(raw: str) -> str:
    """Parse a simple YAML scalar (strip quotes)."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_inline_list(raw: str) -> list[str]:
    """Parse ``[a, b, "c, d"]`` style inline YAML lists."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    if not raw.strip():
        return []
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in raw:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
        elif char in "\"'":
            quote = char
        elif char == ",":
            items.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    items.append("".join(current).strip())
    return [item for item in items if item]


def parse_frontmatter(block: str) -> dict[str, object]:
    """Parse the small, flat YAML subset the KB schema actually uses."""
    data: dict[str, object] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith("[") or value.startswith("["):
            data[key] = parse_inline_list(value)
        elif value == "" or value == "[]":
            data[key] = [] if value == "[]" else ""
        else:
            data[key] = parse_scalar(value)
    return data


def split_sections(body: str) -> dict[str, str]:
    """Split the page body into ``##`` sections keyed by canonical field."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(body))
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        field = SECTION_ALIASES.get(heading)
        if field is None:
            # Keep unknown sections addressable rather than dropping content.
            field = heading
        sections[field] = content
    return sections


def parse_page(path: Path, kb_root: Path) -> dict[str, object]:
    """Parse one wiki page into the JSON entry shape."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    front: dict[str, object] = {}
    body = text
    if match:
        front = parse_frontmatter(match.group(1))
        body = text[match.end():]

    sections = split_sections(body)

    title = str(front.get("title") or "").strip()
    if not title:
        heading = _H1_RE.search(body)
        title = heading.group(1).strip() if heading else path.stem

    tags = front.get("tags") or []
    keywords = front.get("keywords") or []
    if isinstance(tags, str):
        tags = [tags]
    if isinstance(keywords, str):
        keywords = [keywords]

    # Category = the wiki subdirectory (howtos / decisions / ...).
    try:
        category = path.parent.relative_to(kb_root / "wiki").as_posix()
    except ValueError:
        category = path.parent.name

    return {
        "slug": path.stem,
        "title": title,
        "platform": str(front.get("platform") or "").strip() or "unknown",
        "category": category,
        "tags": [str(t) for t in tags],
        "keywords": [str(k) for k in keywords],
        "symptom": sections.get("symptom", ""),
        "cause": sections.get("cause", ""),
        "steps": sections.get("steps", ""),
        "verify": sections.get("verify", ""),
        "todo": sections.get("todo", ""),
        "body": body.strip(),
        "path": path.relative_to(kb_root).as_posix(),
    }


# --------------------------------------------------------------------------
# index.md rendering
# --------------------------------------------------------------------------

CATEGORY_TITLES = {
    "howtos": "Howtos",
    "decisions": "Decisions",
    "postmortems": "Postmortems",
    "notes": "Notes",
}


def render_index(entries: list[dict], kb_root: Path) -> str:
    """Regenerate index.md so every page is reachable (schema requirement)."""
    today = _dt.date.today().isoformat()
    grouped: dict[str, list[dict]] = {}
    for entry in entries:
        grouped.setdefault(str(entry["category"]), []).append(entry)

    lines = [
        "---",
        "title: 知识库目录",
        f"updated: {today}",
        "---",
        "",
        "# 知识库",
        "",
        "> 找东西用搜索（🔍）最快；新条目加工后请在对应小节挂链接。",
        "> 本文件由 `tools/build_kb.py` 依据各页面 frontmatter 自动生成，不要手工编辑。",
        "",
    ]

    ordered = list(CATEGORY_TITLES) + sorted(set(grouped) - set(CATEGORY_TITLES))
    for category in ordered:
        items = grouped.get(category)
        if not items:
            continue
        lines.append(f"## {CATEGORY_TITLES.get(category, category.title())}")
        lines.append("")
        for entry in sorted(items, key=lambda e: (str(e["platform"]), str(e["slug"]))):
            rel = f"wiki/{entry['category']}/{entry['slug']}.md"
            keywords = "、".join(entry["keywords"][:4])  # type: ignore[index]
            lines.append(f"- [[{entry['slug']}]] — {entry['title']}（`{entry['platform']}`）")
            if keywords:
                lines.append(f"  - 关键词：{keywords}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def build(kb_root: Path) -> tuple[dict, list[dict]]:
    wiki_root = kb_root / "wiki"
    if not wiki_root.is_dir():
        raise SystemExit(f"找不到 wiki 目录：{wiki_root}")

    paths = sorted(p for p in wiki_root.rglob("*.md") if p.is_file())
    entries = [parse_page(path, kb_root) for path in paths]
    entries.sort(key=lambda e: (str(e["platform"]), str(e["slug"])))

    payload = {
        "version": _dt.date.today().isoformat(),
        "generated_from": str(kb_root.name),
        "count": len(entries),
        "entries": entries,
    }
    return payload, entries


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parent
    project_root = here.parent

    parser = argparse.ArgumentParser(description="Build kb.json from the wiki pages")
    parser.add_argument("--kb-root", default=str(project_root / "kb"),
                        help="knowledge base root (contains wiki/)")
    parser.add_argument("--out", default=str(project_root / "src" / "mirecovery" / "data" / "kb.json"),
                        help="output kb.json path")
    parser.add_argument("--index", default=None,
                        help="also (re)write index.md at this path; default <kb-root>/index.md")
    parser.add_argument("--no-index", action="store_true", help="skip index.md regeneration")
    args = parser.parse_args(argv)

    kb_root = Path(args.kb_root).resolve()
    payload, entries = build(kb_root)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[build_kb] {len(entries)} 个条目 -> {out_path}")

    if not args.no_index:
        index_path = Path(args.index) if args.index else kb_root / "index.md"
        index_path.write_text(render_index(entries, kb_root), encoding="utf-8")
        print(f"[build_kb] index.md -> {index_path}")

    by_platform: dict[str, int] = {}
    for entry in entries:
        by_platform[str(entry["platform"])] = by_platform.get(str(entry["platform"]), 0) + 1
    summary = "、".join(f"{k}:{v}" for k, v in sorted(by_platform.items()))
    print(f"[build_kb] 平台分布 {summary}")

    # Cheap schema sanity check: a page without keywords cannot be retrieved.
    for entry in entries:
        if not entry["keywords"]:
            print(f"[build_kb] ⚠️  {entry['slug']} 缺少 keywords，检索效果会变差",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
