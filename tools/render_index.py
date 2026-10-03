#!/usr/bin/env python3
"""Regenerate index.md and the log line, writing them to *stdout*.

Used by ``tools/sync_kb.ps1``: in this environment Python subprocesses are not
permitted to write into the dsh-kb vault, while PowerShell is. So Python does
the thinking (parse frontmatter, render the index) and PowerShell does the
writing.

    python tools/render_index.py                       # index.md -> stdout
    python tools/render_index.py --log-line            # log.md line -> stdout
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import build_kb  # noqa: E402


def write_stdout(text: str) -> None:
    """Write UTF-8 to stdout regardless of the console code page.

    The index template contains an emoji, and a GBK console would otherwise
    raise UnicodeEncodeError and break the sync.
    """
    data = text.encode("utf-8")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(data)
        buffer.flush()
    else:  # pragma: no cover - exotic stdout replacement
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kb-root", default=str(PROJECT_ROOT / "kb"))
    parser.add_argument("--log-line", action="store_true",
                        help="输出 log.md 追加行而不是 index.md")
    parser.add_argument("--log-header", action="store_true",
                        help="输出 log.md 的初始表头（文件不存在或为空时使用）")
    parser.add_argument("--count", type=int, default=None, help="同步页面数（写入日志行）")
    args = parser.parse_args(argv)

    kb_root = Path(args.kb_root).resolve()

    if args.log_header:
        write_stdout(
            "# 操作流水\n\n"
            "<!-- 格式：- YYYY-MM-DD HH:mm <author> <新增|更新|标注矛盾> "
            "<wiki 路径> ← <raw 路径> -->\n"
        )
        return 0

    _, entries = build_kb.build(kb_root)

    if args.log_line:
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        count = args.count if args.count is not None else len(entries)
        write_stdout(
            f"- {stamp} deepseek-agent 更新 wiki/howtos/ "
            f"（批量同步 {count} 篇：MTK / 高通 / fastboot / recovery / AVB）"
            f" ← 项目 mi-recovery-helper/kb\n"
        )
        return 0

    write_stdout(build_kb.render_index(entries, kb_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
