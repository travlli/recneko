"""Screen-recognition tests.

Covers the properties that matter and the defects that were found:

* a reference library with a mismatched feature version must be refused, not
  silently used (missing thumbnails make 68% of the weighting a constant);
* flat / blank images must be declined rather than force-matched;
* whatever the recogniser *accepts* must be correct - precision over coverage;
* the two-stage prefilter must not change conclusions.
"""

from __future__ import annotations

import json

import pytest
from PIL import Image

from mirecovery.imagefeatures import (
    FEATURE_VERSION,
    Features,
    Reference,
    ReferenceLibrary,
    cheap_score,
    extract,
    similarity,
)
from mirecovery.recognize import (
    MIN_STRUCTURE,
    ScreenRecognizer,
    load_default_recognizer,
)


# --------------------------------------------------------------------------
# Library versioning
# --------------------------------------------------------------------------


def test_library_reports_current_version(reference_library):
    assert reference_library.version == FEATURE_VERSION


def test_mismatched_version_is_skipped(tmp_path, reference_library):
    """Regression: version was never checked.

    A v1 library (no ZNCC thumbnails) loaded without complaint; every ZNCC
    component then returned a constant 0.5 and the recogniser still answered.
    """
    raw = {
        "feature_version": 1,
        "references": [r.to_dict() for r in reference_library.references],
    }
    bad = tmp_path / "v1.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")

    recognizer, message = load_default_recognizer([bad])
    # It may fall back to the bundled (correct) library, but it must SAY so.
    assert "特征版本不匹配" in message or recognizer is None


def test_only_one_class_available_declines():
    """With nothing to compare against, the recogniser must not claim certainty."""
    entry = Reference(
        label="only",
        title="唯一类别",
        kb_slug="x",
        source="synthetic",
        features=extract(Image.new("RGB", (300, 600), (20, 40, 90))),
    )
    recognizer = ScreenRecognizer(ReferenceLibrary(references=[entry]))
    # A structured but unrelated image.
    image = Image.new("RGB", (300, 600), (10, 10, 12))
    for y in range(0, 600, 20):
        for x in range(0, 300, 7):
            image.putpixel((x, y), (240, 240, 240))
    result = recognizer.recognize_image(image)
    assert not result.matched


# --------------------------------------------------------------------------
# Degenerate input
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "colour",
    [(0, 0, 0), (255, 255, 255), (18, 30, 68)],
    ids=["black", "white", "navy"],
)
def test_flat_image_declined(recognizer, colour):
    """Regression: a black frame used to be 'matched' to a dark reference."""
    result = recognizer.recognize_image(Image.new("RGB", (400, 800), colour))
    assert not result.matched
    assert result.reason


def test_low_structure_is_rejected_before_matching(recognizer):
    features = extract(Image.new("RGB", (200, 400), (0, 0, 0)))
    assert features.structure < MIN_STRUCTURE
    assert not recognizer.recognize_features(features).matched


def test_corrupt_and_missing_files(recognizer, tmp_path):
    junk = tmp_path / "not-really.png"
    junk.write_bytes(b"nope" * 100)
    assert not recognizer.recognize_path(junk).matched

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    assert not recognizer.recognize_path(empty).matched

    assert not recognizer.recognize_path(tmp_path / "absent.png").matched


def test_empty_library_returns_error():
    recognizer = ScreenRecognizer(ReferenceLibrary(references=[]))
    result = recognizer.recognize_features(Features(dhash="ffff", ahash="ffff"))
    assert not result.matched
    assert result.error == "empty library"


# --------------------------------------------------------------------------
# Accuracy / precision on the synthetic benchmark
# --------------------------------------------------------------------------


def test_precision_on_benchmark(recognizer, benchmark_images):
    """Everything accepted must be right - the core safety property.

    Measured on synthetic images only. Real-camera accuracy is unknown until
    real photos are added under kb/image_refs/user/.
    """
    accepted = correct = 0
    wrong: list[str] = []
    for expected, path in benchmark_images:
        result = recognizer.recognize_path(path)
        if result.matched:
            accepted += 1
            if result.label == expected:
                correct += 1
            else:
                wrong.append(f"{path.name}: 期望 {expected} 判为 {result.label}")

    assert not wrong, f"接受了错误结论：{wrong}"
    assert accepted > 0, "识别器对所有基准图都拒绝了，流程可能失效"
    # Coverage floor: the earlier revision reached 26/48 = 54%.
    assert accepted / len(benchmark_images) >= 0.40


def test_prefilter_preserves_conclusions(reference_library, benchmark_images):
    """The two-stage prefilter must not change what a full scan would decide."""
    from mirecovery.recognize import RERANK_LABELS, RERANK_PER_LABEL

    two_stage = ScreenRecognizer(reference_library)

    # A recogniser with the shortlist widened to the whole library.
    class FullScan(ScreenRecognizer):
        pass

    import mirecovery.recognize as rec_mod

    saved_labels, saved_per = rec_mod.RERANK_LABELS, rec_mod.RERANK_PER_LABEL
    try:
        rec_mod.RERANK_LABELS = 999
        rec_mod.RERANK_PER_LABEL = 999
        full = ScreenRecognizer(reference_library)
        mismatches = []
        for expected, path in benchmark_images:
            a = two_stage.recognize_path(path)
            b = full.recognize_path(path)
            if (a.matched, a.label) != (b.matched, b.label):
                mismatches.append(
                    f"{path.name}: 预筛={a.matched}/{a.label} 全扫={b.matched}/{b.label}"
                )
        assert not mismatches, f"预筛改变了结论：{mismatches[:5]}"
    finally:
        rec_mod.RERANK_LABELS, rec_mod.RERANK_PER_LABEL = saved_labels, saved_per


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------


def test_no_id_keyed_global_cache():
    """Regression: the vector cache was keyed by id() and never evicted.

    id() values are recycled after GC, so the cache could hand back another
    image's vector and silently produce a wrong similarity; it also grew
    without bound.
    """
    import mirecovery.imagefeatures as F

    assert not hasattr(F, "_VECTOR_CACHE")
    assert "_vec" in F.Thumb.__dataclass_fields__


def _structured(colour, bg=(10, 10, 14)) -> Image.Image:
    """A non-flat test image (flat images have zero variance -> no vector)."""
    image = Image.new("RGB", (240, 480), bg)
    for y in range(0, 480, 16):
        for x in range(0, 240, 5):
            image.putpixel((x, y), colour)
    return image


def test_thumb_vector_memo_is_per_object():
    import mirecovery.imagefeatures as F

    if F._np is None:
        pytest.skip("numpy 不可用，跳过向量 memo 检查")
    a = extract(_structured((235, 235, 240)))
    b = extract(_structured((240, 120, 40)))
    va = F._thumb_vector(a.thumb_grey)
    vb = F._thumb_vector(b.thumb_grey)
    assert va is not None and vb is not None
    assert not (va == vb).all()
    # Repeated calls return the same memo, and do not leak across objects.
    assert F._thumb_vector(a.thumb_grey) is va


def test_cheap_score_is_bounded():
    a = extract(_structured((235, 235, 240)))
    b = extract(_structured((235, 235, 240)))
    score = cheap_score(a, b)
    assert 0.0 <= score <= 1.0, f"cheap_score 越界: {score}"
    assert similarity(a, b) > 0.9
    assert similarity(a, b) <= 1.0


def test_similarity_components_are_bounded():
    """Regression: rgb_hist could contribute 3.0 (3 channels concatenated).

    That made the configured weight three times too large and let the weighted
    similarity saturate at 1.0, so the numbers in WEIGHTS did not mean what the
    comments claimed.
    """
    from mirecovery.imagefeatures import components

    a = extract(_structured((235, 235, 240)))
    b = extract(_structured((235, 235, 240)))
    for name, value in components(a, b).items():
        assert 0.0 <= value <= 1.0, f"{name} = {value} 超出 [0,1]"
    assert similarity(a, b) <= 1.0


def test_feature_roundtrip():
    """Serialise/deserialise must preserve the features (needs structure)."""
    features = extract(_structured((235, 235, 240)))
    restored = Features.from_dict(features.to_dict())
    # Thumbnails are stored quantised to bytes, so a little loss is expected.
    assert similarity(features, restored) > 0.98
    assert restored.structure == pytest.approx(features.structure, abs=1e-3)


def test_flat_image_roundtrip_stays_flat():
    """A flat image has no structure, so ZNCC is undefined and scores 0.5.

    Documenting the behaviour rather than pretending the roundtrip is exact:
    with zero variance there is nothing to correlate.
    """
    features = extract(Image.new("RGB", (120, 240), (40, 80, 160)))
    restored = Features.from_dict(features.to_dict())
    assert features.structure == 0.0
    # The thumbnails dominate the weight, and all three degrade to 0.5.
    assert 0.7 < similarity(features, restored) < 0.9
