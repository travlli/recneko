"""Text-recognition (OCR) tests.

Measured reality that these encode:

* Backend selection must prefer the best available engine and never crash when
  none is installed - the built-in template matcher is the last resort and is the
  only one that can exist in the apk (Chaquopy has no Tesseract and no
  onnxruntime).
* The built-in matcher's single-character accuracy is good only because the
  template set renders each glyph at many sizes. With single-size templates the
  same character at another size correlated at just 0.76, and a *wrong* glyph
  often outscored the right one (digits 91.5%, whole 4-digit codes 70%). The
  size sweep lifted those to 99.6% / 99.5%; a regression test guards it.
* OCR look-alikes ("fai1ed", "a110wed") must be folded before keyword search,
  and numeric tokens must survive untouched.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw, ImageFont

from mirecovery.ocr import (
    CHAR_HEIGHT,
    CHAR_WIDTH,
    TEMPLATE_VERSION,
    TemplateSet,
    available_backends,
    clean_text,
    extract_error_codes,
    keywords_from_text,
    normalize_confusions,
    normalize_glyph,
    recognize_text,
)

FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


def _font(size: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    pytest.skip("没有可用的 TrueType 字体")


def render_line(text: str, size: int = 24, bg=(255, 255, 255), fg=(20, 20, 20)) -> Image.Image:
    font = _font(size)
    box = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), text, font=font)
    image = Image.new("RGB", (max(80, box[2] + 40), max(40, box[3] + 30)), bg)
    ImageDraw.Draw(image).text((20, 15), text, font=font, fill=fg)
    return image


# --------------------------------------------------------------------------
# Backend plumbing
# --------------------------------------------------------------------------


def test_some_backend_is_always_available():
    """There must always be something to fall back on."""
    assert available_backends(), "没有任何可用 OCR 后端"


def test_builtin_templates_exist_and_match_version():
    assert TemplateSet.load().charset, "内置字形模板为空"
    import json

    from mirecovery.ocr import TEMPLATES_PATH

    payload = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    assert payload["template_version"] == TEMPLATE_VERSION


def test_builtin_templates_cover_the_size_range():
    """Regression: single-size templates break cross-size matching."""
    import json

    from mirecovery.ocr import TEMPLATES_PATH

    payload = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    sizes = payload.get("sizes") or []
    assert len(sizes) >= 4, (
        f"模板只渲染了 {sizes}；单一字号会让同一字符在不同字号下只有约 0.76 "
        "相关度，导致错误字形胜出（实测数字 91.5%、整串 70%）"
    )


def test_forced_backend_and_unknown_backend():
    image = render_line("ERROR 4032")
    result = recognize_text(image, backend="builtin")
    assert result.backend == "builtin"
    # An unknown name must not raise.
    assert isinstance(recognize_text(image, backend="nope-not-a-backend"), type(result))


def test_blank_image_reports_no_text():
    result = recognize_text(Image.new("RGB", (400, 120), (255, 255, 255)))
    assert not result.ok


def test_min_confidence_suppresses_low_quality():
    result = recognize_text(render_line("ERROR 4032"), min_confidence=0.999)
    assert not result.ok or result.confidence >= 0.999


# --------------------------------------------------------------------------
# Built-in matcher quality
# --------------------------------------------------------------------------


def _glyph(ch: str, font) -> list[float] | None:
    size = getattr(font, "size", 24) or 24
    canvas = Image.new("L", (size * 3, size * 3), 255)
    ImageDraw.Draw(canvas).text((size, size), ch, font=font, fill=0)
    bbox = canvas.point(lambda v: 255 - v).getbbox()
    if bbox is None:
        return None
    return normalize_glyph(canvas.crop(bbox))


def test_builtin_digit_accuracy():
    """Digits are the highest-value target: they carry the error codes."""
    templates = TemplateSet.load()
    digits = "0123456789"
    correct = total = 0
    for size in (14, 18, 22, 28, 34):
        font = _font(size)
        for ch in digits:
            values = _glyph(ch, font)
            if values is None:
                continue
            got, _ = templates.match(values, charset=digits)
            total += 1
            if got == ch:
                correct += 1
    accuracy = correct / total
    assert accuracy >= 0.85, f"数字识别准确率过低：{accuracy:.1%}"


def test_glyph_grid_dimensions():
    font = _font(24)
    values = _glyph("A", font)
    assert values is not None
    assert len(values) == CHAR_WIDTH * CHAR_HEIGHT


# --------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("fai1ed to mount /data", "failed to mount /data"),
        ("a110wed in locked state", "allowed in locked state"),
        ("dm-verity corruption", "dm-verity corruption"),
    ],
)
def test_confusions_are_folded(raw, expected):
    assert normalize_confusions(raw) == expected


@pytest.mark.parametrize("code", ["ERROR 4032", "4004", "(4032)", "2004 3004"])
def test_numeric_tokens_survive_normalisation(code):
    """An error code must never be corrupted by the look-alike folding."""
    assert normalize_confusions(code) == code


def test_extract_error_codes():
    assert extract_error_codes("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)") == ["4032"]
    assert extract_error_codes("ERROR 4004 and ERROR 2004") == ["4004", "2004"]
    assert extract_error_codes("nothing here") == []


def test_keywords_from_text():
    words = keywords_from_text("E:fai1ed to mount /data")
    assert "failed" in words
    assert "mount" in words
    assert all(len(word) >= 4 for word in words)


def test_clean_text_drops_unknown_glyphs():
    assert "?" not in clean_text("ERROR ?032")


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


def test_reads_error_code_from_a_rendered_line():
    """The single most valuable thing OCR does for this app."""
    result = recognize_text(render_line("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"))
    if not result.ok:
        pytest.skip(f"本环境 OCR 不可用：{result.error}")
    assert "4032" in result.text


def test_reads_light_text_on_dark_background():
    """Recovery screens are light-on-dark; polarity must not be assumed."""
    image = render_line(
        "E:failed to mount /data", bg=(8, 8, 10), fg=(240, 80, 80)
    )
    result = recognize_text(image)
    if not result.ok:
        pytest.skip(f"本环境 OCR 不可用：{result.error}")
    normalised = normalize_confusions(clean_text(result.text)).lower()
    assert "mount" in normalised or "data" in normalised


def test_image_pipeline_hits_the_right_kb_entry(kb, recognizer):
    """OCR text must drive the KB search, not just be displayed."""
    from mirecovery.report import analyze_image

    if "windows" not in available_backends() and "tesseract" not in available_backends():
        pytest.skip("需要真实 OCR 后端")

    import tempfile
    from pathlib import Path

    cases = [
        ("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)", "mtk-spflash-error-4032-4004-4008"),
        ("E:failed to mount /data", "recovery-cant-load-android-system"),
        ("ERROR: Sahara Fail", "qualcomm-sahara-firehose-error"),
        ("dm-verity corruption", "avb-verified-boot-corruption"),
    ]
    for text, expect_slug in cases:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.png"
            render_line(text).save(path)
            analysis = analyze_image(kb, recognizer, path)
            assert analysis.ocr is not None and analysis.ocr.ok, f"OCR 失败: {text}"
            assert analysis.entry is not None, f"未命中知识库: {text}"
            assert analysis.entry.slug == expect_slug, (
                f"{text!r} -> {analysis.entry.slug}（期望 {expect_slug}）"
            )


# --------------------------------------------------------------------------
# The "no fault visible" gate
# --------------------------------------------------------------------------

# Real downloaded screenshots drove this: a plain fastboot screen (device info
# only) matched a KB page at score 72.7, an update-progress screen at 16.6, and a
# bare "FASTBOOT" logo at 10.6 - none contained an error, yet all three were
# handed a flashing procedure. Handing out a repair route for a screen with no
# fault is the worst thing this app can do.


@pytest.mark.parametrize(
    "text",
    [
        "ERROR 4032",
        "FAILED (remote: not allowed in locked state)",
        "E:failed to mount /data",
        "dm-verity corruption",
        "无法开机 刷机失败",
        "校验失败",
    ],
)
def test_looks_like_error_accepts_real_errors(text):
    from mirecovery.ocr import looks_like_error

    is_error, hits = looks_like_error(text)
    assert is_error, f"未识别为报错：{text!r}"
    assert hits


@pytest.mark.parametrize(
    "text",
    [
        # A normal fastboot screen: UI labels only.
        "fastbootd Android fastboot Product name - device bootloader version unknown "
        "Baseband version Serial number Secure Boot - yes Use volume up/down and power",
        "FASTBOOT",
        "Android 14 0/30",
        "",
        "0n0 0 | 0",
    ],
)
def test_looks_like_error_rejects_normal_screens(text):
    from mirecovery.ocr import looks_like_error

    is_error, _ = looks_like_error(text)
    assert not is_error, f"误判为报错：{text!r}"


def test_no_fault_screen_gets_no_solution(kb, recognizer):
    """A screen with no error text must not be handed a repair procedure."""
    from mirecovery.report import analyze_image

    if "windows" not in available_backends() and "tesseract" not in available_backends():
        pytest.skip("需要真实 OCR 后端")

    import tempfile
    from pathlib import Path

    # Mimics the real fastboot screen that produced a false 72.7 match.
    screen = render_line(
        "fastbootd  Product name - device  bootloader version - unknown  "
        "Secure Boot - yes  Use volume up/down and power"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fastboot.png"
        screen.save(path)
        analysis = analyze_image(kb, recognizer, path)
        assert analysis.entry is None, (
            f"没有报错的画面却给出了方案：{analysis.entry.slug}"
        )
        assert "没有发现报错" in analysis.text


def test_low_score_match_is_not_presented(kb, recognizer):
    """A match below the score floor must be demoted to a suggestion."""
    from mirecovery.report import MIN_IMAGE_MATCH_SCORE, analyze_image

    if "windows" not in available_backends() and "tesseract" not in available_backends():
        pytest.skip("需要真实 OCR 后端")

    import tempfile
    from pathlib import Path

    # "ERROR" alone is error-like but matches almost nothing.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "weak.png"
        render_line("ERROR").save(path)
        analysis = analyze_image(kb, recognizer, path)
        if analysis.matches:
            top = analysis.matches[0]
            if top.score < MIN_IMAGE_MATCH_SCORE:
                assert analysis.entry is None, (
                    f"分数 {top.score} 低于门槛 {MIN_IMAGE_MATCH_SCORE} 却被当成结论"
                )
