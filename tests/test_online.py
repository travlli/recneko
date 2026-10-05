"""Tests for online lookup (mirecovery.online).

These never touch the network. The point is to pin the *rules* that make online
lookup safe to ship:

* nothing is sent unless it is explicitly enabled **and** configured,
* device identifiers are masked before anything leaves the process,
* an answer with no citation is rejected rather than shown,
* the project's own issue tracker can never be cited as a source.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mirecovery.online import (
    AiConfig,
    OnlineAnswer,
    Source,
    _is_blocked,
    build_query,
    fetch_page,
    html_to_text,
    redact,
    render_answer,
    research,
    search_web,
)


# --------------------------------------------------------------------------
# Privacy
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,secret",
    [
        ("Serial number: HO70390000000355", "HO70390000000355"),
        ("IMEI 860000000000000", "860000000000000"),
        (r"C:\Users\admin\Documents\log.txt", "admin"),
        ("mail me at someone@example.com", "someone@example.com"),
        ("call 13800138000", "13800138000"),
        ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"),
    ],
)
def test_redact_masks_identifiers(raw, secret):
    out = redact(raw)
    assert secret not in out, f"未脱敏：{raw!r} -> {out!r}"


def test_redact_keeps_error_content():
    """Over-redaction must not destroy the actual error information."""
    text = "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032) [EMI] Enable DRAM Failed!"
    out = redact(text)
    assert "4032" in out
    assert "S_FT_ENABLE_DRAM_FAIL" in out


def test_redact_handles_empty():
    assert redact("") == ""


# --------------------------------------------------------------------------
# Configuration: off by default
# --------------------------------------------------------------------------


def test_config_is_disabled_by_default(tmp_path):
    config = AiConfig.load(tmp_path / "does-not-exist.json")
    assert config.enabled is False
    assert config.usable is False


def test_config_from_file(tmp_path, monkeypatch):
    for var in ("RECNEKO_AI_BASE_URL", "RECNEKO_AI_API_KEY", "RECNEKO_AI_MODEL",
                "RECNEKO_AI_ENABLED"):
        monkeypatch.delenv(var, raising=False)
    path = tmp_path / "ai.json"
    path.write_text(
        json.dumps({
            "base_url": "http://example.invalid/v1",
            "api_key": "k",
            "model": "m",
            "enabled": True,
        }),
        encoding="utf-8",
    )
    config = AiConfig.load(path)
    assert config.usable is True


def test_env_overrides_file(tmp_path, monkeypatch):
    path = tmp_path / "ai.json"
    path.write_text(json.dumps({"base_url": "http://from-file/v1"}), encoding="utf-8")
    monkeypatch.setenv("RECNEKO_AI_BASE_URL", "http://from-env/v1")
    assert AiConfig.load(path).base_url == "http://from-env/v1"


def test_research_refuses_when_disabled():
    answer = research("ERROR 4032", config=AiConfig())
    assert not answer.ok
    assert "未启用" in answer.error


def test_research_refuses_when_unconfigured():
    answer = research("ERROR 4032", config=AiConfig(enabled=True))
    assert not answer.ok
    assert "未配置" in answer.error


# --------------------------------------------------------------------------
# Query building
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,phrase",
    [
        ("BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)", '"ERROR 4032"'),
        ("error: FAILED (data transfer failure (Too many links))", '"Too many links"'),
        ("error: Antirollback check error", '"Antirollback check error"'),
        ("手机屏幕显示 press any key to shutdown", '"press any key to shutdown"'),
    ],
)
def test_build_query(text, phrase):
    """The quoted phrase must survive, plus a flashing context hint.

    Without the hint a bare phrase attracts the wrong content entirely: measured,
    `SP Flash Tool 4032` returned a Bilibili video about unpacking **Flash games**.
    """
    query = build_query(text)
    assert query.startswith(phrase)
    assert "刷机" in query, f"缺少刷机语境: {query}"


def test_build_query_adds_a_platform_hint():
    from mirecovery.scanner import analyze

    text = "BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)"
    assert "MTK" in build_query(text, analyze(text))


def test_relevance_phrase_ignores_the_hint():
    """The hint must not enter the "page must contain" phrase.

    Including it rejected every correct source, because no page writes
    "Antirollback check error 刷机" adjacently.
    """
    from mirecovery.online import relevance_phrase

    assert relevance_phrase('"Antirollback check error" 刷机') == "antirollback check error"
    assert relevance_phrase('"ERROR 4032" 刷机 MTK') == "error 4032"


def test_build_query_is_quoted():
    """Phrase search is what makes results about *this* error."""
    assert build_query("error: Antirollback check error").startswith('"')


# --------------------------------------------------------------------------
# Only Android-flashing results survive
# --------------------------------------------------------------------------
#
# Measured junk that used to reach the user: `mkdocs/issues/4032` (matched the
# number), an NVIDIA driver thread, a Cities-Skylines traffic-mod video and a
# "unpack Flash game assets" video (matched the word "flash").


@pytest.mark.parametrize(
    "title",
    [
        "Hang after drawing first frame with NVIDIA 580 drivers",
        "`mkdocs` does not watch for file changes when using `click>8.2`",
        "[视频] 天际线2更新以后的红绿灯新模组 traffic tool essentials",
        "[视频] 拆包Flash游戏导出素材，反编译以及网站下载",
        "Add durable break-glass approvals",
        "error and uncertainty",
    ],
)
def test_off_topic_results_are_dropped(title):
    from mirecovery.online import source_is_on_topic

    assert not source_is_on_topic(Source(title=title, url="https://x/1")), title


@pytest.mark.parametrize(
    "title",
    [
        "MTK刷机工具Flash_Tool部分4032错误解决办法",
        "通过SP_Flash_Tool线刷失败解决方法",
        "小米官方线刷工具miflash报错的解决方法",
        "【MTK常见错误指令】SP Flash Tool mtk手机各错误的含义及解决",
        "[视频] sp flash tool 救砖视频教学",
        "fastboot FAILED not allowed in locked state",
        "How to fix TWRP bootloop",
    ],
)
def test_on_topic_results_are_kept(title):
    from mirecovery.online import source_is_on_topic

    assert source_is_on_topic(Source(title=title, url="https://x/1")), title


def test_search_web_filters_off_topic_hits(monkeypatch):
    """Junk must not even reach the result list, let alone the model."""
    import mirecovery.online as online

    monkeypatch.setitem(
        online.BACKENDS, "github",
        lambda q, limit=6, timeout=30: [
            Source(title="`mkdocs` file watching", url="https://github.com/a/1"),
            Source(title="小米刷机报错解决", url="https://github.com/a/2"),
        ],
    )
    results = online.search_web("q", backends=("github",))
    assert [s.title for s in results] == ["小米刷机报错解决"]


def test_search_web_skips_blocked(monkeypatch):
    import mirecovery.online as online

    def fake_github(query, limit=6, timeout=30):
        return [
            Source(title="刷机 自己的 issue", url="https://github.com/travlli/recneko/issues/5"),
            Source(title="小米刷机报错解决方法", url="https://github.com/x/y/issues/1"),
        ]

    monkeypatch.setitem(online.BACKENDS, "github", fake_github)
    results = search_web("test", backends=("github",))
    assert [s.title for s in results] == ["小米刷机报错解决方法"]


def test_search_web_deduplicates(monkeypatch):
    import mirecovery.online as online

    def fake(query, limit=6, timeout=30):
        return [
            Source(title="fastboot 刷机报错", url="https://example.com/x/"),
            Source(title="fastboot 刷机报错 2", url="https://example.com/x"),
        ]

    monkeypatch.setitem(online.BACKENDS, "github", fake)
    assert len(search_web("test", backends=("github",))) == 1


# --------------------------------------------------------------------------
# HTML handling
# --------------------------------------------------------------------------


def test_html_to_text_strips_markup():
    html = "<html><head><style>p{color:red}</style></head><body><p>Hello</p><p>World</p></body></html>"
    text = html_to_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "<" not in text
    assert "color:red" not in text


def test_fetch_page_failure_is_empty_not_raise():
    assert fetch_page("http://127.0.0.1:1/nothing") == ""


# --------------------------------------------------------------------------
# Grounding: no source, no answer
# --------------------------------------------------------------------------


class _StubClient:
    """A model that always returns a usable answer."""

    def __init__(self, reply="## 现象\n报错 [自身知识]\n## 排查步骤\n1. 换线 [自身知识]", tokens=7):
        self.reply = reply
        self.tokens = tokens

    def chat(self, messages, timeout=None):
        return self.reply, self.tokens


def test_research_still_answers_without_any_sources(monkeypatch):
    """The web search supplements the model; it must not gate the answer.

    An earlier version returned "no answer" whenever nothing was grounded, which
    threw the feature away exactly when it was most useful (search rate-limited or
    simply empty).
    """
    import mirecovery.online as online

    monkeypatch.setitem(online.BACKENDS, "github", lambda *a, **k: [])
    config = AiConfig(
        base_url="http://x/v1", api_key="k", model="m", enabled=True,
        backends=("github",),
    )
    answer = research("ERROR 9999", config=config, client=_StubClient())
    assert answer.ok, "没有来源就不作答了"
    assert answer.grounded is False
    assert "自身知识" in answer.text or answer.text


def test_research_answers_even_when_no_body_can_be_fetched(monkeypatch):
    import mirecovery.online as online

    monkeypatch.setitem(
        online.BACKENDS, "github",
        lambda *a, **k: [Source(title="小米刷机报错 ERROR 9999", url="https://example.com/a")],
    )
    monkeypatch.setattr(online, "fetch_page", lambda *a, **k: "")
    config = AiConfig(
        base_url="http://x/v1", api_key="k", model="m", enabled=True,
        backends=("github",),
    )
    answer = research("ERROR 9999", config=config, client=_StubClient())
    assert answer.ok
    assert answer.grounded is False
    assert "抓不到正文" in answer.error, answer.error


def test_ungrounded_answer_is_labelled(monkeypatch):
    """The user must be able to tell source-backed from model-knowledge."""
    import mirecovery.online as online

    monkeypatch.setitem(online.BACKENDS, "github", lambda *a, **k: [])
    config = AiConfig(
        base_url="http://x/v1", api_key="k", model="m", enabled=True,
        backends=("github",),
    )
    answer = research("ERROR 9999", config=config, client=_StubClient())
    rendered = render_answer(answer)
    assert "没有检索到可核对的联网来源" in rendered
    assert "自身知识" in rendered


def test_grounded_answer_is_accepted(monkeypatch):
    import mirecovery.online as online

    monkeypatch.setitem(
        online.BACKENDS, "github",
        lambda *a, **k: [Source(title="小米刷机报错 ERROR 9999", url="https://example.com/a")],
    )
    monkeypatch.setattr(
        online, "fetch_page", lambda *a, **k: "ERROR 9999 reported here. " * 30
    )
    config = AiConfig(
        base_url="http://x/v1", api_key="k", model="m", enabled=True,
        backends=("github",),
    )
    answer = research(
        "ERROR 9999", config=config,
        client=_StubClient("现象：报错 [1]\n步骤：换线 [1]", tokens=42),
    )
    assert answer.ok
    assert answer.grounded is True
    assert answer.tokens == 42
    assert answer.sources
    assert "可点开核对" in render_answer(answer)


def test_blocked_search_reports_the_reason(monkeypatch):
    """A rate limit must be named, not look like "no results anywhere"."""
    import time as _time

    import mirecovery.online as online

    def blocked(*args, **kwargs):
        raise online.SearchBlocked("360 触发频率限制")

    monkeypatch.setitem(online.BACKENDS, "web360", blocked)
    monkeypatch.setitem(online.BACKENDS, "github", lambda q, limit=6, timeout=30: [])
    monkeypatch.setattr(online, "LAST_BLOCKED_AT", _time.time())

    config = AiConfig(
        base_url="http://x/v1", api_key="k", model="m", enabled=True,
        backends=("web360", "github"),
    )
    answer = research("ERROR 9999", config=config, client=_StubClient())
    # Still answers, but says why there was nothing to check against.
    assert answer.ok
    assert answer.grounded is False
    assert "频率限制" in answer.error, answer.error


def test_render_answer_failure_lists_why():
    text = render_answer(OnlineAnswer(error="没有搜到可引用的资料"))
    assert "没有搜到可引用的资料" in text


def test_render_answer_success_includes_sources():
    answer = OnlineAnswer(
        ok=True,
        text="现象：x [1]",
        sources=[Source(title="标题", url="https://example.com/a")],
        model="m",
        tokens=5,
    )
    text = render_answer(answer)
    assert "https://example.com/a" in text
    assert "5 tokens" in text


# --------------------------------------------------------------------------
# Search backends: more than GitHub
# --------------------------------------------------------------------------
#
# The first version only searched GitHub because that was the only backend that
# worked when it was written. Re-measured: 360 (so.com) handles multi-word queries
# correctly and reaches Coolapk content; Bilibili's search API works once a
# `buvid3` cookie is bootstrapped (without it: HTTP 412); XDA answers 403.


def test_default_backends_cover_more_than_github():
    from mirecovery.online import DEFAULT_BACKENDS

    assert "github" in DEFAULT_BACKENDS
    assert "web360" in DEFAULT_BACKENDS, "通用网页搜索没有启用"
    assert len(DEFAULT_BACKENDS) >= 3


def test_all_backends_are_registered():
    from mirecovery.online import BACKENDS

    for name in ("github", "web360", "csdn", "coolapk", "tieba", "zhihu",
                 "bilibili", "xda", "bing"):
        assert name in BACKENDS, f"缺少后端 {name}"


def test_new_sites_are_enabled_by_default():
    from mirecovery.online import DEFAULT_BACKENDS

    for name in ("csdn", "tieba", "zhihu"):
        assert name in DEFAULT_BACKENDS, f"{name} 没有启用"


def test_csdn_parses_its_own_api():
    """CSDN 的搜索页是 JS 壳，所以走它自己的 JSON 接口。"""
    from mirecovery.online import _parse_csdn_payload

    payload = {"result_vos": [{
        "title": "MTK刷机工具Flash_Tool部分4032错误解决办法",
        "url": "https://blog.csdn.net/qsw15923/article/details/77398668",
        "digest": "先换一根数据线试试。",
        "author": "qsw15923",
    }]}
    results = _parse_csdn_payload(payload, limit=5)
    assert len(results) == 1
    assert results[0].origin == "csdn"
    assert "4032" in results[0].title
    assert "qsw15923" in results[0].snippet


def test_csdn_parser_skips_entries_without_a_url():
    from mirecovery.online import _parse_csdn_payload

    assert _parse_csdn_payload({"result_vos": [{"title": "没有链接", "url": ""}]}, 5) == []


def test_antibot_page_is_detected():
    """验证码页不能看起来像"这个报错没有结果"。"""
    from mirecovery.online import _looks_like_antibot

    captcha = "<html><head><title>访问异常页面</title></head><body>请完成安全验证</body></html>"
    assert _looks_like_antibot(captcha)
    block = '<li class="res-list">x</li>'
    real = "<html><body>" + (block * 500) + "</body></html>"
    assert not _looks_like_antibot(real)


def test_via_360_backends_are_declared():
    """哪些后端共用同一条会被限流的通道，要写清楚。"""
    from mirecovery.online import BACKENDS, VIA_360

    for name in VIA_360:
        assert name in BACKENDS
    assert "csdn" not in VIA_360, "CSDN 有自己的 API，不依赖 360"


def test_360_parser_extracts_results():
    from mirecovery.online import _parse_360

    html = """
    <li class="res-list">
      <h3><a href="https://www.so.com/link?m=x" data-mdurl="https://blog.csdn.net/a/1">MTK刷机4032错误解决办法</a></h3>
      <p class="res-desc">先说结论：换数据线。</p>
    </li>
    """
    results = _parse_360(html, limit=5, origin="web360")
    assert len(results) == 1
    assert results[0].url == "https://blog.csdn.net/a/1", "应使用真实地址而非跳转链接"
    assert "4032" in results[0].title
    assert results[0].origin == "web360"


def test_360_parser_drops_the_engines_own_widgets():
    """360 injects its own AI/translation boxes as results; they are not sources."""
    import urllib.parse as _urlparse

    from mirecovery.online import _parse_360

    html = """
    <li class="res-list">
      <h3><a href="https://ai.so.com/search/so123">can not found file 是什么意思</a></h3>
      <p class="res-desc">AI 回答</p>
    </li>
    <li class="res-list">
      <h3><a href="https://fanyi.so.com/?src=onebox#x">在线翻译</a></h3>
      <p class="res-desc">翻译</p>
    </li>
    <li class="res-list">
      <h3><a href="https://www.coolapk.com/feed/35606610">小米官方线刷工具报错的解决方法</a></h3>
      <p class="res-desc">真实来源</p>
    </li>
    """
    results = _parse_360(html, limit=5, origin="web360")
    hosts = [_urlparse.urlparse(s.url).netloc for s in results]
    assert hosts == ["www.coolapk.com"], f"没有过滤掉搜索引擎自带页面: {hosts}"


def test_search_web_interleaves_backends(monkeypatch):
    """Every backend must get a turn; the first one must not take every slot."""
    import mirecovery.online as online

    monkeypatch.setitem(
        online.BACKENDS, "github",
        lambda q, limit=6, timeout=30: [
            Source(title=f"刷机报错 {i}", url=f"https://github.com/x/{i}", origin="github")
            for i in range(5)
        ],
    )
    monkeypatch.setitem(
        online.BACKENDS, "web360",
        lambda q, limit=6, timeout=30: [
            Source(title="fastboot 刷机 web0", url="https://example.com/a", origin="web360")
        ],
    )
    results = online.search_web("q", backends=("github", "web360"), limit=4)
    origins = [s.origin for s in results]
    assert origins[0] == "github"
    assert origins[1] == "web360", f"第二个后端没有拿到名额: {origins}"


def test_search_web_survives_a_broken_backend(monkeypatch):
    import mirecovery.online as online

    def boom(q, limit=6, timeout=30):
        raise RuntimeError("network exploded")

    monkeypatch.setitem(online.BACKENDS, "web360", boom)
    monkeypatch.setitem(
        online.BACKENDS, "github",
        lambda q, limit=6, timeout=30: [
            Source(title="刷机报错 ok", url="https://github.com/x/1")
        ],
    )
    results = online.search_web("q", backends=("web360", "github"))
    assert [s.title for s in results] == ["刷机报错 ok"]


def test_bilibili_results_are_labelled_as_video():
    """Only titles/descriptions are readable, so they must be marked as videos."""
    from mirecovery.online import search_bilibili

    results = search_bilibili("SP Flash Tool 4032", limit=3)
    if not results:
        pytest.skip("B 站不可达（网络受限）")
    for source in results:
        assert source.title.startswith("[视频]"), source.title
        assert "bilibili.com/video/" in source.url
        assert source.origin == "bilibili"


def test_site_search_helper_builds_a_site_query(monkeypatch):
    """Coolapk/XDA go through the engine's index with a site: operator."""
    import mirecovery.online as online

    seen: list[str] = []

    def fake_get(url, timeout=30, referer=""):
        seen.append(url)
        return (
            '<li class="res-list"><h3><a href="https://www.coolapk.com/feed/1" '
            'data-mdurl="https://www.coolapk.com/feed/1">酷安帖子</a></h3></li>'
        )

    monkeypatch.setattr(online, "_browser_get", fake_get)
    results = online._site_search("刷机 4032", "coolapk.com", "coolapk", 5, 30)
    assert "site%3Acoolapk.com" in seen[0] or "site:coolapk.com" in seen[0]
    assert results and results[0].origin == "coolapk"


# --------------------------------------------------------------------------
# Settings persistence (the dialog writes through these)
# --------------------------------------------------------------------------


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "ai.json"
    config = AiConfig(
        base_url="http://localhost:1234/v1",
        api_key="secret",
        model="m",
        enabled=True,
    )
    saved = config.save(path)
    assert saved == path
    loaded = AiConfig.load(path)
    assert loaded.base_url == "http://localhost:1234/v1"
    assert loaded.api_key == "secret"
    assert loaded.model == "m"
    assert loaded.enabled is True
    assert loaded.usable is True


def test_save_falls_back_when_preferred_is_unwritable(tmp_path, monkeypatch):
    """A read-only profile must not make the settings dialog fail silently."""
    import mirecovery.online as online

    good = tmp_path / "fallback" / "ai.json"
    monkeypatch.setattr(
        online, "config_candidates", lambda: [Path("Z:/definitely/not/writable/ai.json"), good]
    )
    saved = AiConfig(base_url="http://x/v1", api_key="k", model="m").save()
    assert saved == good
    assert good.is_file()


def test_save_reports_failure_instead_of_pretending(tmp_path, monkeypatch):
    import mirecovery.online as online

    monkeypatch.setattr(
        online, "config_candidates", lambda: [Path("Z:/definitely/not/writable/ai.json")]
    )
    with pytest.raises(OSError):
        AiConfig(base_url="http://x/v1", api_key="k", model="m").save()


def test_env_vars_win_over_saved_file(tmp_path, monkeypatch):
    path = tmp_path / "ai.json"
    AiConfig(base_url="http://from-file/v1", api_key="k", model="m").save(path)
    monkeypatch.setenv("RECNEKO_AI_BASE_URL", "http://from-env/v1")
    assert AiConfig.load(path).base_url == "http://from-env/v1"


# --------------------------------------------------------------------------
# Connection test (the "测试连接" button)
# --------------------------------------------------------------------------


def test_connection_validates_required_fields():
    from mirecovery.online import test_connection

    ok, message = test_connection(AiConfig())
    assert not ok and "API 地址" in message

    ok, message = test_connection(AiConfig(base_url="ftp://x"))
    assert not ok and "http" in message

    ok, message = test_connection(AiConfig(base_url="http://x/v1"))
    assert not ok and "API Key" in message

    ok, message = test_connection(AiConfig(base_url="http://x/v1", api_key="k"))
    assert not ok and "模型名" in message


def test_connection_reports_success(monkeypatch):
    import mirecovery.online as online

    monkeypatch.setattr(
        online.AiClient, "chat", lambda self, messages, timeout=None: ("可用", 12)
    )
    ok, message = online.test_connection(
        AiConfig(base_url="http://x/v1", api_key="k", model="m")
    )
    assert ok
    assert "可用" in message


def test_connection_handles_401(monkeypatch):
    import urllib.error

    import mirecovery.online as online

    def boom(self, messages, timeout=None):
        raise urllib.error.HTTPError("http://x", 401, "unauthorized", {}, None)

    monkeypatch.setattr(online.AiClient, "chat", boom)
    ok, message = online.test_connection(
        AiConfig(base_url="http://x/v1", api_key="bad", model="m")
    )
    assert not ok
    assert "401" in message


def test_connection_handles_unreachable(monkeypatch):
    import urllib.error

    import mirecovery.online as online

    def boom(self, messages, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(online.AiClient, "chat", boom)
    ok, message = online.test_connection(
        AiConfig(base_url="http://127.0.0.1:1/v1", api_key="k", model="m")
    )
    assert not ok
    assert "连不上" in message


def test_connection_treats_reasoning_only_reply_as_success(monkeypatch):
    """A reasoning model may return no text but still prove the endpoint works."""
    import mirecovery.online as online

    monkeypatch.setattr(
        online.AiClient, "chat", lambda self, messages, timeout=None: ("", 16)
    )
    ok, message = online.test_connection(
        AiConfig(base_url="http://x/v1", api_key="k", model="m")
    )
    assert ok
    assert "16" in message


# --------------------------------------------------------------------------
# Relevance filtering: junk sources must never reach the model
# --------------------------------------------------------------------------
#
# Measured with a real endpoint: searching `"remote: Check device console"`
# returned cordova-android / ionic-framework / html5-qrcode threads, because
# GitHub's search matches the words loosely. Handing those to the model cost
# ~7000 tokens and produced "资料不足" - an expensive way to learn nothing.


def test_relevance_accepts_page_that_quotes_the_error():
    from mirecovery.online import relevance_phrase, source_is_relevant

    phrase = relevance_phrase('"Too many links" fastboot')
    page = "fastboot boot fails with FAILED (Status read failed (Too many links))"
    assert source_is_relevant(page, phrase)


def test_relevance_rejects_unrelated_pages():
    from mirecovery.online import relevance_phrase, source_is_relevant

    phrase = relevance_phrase('"remote: Check device console"')
    for junk in [
        "Content-security-policy bug in cordova-android",
        "Toast - No component factory found in production",
        "CORS in IONIC4 apk",
    ]:
        assert not source_is_relevant(junk, phrase), junk


def test_relevance_rejects_page_sharing_only_common_words():
    """The word-based filter passed these; the phrase-based one must not."""
    from mirecovery.online import relevance_phrase, source_is_relevant

    phrase = relevance_phrase('"remote: Check device console"')
    page = (
        "This device will check the remote server console output and report "
        "any error it finds while checking the device."
    )
    assert not source_is_relevant(page, phrase)


def test_relevance_handles_empty_phrase():
    from mirecovery.online import source_is_relevant

    assert source_is_relevant("anything", "")


def test_junk_sources_are_dropped_before_calling_the_model(monkeypatch):
    """A page that does not mention the error means no model call at all.

    The title is on-topic on purpose, so the hit survives the *topic* filter and
    is rejected later by the *phrase* filter - that is the layer under test here.
    """
    import mirecovery.online as online

    monkeypatch.setitem(
        online.BACKENDS,
        "github",
        lambda *a, **k: [
            Source(title="小米刷机 通用教程", url="https://example.com/junk")
        ],
    )
    monkeypatch.setattr(online, "fetch_page", lambda *a, **k: "cordova policy " * 60)

    calls = {"n": 0}

    class CountingClient:
        def chat(self, messages, timeout=None):
            calls["n"] += 1
            return "x [1]", 100

    config = AiConfig(
            base_url="http://x/v1", api_key="k", model="m", enabled=True,
            # Pin the backend: the default set now includes real web
            # backends, which would make these tests hit the network.
            backends=("github",),
        )
    answer = research(
        "error: Check device console", config=config, client=CountingClient()
    )
    # It still answers (from the model's own knowledge), but the off-topic page was
    # never passed in as evidence - so the prompt carried no material.
    assert answer.ok
    assert answer.grounded is False
    assert "没有一个真正提到" not in (answer.error or "")
    assert "没提到这个报错" in answer.error, answer.error
    assert answer.tokens == 100
