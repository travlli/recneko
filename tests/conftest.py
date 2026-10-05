"""Shared pytest fixtures.

The project previously had no test framework at all - only four ad-hoc scripts
(``smoke_test.py``, ``verify_gui.py``, ``verify_tk_gui.py``,
``verify_entrypoints.py``) that printed PASS/FAIL and had to be run by hand in
the right order. Those are replaced by the ``tests/`` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TOOLS = ROOT / "tools"

for path in (SRC, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def kb():
    """The built knowledge base, or skip if it has not been generated."""
    from mirecovery.kb import KB

    try:
        return KB.load()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"知识库不可用（先运行 tools/build_kb.py）：{exc}")


@pytest.fixture(scope="session")
def reference_library():
    path = ROOT / "src" / "mirecovery" / "data" / "image_refs.json"
    if not path.is_file():
        pytest.skip("未生成 image_refs.json（先运行 tools/build_references.py）")
    from mirecovery.imagefeatures import ReferenceLibrary

    return ReferenceLibrary.load(path)


@pytest.fixture(scope="session")
def recognizer(reference_library):
    from mirecovery.recognize import ScreenRecognizer

    return ScreenRecognizer(reference_library)


@pytest.fixture(scope="session")
def benchmark_images() -> list[tuple[str, Path]]:
    """Augmented benchmark images as (expected_label, path)."""
    base = ROOT / "kb" / "image_refs" / "benchmark"
    if not base.is_dir():
        pytest.skip("未生成基准图（先运行 tools/make_reference_images.py）")
    samples: list[tuple[str, Path]] = []
    for label_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for image in sorted(label_dir.glob("*")):
            samples.append((label_dir.name, image))
    if not samples:
        pytest.skip("基准图为空")
    return samples


@pytest.fixture(scope="session")
def synthetic_references() -> list[tuple[str, Path]]:
    base = ROOT / "kb" / "image_refs" / "synthetic"
    if not base.is_dir():
        pytest.skip("未生成合成参考图")
    samples: list[tuple[str, Path]] = []
    for label_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for image in sorted(label_dir.glob("*")):
            samples.append((label_dir.name, image))
    return samples
