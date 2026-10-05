"""Knowledge-base loading, retrieval and data-quality tests."""

from __future__ import annotations

import json

import pytest

from mirecovery.kb import KB, KBLoadError


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def test_load_bundled(kb):
    assert len(kb.entries) >= 15
    assert set(kb.platforms()) >= {"mtk", "qualcomm", "fastboot", "recovery"}


def test_explicit_path_is_authoritative(tmp_path):
    """Regression: a corrupt explicit path silently fell back to the bundled KB.

    ``KB.load(bad_path)`` returned the 18 bundled entries instead of failing, so
    a caller could pass a typo'd path and quietly search a different database.
    """
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(KBLoadError):
        KB.load(bad)


def test_missing_explicit_path_raises(tmp_path):
    with pytest.raises(KBLoadError):
        KB.load(tmp_path / "does-not-exist.json")


def test_strict_false_allows_fallback(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    kb = KB.load(bad, strict=False)
    assert len(kb.entries) >= 15


def test_malformed_payload_rejected(tmp_path):
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"nope": []}), encoding="utf-8")
    with pytest.raises(KBLoadError):
        KB.load(wrong)


def test_empty_library_loads(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"entries": []}), encoding="utf-8")
    kb = KB.load(empty)
    assert kb.entries == []
    assert kb.platforms() == []


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------


def test_retrieval_hits_expected_pages(kb):
    """Each pasted log should surface the right page."""
    from mirecovery.report import build_report

    cases = [
        ("ERROR 4032", "4032"),
        ("Sahara Fail", "sahara"),
        ("not allowed in locked state", "locked"),
        ("failed to mount /data", "data"),
        ("dm-verity corruption", "vbmeta"),
        ("waiting for any device", "device"),
    ]
    for log, expected in cases:
        _, matches, _ = build_report(kb, log, limit=3)
        assert matches, f"no match for {log!r}"
        blob = f"{matches[0].entry.slug} {matches[0].entry.title}".lower()
        assert expected in blob, f"{log!r} -> {matches[0].entry.slug}"


def test_search_empty_and_whitespace(kb):
    assert kb.search("") == []
    assert kb.search("   \n\t ") == []


def test_search_limit_is_respected(kb):
    assert len(kb.search("ERROR", limit=0)) == 0
    assert len(kb.search("flash", limit=2)) <= 2


def test_platform_filter(kb):
    results = kb.search("ERROR", limit=5, platform="mtk")
    assert all(m.entry.platform == "mtk" for m in results)
    assert kb.search("ERROR", limit=5, platform="symbian") == []


def test_large_input_is_handled(kb):
    """A 1 MB paste must not hang or crash."""
    text = "ERROR 4032\n" * 20000
    results = kb.search(text, limit=5)
    assert isinstance(results, list)


# --------------------------------------------------------------------------
# Regression: the real error messages from the project's issue #5
# --------------------------------------------------------------------------
#
# Real error text collected from MIUI community / XDA / TWRP threads. The issue
# measured 8/16 uncovered and, worse, that an uncovered error still produced five
# unrelated "solutions" because the search had no relevance floor.

# (error text, expected slug). Top-1 must be the right page.
REAL_COVERED = [
    ("error: couldn't find flash script", "miflash-flash-script-errors"),
    ("error: FAILED (remote: Erase is not allowed in Lock State)", "fastboot-flash-errors"),
    ("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032) [EMI] Enable DRAM Failed!", "mtk-spflash-error-4032-4004-4008"),
    ("BROM ERROR: S_FT_ENABLE_DRAM_FAIL (4032)", "mtk-spflash-error-4032-4004-4008"),
    ("Download Fail: Sahara Fail: QSaharaServer Fail: Process Fail", "qualcomm-sahara-firehose-error"),
    ("Qualcomm HS-USB QDLoader 9008 (COM3)", "qualcomm-edl-9008-enter"),
    ("E:failed to mount /data (Invalid argument)", "recovery-cant-load-android-system"),
    ("could not mount /data and unable to find crypto footer", "recovery-cant-load-android-system"),
    # Added by tools/research_kb.py from real online sources.
    ("error: Antirollback check error", "fastboot-antirollback-check-error"),
    ("error: Missmatching image and device error", "fastboot-mismatching-image-and-device"),
    ("error: FAILED (data transfer failure (Too many links))", "fastboot-data-transfer-failure-too-many-links"),
    ("can not found file flash_all_lock.bat", "miflash-flash-all-lock-bat-missing"),
    ("手机屏幕显示 press any key to shutdown", "device-press-any-key-to-shutdown"),
    ("error:Not catch checkpoint ($fastboot -s .*lock), flash is not done", "miflash-not-catch-checkpoint-flash-not-done"),
    ("error: Sending sparse 'system' 3/5 (102400 KB) FAILED (Error reading sparse file)", "fastboot-error-reading-sparse-file"),
]

# Junk and still-uncovered input. Must return NOTHING - the regression that used
# to fail (five unrelated "solutions" were printed for these).
REAL_UNMATCHED = [
    "the the the",
    "and and and",
    "今天天气不错",
    "hello world",
    "abcdef",
    "test test",
    "加载设备提示 Length cannot be less than zero",
]


@pytest.mark.parametrize("text,expected", REAL_COVERED)
def test_real_errors_hit_the_right_entry(kb, text, expected):
    matches = kb.search(text, limit=1)
    assert matches, f"未命中：{text!r}"
    assert matches[0].entry.slug == expected, f"{text!r} -> {matches[0].entry.slug}"


@pytest.mark.parametrize("text", REAL_UNMATCHED)
def test_uncovered_and_junk_input_return_nothing(kb, text):
    assert kb.search(text, limit=5) == [], f"乱答：{text!r}"


def test_stopwords_cannot_outrank_real_matches(kb):
    """Regression: "the the the" scored 228.6 while the real keyword BROM got 38.6."""
    junk = kb.search("the the the", limit=1, min_score=0)
    real = kb.search("BROM", limit=1, min_score=0)
    assert not junk, "停用词仍能拿到分数"
    assert real, "真实关键词反而不命中"


def test_relevance_threshold_sits_in_a_real_gap(kb):
    """The threshold must separate the classes, not be tuned to one example.

    Adding entries shifts every score (the token weight uses IDF), so this
    asserts the *separation* rather than exact numbers.
    """
    from mirecovery.kb import MIN_RELEVANCE

    def best(text: str) -> float:
        found = kb.search(text, limit=1, min_score=0)
        return found[0].score if found else 0.0

    lowest_hit = min(best(text) for text, _ in REAL_COVERED)
    highest_miss = max(best(text) for text in REAL_UNMATCHED)
    assert highest_miss < MIN_RELEVANCE <= lowest_hit, (
        f"阈值 {MIN_RELEVANCE} 不在间隔内：不应命中最高 {highest_miss}，"
        f"应命中最低 {lowest_hit}"
    )


@pytest.mark.parametrize(
    "query,slug",
    [
        ("ERROR 2004", "mtk-spflash-error-2004-2005-3004"),
        ("ERROR: 2004", "mtk-spflash-error-2004-2005-3004"),
        ("ERROR:2004", "mtk-spflash-error-2004-2005-3004"),
        ("ERROR : 2004", "mtk-spflash-error-2004-2005-3004"),
        ("dm-verity corruption", "avb-verified-boot-corruption"),
        # OCR splits compound words: Windows OCR reads "d m-verity corruption".
        ("d m-verity corruption", "avb-verified-boot-corruption"),
        ("E : failed to mount / data", "recovery-cant-load-android-system"),
    ],
)
def test_keyword_matching_ignores_separators(kb, query, slug):
    matches = kb.search(query, limit=1)
    assert matches, f"未命中：{query!r}"
    assert matches[0].entry.slug == slug, f"{query!r} -> {matches[0].entry.slug}"


def test_explain_distinguishes_keyword_from_token(kb):
    """`命中关键词: and` was misleading - that was a query token, not a keyword."""
    matches = kb.search("error: Antirollback check error", limit=1, min_score=0)
    assert matches
    assert matches[0].reason.startswith("命中关键词")
    assert "Antirollback" in matches[0].reason


# --------------------------------------------------------------------------
# Data quality (schema rules that nothing used to enforce)
# --------------------------------------------------------------------------


def test_every_page_has_keywords(kb):
    missing = [e.slug for e in kb.entries if not e.keywords]
    assert not missing, f"这些页面没有 keywords，无法被检索：{missing}"


def test_no_dead_wiki_links(kb):
    """Regression: three pages linked to [[fastboot-unlock-failed]].

    The page never existed (the real slug is
    ``fastboot-unlock-token-verify-failed``), and the schema's lint step that
    should have caught it was never run.
    """
    import re

    slugs = {e.slug for e in kb.entries}
    dead: dict[str, list[str]] = {}
    for entry in kb.entries:
        for link in re.findall(r"\[\[([^\]|]+)", entry.body):
            target = link.strip()
            if target and target not in slugs:
                dead.setdefault(entry.slug, []).append(target)
    assert not dead, f"死链：{dead}"


def test_every_page_has_todo_section(kb):
    """Pages should be explicit about what is unverified."""
    missing = [e.slug for e in kb.entries if not e.todo]
    assert not missing, f"缺少「待确认」小节：{missing}"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "已知缺口：全部 18 条页面的 sources 都是空的，知识库没有真实素材支撑。"
        "本用例故意保持失败以持续暴露这个问题；一旦补上真实 raw/ 素材，"
        "它会变成 XPASS，strict=True 会提醒你移除这个标记。"
    ),
)
def test_sources_are_declared(kb):
    """Every page must cite the raw material it came from (schema rule)."""
    ungrounded = [e.slug for e in kb.entries if not e.sources]
    assert not ungrounded, (
        f"{len(ungrounded)} 个条目没有 sources（内容无据）：{ungrounded[:5]}..."
    )
