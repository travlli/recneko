"""Report rendering and the entry-point / packaging contracts."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from mirecovery.report import build_report, empty_report, recognition_report


# --------------------------------------------------------------------------
# Text reports
# --------------------------------------------------------------------------


def test_empty_report_mentions_both_inputs():
    text = empty_report()
    assert "日志" in text
    assert "图片" in text


def test_build_report_renders_solution(kb):
    finding, matches, text = build_report(kb, "ERROR 4032", limit=3)
    assert finding.platform == "mtk"
    assert matches
    assert "诊断结果" in text
    assert "匹配到的解决方案" in text
    assert "4032" in text


def test_build_report_handles_no_match(kb):
    _, matches, text = build_report(kb, "zzzz qqqq unrelated", limit=3)
    assert isinstance(text, str) and text


def test_platform_line_is_not_contradictory(kb):
    """Regression: the report said "未能判定" and then gave an MTK solution."""
    _, _, text = build_report(kb, "ERROR 4032", limit=3)
    assert "未能判定" not in text.split("识别到错误码")[0]


def test_recognition_report_includes_solution(kb, recognizer, synthetic_references):
    label, path = synthetic_references[0]
    result = recognizer.recognize_path(path)
    entry, text = recognition_report(kb, result)
    assert "图片识别结果" in text
    if result.matched:
        assert entry is not None, f"匹配到 {result.kb_slug} 但知识库里没有该页面"
        assert "对应解决方案" in text


# --------------------------------------------------------------------------
# Entry point / frozen-build contracts
# --------------------------------------------------------------------------

ENTRY_POINT = "launcher.py"


def test_launcher_uses_absolute_imports(project_root):
    """PyInstaller runs the entry script as __main__ with no parent package.

    A relative import there fails with "attempted relative import with no known
    parent package" - which is exactly how the first packaged build died.
    """
    source = (project_root / "src" / ENTRY_POINT).read_text(encoding="utf-8")
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        assert not (stripped.startswith("from .") or stripped.startswith("import .")), (
            f"src/{ENTRY_POINT}:{number} 使用了相对导入，打包后会启动失败"
        )


def test_launcher_executes_as_main(project_root, monkeypatch):
    """Exec the launcher the way PyInstaller does, with both GUIs stubbed."""
    import mirecovery.app as toga_module
    import mirecovery.tkapp as tk_module

    reached = {"toga": False, "tk": False}
    monkeypatch.setattr(toga_module, "run", lambda *a, **k: reached.__setitem__("toga", True))
    monkeypatch.setattr(tk_module, "run", lambda *a, **k: reached.__setitem__("tk", True))
    monkeypatch.setenv("MIRECOVERY_GUI", "tk")

    # The launcher ends with `raise SystemExit(main())`, exactly like a real
    # entry point, so the SystemExit is expected and its code must be 0.
    with pytest.raises(SystemExit) as info:
        runpy.run_path(str(project_root / "src" / ENTRY_POINT), run_name="__main__")
    assert info.value.code == 0
    assert reached["tk"] or reached["toga"]


def test_specs_use_shared_config(project_root):
    """Regression: three specs duplicated config and drifted twice."""
    for name in (
        "MiRecoveryHelper-tk.spec",
        "MiRecoveryHelper-tk.onedir.spec",
        "MiRecoveryHelper.spec",
        "MiRecoveryHelper.selftest.spec",
    ):
        text = (project_root / name).read_text(encoding="utf-8")
        assert "spec_common" in text, f"{name} 没有使用公共配置，会再次漂移"
        assert "launcher.py" in text or "frozen_selftest.py" in text
        assert 'mirecovery" / "__main__.py"' not in text


def test_specs_declare_version_info(project_root):
    """Regression: the exe had no version resource at all."""
    for name in (
        "MiRecoveryHelper-tk.spec",
        "MiRecoveryHelper-tk.onedir.spec",
        "MiRecoveryHelper.spec",
    ):
        text = (project_root / name).read_text(encoding="utf-8")
        assert "version_file" in text, f"{name} 未声明版本信息"


def test_no_build_time_env_hack(project_root):
    """Regression: a spec set os.environ, which cannot affect the built exe."""
    for name in ("MiRecoveryHelper-tk.spec", "MiRecoveryHelper-tk.onedir.spec"):
        text = (project_root / name).read_text(encoding="utf-8")
        assert "os.environ[" not in text, f"{name} 里的 os.environ 是空操作"


def test_buildcfg_is_importable(project_root):
    """The generated build config must exist so the launcher can read it."""
    sys.path.insert(0, str(project_root / "src"))
    import mirecovery._buildcfg as cfg

    assert cfg.DEFAULT_GUI in ("tk", "toga", None)


def test_spec_common_writes_version_file(project_root):
    import spec_common

    version = spec_common.app_version(project_root)
    assert version != "0.0.0"
    path = spec_common.version_file(project_root)
    assert path is not None
    assert "VSVersionInfo" in Path(path).read_text(encoding="utf-8")
    assert version in Path(path).read_text(encoding="utf-8")


def test_spec_common_requires_kb(project_root):
    import spec_common

    datas = spec_common.data_files(project_root)
    assert any(dest == "mirecovery/data" for _, dest in datas)


def test_excludes_keep_numpy_out(project_root):
    """numpy is intentionally excluded; the prefilter is what makes that OK."""
    import spec_common

    assert "numpy" in spec_common.excludes(with_toga=False)
    assert "numpy" in spec_common.excludes(with_toga=True)
    assert "toga_winforms" in spec_common.excludes(with_toga=False)
