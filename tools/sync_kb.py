#!/usr/bin/env python3
"""Mirror the project knowledge base into the dsh-kb Obsidian vault.

The canonical source of truth is this project's ``kb/`` directory (version
controlled, consumed by ``tools/build_kb.py``). This script publishes it to the
dsh-kb root so the wiki is browsable/searchable in the dsh-kb 界面 and so that
the schema's ``index.md`` / ``log.md`` bookkeeping stays current.

Usage
-----
    python tools/sync_kb.py                    # mirror to ~/.dsh/kb
    python tools/sync_kb.py --target D:\\kb      # mirror somewhere else
    python tools/sync_kb.py --dry-run

Notes
-----
* ``raw/`` is never touched (schema: raw material is immutable).
* Existing wiki pages are overwritten with the project version, because the
  project tree is authoritative for this KB.
* ``index.md`` is regenerated; ``log.md`` gets one appended line per run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import build_kb  # noqa: E402

DEFAULT_TARGET = Path.home() / ".dsh" / "kb"
AUTHOR = "deepseek-agent"


def sync(source: Path, target: Path, dry_run: bool = False) -> int:
    if not (source / "wiki").is_dir():
        print(f"[sync_kb] ERROR: 源目录没有 wiki/：{source}", file=sys.stderr)
        return 1

    payload, entries = build_kb.build(source)

    if dry_run:
        print(f"[sync_kb] dry-run：将同步 {len(entries)} 个页面到 {target}")
        for entry in entries:
            print(f"  - {entry['path']}")
        return 0

    target.mkdir(parents=True, exist_ok=True)

    # 1. wiki/**/*.md
    copied = 0
    for page in sorted((source / "wiki").rglob("*.md")):
        relative = page.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(page, destination)
        copied += 1

    # 2. Keep the schema in sync (targets may be a fresh vault).
    source_schema = source / "schema.md"
    if source_schema.is_file():
        shutil.copy2(source_schema, target / "schema.md")

    # 3. index.md regenerated from frontmatter.
    index_text = build_kb.render_index(entries, target)
    (target / "index.md").write_text(index_text, encoding="utf-8")

    # 4. log.md — always read the latest file first, then append (schema rule).
    log_path = target / "log.md"
    existing = ""
    if log_path.is_file():
        existing = log_path.read_text(encoding="utf-8")
    if not existing.strip():
        existing = (
            "# 操作流水\n\n"
            "<!-- 格式：- YYYY-MM-DD HH:mm <author> <新增|更新|标注矛盾> "
            "<wiki 路径> ← <raw 路径> -->\n"
        )

    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"- {stamp} {AUTHOR} 更新 wiki/howtos/ "
        f"（批量同步 {copied} 篇：MTK / 高通 / fastboot / recovery / AVB） ← 项目 mi-recovery-helper/kb"
    ]
    if not existing.endswith("\n"):
        existing += "\n"
    log_path.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")

    print(f"[sync_kb] 已同步 {copied} 个页面 -> {target}")
    print(f"[sync_kb] index.md / log.md / schema.md 已更新")

    by_platform: dict[str, int] = {}
    for entry in entries:
        key = str(entry["platform"])
        by_platform[key] = by_platform.get(key, 0) + 1
    print("[sync_kb] 平台分布 " + "、".join(f"{k}:{v}" for k, v in sorted(by_platform.items())))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=str(PROJECT_ROOT / "kb"),
                        help="项目内知识库根目录（含 wiki/）")
    parser.add_argument("--target", default=str(DEFAULT_TARGET),
                        help="dsh-kb 根目录，默认 ~/.dsh/kb")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    return sync(Path(args.source).resolve(), Path(args.target).expanduser(), args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
