#!/usr/bin/env python3
"""Pre-build hook: make sure the bundled knowledge base is up to date.

Called by the CI workflow before packaging, and safe to run locally:

    python tools/ci_prepare.py

It (re)generates ``kb.json`` from the wiki pages so the exe/apk never ship a
stale knowledge base.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import build_kb  # noqa: E402


def main() -> int:
    result = build_kb.main([])
    if result != 0:
        return result

    data_file = PROJECT_ROOT / "src" / "mirecovery" / "data" / "kb.json"
    if not data_file.is_file():
        print(f"[ci_prepare] ERROR: {data_file} 未生成", file=sys.stderr)
        return 1

    size = data_file.stat().st_size
    print(f"[ci_prepare] kb.json 就绪（{size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
