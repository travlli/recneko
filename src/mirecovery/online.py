"""Online lookup: AI-assisted, source-grounded answers for errors the KB misses.

What this is for
----------------
The bundled knowledge base covers common failures, but real-world flashing
errors are long-tailed. This module lets the app look one up online: it searches,
fetches the pages it found, and asks a model to summarise **only what those pages
say**, with citations.

Design rules (these are the point of the module, not decoration)
---------------------------------------------------------------
1. **Off by default.** The app's promise is that logs and screenshots stay on the
   machine. Nothing is ever sent anywhere unless the user explicitly enables
   online lookup *and* confirms the specific request.
2. **Grounded or silent.** The model is given fetched material and told to use
   nothing else. If no source can be retrieved, or the answer cites nothing, the
   result is reported as a failure - never as a solution. A confident answer with
   no source is worse than no answer: it would be written into the KB as fact.
3. **Redacted.** Serial numbers, IMEIs, phone numbers, e-mail addresses and user
   paths are masked before anything leaves the process.
4. **Degrades quietly.** With no configuration or no network, every entry point
   returns a failure object; the offline app keeps working exactly as before.

Measured environment notes (this machine)
-----------------------------------------
* The AI endpoint is an OpenAI-compatible service; verified working.
* **Bing text search is unusable here**: multi-word queries come back as results
  for the *first* word only ("SP Flash Tool ERROR 4032" -> "SP Group"), with or
  without `+`/`%20` encoding and via both HTML and RSS. It is kept as an optional
  backend but is not trusted on its own.
* **The GitHub API works well** and is a genuinely good source for this domain -
  real issue threads and repos discuss MTK/Qualcomm/fastboot errors with exact
  strings. It is the default backend.
* XDA and similar sites answer 403 to this environment (Cloudflare), so they are
  not usable as sources here even though the pages exist.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .logsetup import get_logger

logger = get_logger(__name__)

USER_AGENT = "recneko/2.3 (+offline-first flashing-error helper)"
DEFAULT_TIMEOUT = 30

# How much material to hand the model. Long inputs cost tokens and add noise.
MAX_SOURCES = 6
MAX_SOURCE_CHARS = 6000
MAX_TOTAL_CHARS = 24000

# GitHub is the default because it is the only search backend verified to return
# relevant results from this environment.
# Backends used when the user has not chosen any.
#
# GitHub finds exact error strings in issue threads; CSDN has its own search API
# (independent of 360); 360 is the working general web search; Bilibili has
# tutorials (titles only). 酷安 / 贴吧 / 知乎 are also enabled - they reach their
# site through 360's index, which works but is the part most likely to be
# rate-limited. `xda` and `bing` are available but not default: XDA answers 403
# to this environment and Bing mangles multi-word queries.
DEFAULT_BACKENDS = (
    "github", "csdn", "web360", "coolapk", "tieba", "zhihu", "bilibili",
)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def config_path() -> Path:
    """Preferred location for the AI settings (next to the logs)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        root = Path(base) if base else Path.home() / ".config"
    return root / "rec检查喵" / "ai.json"


def config_candidates() -> list[Path]:
    """Where settings may live, best first.

    A single hard-coded path means the settings dialog silently fails to save
    whenever that directory is unwritable (locked-down profile, read-only share,
    sandbox). Same fallback idea as the log directory.
    """
    candidates = [config_path()]
    for var in ("TEMP", "TMP"):
        value = os.environ.get(var)
        if value:
            candidates.append(Path(value) / "rec检查喵" / "ai.json")
    try:
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "ai.json")
        else:
            candidates.append(Path.cwd() / "ai.json")
    except Exception:
        pass

    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


@dataclass
class AiConfig:
    """Settings for online lookup.

    Precedence: environment variable > config file > default. The API key is
    never written by the app unless the user asks, and never committed.
    """

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    enabled: bool = False
    timeout: int = DEFAULT_TIMEOUT
    max_tokens: int = 4096
    backends: tuple[str, ...] = DEFAULT_BACKENDS

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    @property
    def usable(self) -> bool:
        return self.enabled and self.configured

    @classmethod
    def load(cls, path: Path | None = None) -> "AiConfig":
        data: dict = {}
        targets = [Path(path)] if path else config_candidates()
        for target in targets:
            try:
                if target.is_file():
                    data = json.loads(target.read_text(encoding="utf-8"))
                    break
            except Exception as exc:
                logger.warning("读取 AI 配置失败（忽略）：%s", exc)
                data = {}

        def pick(env: str, key: str, default):
            value = os.environ.get(env)
            if value not in (None, ""):
                return value
            return data.get(key, default)

        backends = pick("RECNEKO_AI_BACKENDS", "backends", DEFAULT_BACKENDS)
        if isinstance(backends, str):
            backends = tuple(b.strip() for b in backends.split(",") if b.strip())

        enabled_raw = pick("RECNEKO_AI_ENABLED", "enabled", False)
        if isinstance(enabled_raw, str):
            enabled = enabled_raw.strip().lower() in ("1", "true", "yes", "on")
        else:
            enabled = bool(enabled_raw)

        return cls(
            base_url=str(pick("RECNEKO_AI_BASE_URL", "base_url", "")),
            api_key=str(pick("RECNEKO_AI_API_KEY", "api_key", "")),
            model=str(pick("RECNEKO_AI_MODEL", "model", "")),
            enabled=enabled,
            timeout=int(pick("RECNEKO_AI_TIMEOUT", "timeout", DEFAULT_TIMEOUT)),
            max_tokens=int(pick("RECNEKO_AI_MAX_TOKENS", "max_tokens", 4096)),
            backends=tuple(backends),
        )

    def save(self, path: Path | None = None) -> Path:
        """Write the settings, falling back if the preferred directory is read-only.

        Returns the path actually written. Raises the last error if no candidate
        is writable, so the settings dialog can tell the user rather than
        pretending the save worked.
        """
        payload = json.dumps(
            {
                "base_url": self.base_url,
                "api_key": self.api_key,
                "model": self.model,
                "enabled": self.enabled,
                "timeout": self.timeout,
                "max_tokens": self.max_tokens,
                "backends": list(self.backends),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n"

        targets = [Path(path)] if path else config_candidates()
        last_error: Exception | None = None
        for target in targets:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(payload, encoding="utf-8")
                try:
                    # The file holds an API key; keep it owner-only where the
                    # platform supports it.
                    target.chmod(0o600)
                except Exception:
                    pass
                return target
            except Exception as exc:
                last_error = exc
                logger.debug("写入配置失败 %s: %s", target, exc)
        raise OSError(f"无法写入配置文件（已尝试 {len(targets)} 个位置）：{last_error}")


def test_connection(config: AiConfig, timeout: int = 30) -> tuple[bool, str]:
    """Check the endpoint is reachable and the key/model work.

    Sends one very small request so the settings dialog can say "连接成功"
    instead of letting the user discover a typo on their first real lookup.
    Returns ``(ok, message)``; never raises.
    """
    if not config.base_url:
        return False, "请先填写 API 地址"
    if not config.base_url.startswith(("http://", "https://")):
        return False, "API 地址需要以 http:// 或 https:// 开头"
    if not config.api_key:
        return False, "请先填写 API Key"
    if not config.model:
        return False, "请先填写模型名"

    client = AiClient(config)
    try:
        text, tokens = client.chat(
            [{"role": "user", "content": "回复两个字：可用"}],
            timeout=timeout,
        )
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        if exc.code == 401:
            return False, f"认证失败（401）：API Key 可能不对。{detail}"
        if exc.code == 404:
            return False, (
                f"接口不存在（404）：检查 API 地址是否漏了 /v1。{detail}"
            )
        return False, f"HTTP {exc.code}：{detail}"
    except urllib.error.URLError as exc:
        return False, f"连不上：{exc.reason}（检查地址、网络或代理）"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if not text:
        # A reasoning model can spend the whole budget on thinking; that still
        # proves the endpoint and credentials work.
        if tokens:
            return True, f"连接成功（模型有响应，消耗 {tokens} tokens）"
        return False, "接口有响应但没有内容，检查模型名是否正确"
    return True, f"连接成功：模型回复「{text[:40]}」（{tokens} tokens）"


# --------------------------------------------------------------------------
# Privacy: redaction
# --------------------------------------------------------------------------

# Patterns that must not leave the machine. Order matters: longer, more specific
# patterns first so an IMEI is not half-eaten by the phone-number rule.
_REDACTIONS: tuple[tuple[str, str], ...] = (
    # e-mail
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "<email>"),
    # Windows user paths
    (r"(?i)\b[A-Z]:\\Users\\[^\\\s]+", r"<user-path>"),
    (r"(?i)/home/[^/\s]+", "<user-path>"),
    # IMEI / MEID: 15 digits, often labelled
    (r"(?i)\b(?:imei|meid)\b[\s:=]*\d{14,16}", "<imei>"),
    (r"\b\d{15}\b", "<imei>"),
    # Serial numbers: labelled, or the long hex/uppercase blobs bootloaders print
    (r"(?i)\b(?:serial(?:\s*(?:no|number))?|sn|seri\s*1\s*number)\b[\s:=]*[A-Za-z0-9]{6,}", "<serial>"),
    (r"\b[A-Z0-9]{12,20}\b", "<serial>"),
    # Phone numbers (China mobile and generic long digit runs)
    (r"(?<!\d)1[3-9]\d{9}(?!\d)", "<phone>"),
    # MAC addresses
    (r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", "<mac>"),
    # Long digit runs that are probably device ids
    (r"(?<!\d)\d{12,}(?!\d)", "<id>"),
)


def redact(text: str) -> str:
    """Mask device identifiers before sending anything off the machine.

    Over-redaction is intentional: losing a serial number costs nothing, leaking
    one is a privacy problem the user did not agree to.
    """
    if not text:
        return ""
    out = text
    for pattern, replacement in _REDACTIONS:
        out = re.sub(pattern, replacement, out)
    return out


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass
class Source:
    title: str
    url: str
    snippet: str = ""
    fetched: bool = False
    origin: str = ""

    def citation(self, index: int) -> str:
        return f"[{index}] {self.title} - {self.url}"


@dataclass
class OnlineAnswer:
    ok: bool = False
    text: str = ""
    sources: list[Source] = field(default_factory=list)
    error: str = ""
    model: str = ""
    tokens: int = 0
    queries: list[str] = field(default_factory=list)
    # Whether the answer was backed by fetched sources. An answer can be useful
    # without them (the model's own knowledge), but the user must be able to tell
    # the two apart - one is checkable, the other is not.
    grounded: bool = False
    used_own_knowledge: bool = False

    def __bool__(self) -> bool:
        return self.ok


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _http_post_json(url: str, payload: dict, timeout: int, headers: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


_TAG_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_RE = re.compile(r"\n{3,}")
_ENTITY_MAP = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&#39;": "'", "&apos;": "'", "&ensp;": " ", "&emsp;": " ",
}


def html_to_text(html: str) -> str:
    """Very small HTML-to-text conversion (the project has no bs4 dependency)."""
    text = _TAG_RE.sub(" ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = _ANY_TAG_RE.sub(" ", text)
    for entity, char in _ENTITY_MAP.items():
        text = text.replace(entity, char)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    text = _WS_RE.sub(" ", text)
    text = _BLANK_RE.sub("\n\n", text)
    return text.strip()


def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT, limit: int = MAX_SOURCE_CHARS) -> str:
    """Fetch a URL and return readable text (empty string on any failure).

    GitHub issue/PR links are fetched through the API rather than as HTML:
    measured here, ``github.com`` HTML is refused to this client while
    ``api.github.com`` works, and the API returns the discussion body as clean
    text instead of a page full of navigation chrome.
    """
    github = _github_api_url(url)
    if github:
        text = _fetch_github(github, timeout=timeout)
        if text:
            return text[:limit]

    try:
        raw = _http_get(url, timeout=timeout)
    except Exception as exc:
        logger.debug("抓取失败 %s: %s", url, exc)
        return ""
    text = html_to_text(raw) if "<" in raw[:2000] else raw
    return text[:limit]


_GITHUB_ITEM_RE = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)", re.I
)


def _github_api_url(url: str) -> str | None:
    match = _GITHUB_ITEM_RE.match(url.strip())
    if not match:
        return None
    owner, repo, number = match.groups()
    return f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"


def _fetch_github(api_url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch a GitHub issue/PR body plus its comments as plain text."""
    try:
        payload = json.loads(
            _http_get(api_url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
        )
    except Exception as exc:
        logger.debug("GitHub API 抓取失败 %s: %s", api_url, exc)
        return ""

    parts: list[str] = []
    title = payload.get("title") or ""
    if title:
        parts.append(f"# {title}")
    if payload.get("body"):
        parts.append(payload["body"])

    # Comments often hold the actual resolution ("reflash with X", "it was the
    # cable"). Without them the thread is usually just the problem statement.
    comments_url = payload.get("comments_url")
    if comments_url and (payload.get("comments") or 0) > 0:
        try:
            comments = json.loads(
                _http_get(
                    f"{comments_url}?per_page=10",
                    timeout=timeout,
                    headers={"Accept": "application/vnd.github+json"},
                )
            )
            for comment in comments[:10]:
                body = (comment.get("body") or "").strip()
                if body:
                    parts.append(f"--- 评论 ---\n{body}")
        except Exception as exc:
            logger.debug("GitHub 评论抓取失败: %s", exc)

    return "\n\n".join(parts).strip()


# --------------------------------------------------------------------------
# Search backends
# --------------------------------------------------------------------------


def search_github(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """Search GitHub issues/discussions.

    Chosen as the default backend because it is the only one verified to return
    relevant results here, and because issue threads about flashing errors quote
    the exact error strings - which is what makes a citation useful.
    """
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.github.com/search/issues?q={encoded}"
        f"&per_page={max(1, min(limit, 10))}&sort=reactions"
    )
    try:
        payload = json.loads(
            _http_get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
        )
    except Exception as exc:
        logger.debug("GitHub 搜索失败: %s", exc)
        return []

    results: list[Source] = []
    for item in payload.get("items", [])[:limit]:
        body = (item.get("body") or "").strip()
        results.append(
            Source(
                title=item.get("title") or "(无标题)",
                url=item.get("html_url") or "",
                snippet=body[:400],
                origin="github",
            )
        )
    return results


def search_bing(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """Search Bing via its RSS output.

    Kept for completeness, but **do not trust it alone**: measured here, a
    multi-word query returns results for the first word only, so the results are
    usually unrelated to the error being looked up. Callers must not treat a
    Bing-only answer as grounded.
    """
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&format=rss"
    try:
        raw = _http_get(url, timeout=timeout)
    except Exception as exc:
        logger.debug("Bing 搜索失败: %s", exc)
        return []

    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(raw)
    except Exception:
        return []

    results: list[Source] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = html_to_text(item.findtext("description") or "")
        if link:
            results.append(
                Source(title=title, url=link, snippet=description[:400], origin="bing")
            )
        if len(results) >= limit:
            break
    return results


# --------------------------------------------------------------------------
# General web search (360) and site-specific backends
# --------------------------------------------------------------------------
#
# Why these exist: the first version only searched GitHub, because that was the
# only backend that worked when it was written. Re-measured, the picture is:
#
#   GitHub API            works, good for exact error strings in issue threads
#   Bing (text)           broken here - multi-word queries come back as results
#                         for the *first word only* ("SP Flash Tool ERROR 4032"
#                         -> "SP Group"), via HTML and RSS alike
#   Baidu / DuckDuckGo /  captcha, unreachable, or merely a Bing proxy
#   Google / Ecosia
#   XDA direct            403 (Cloudflare); xda-developers.com drops the connection
#   Coolapk direct        search path 404s, api.coolapk.com 403s
#   Bilibili              search API works once a `buvid3` cookie is bootstrapped
#                         (without it: HTTP 412)
#   **360 (so.com)**      works, and handles multi-word queries correctly
#
# 360 is therefore the general-web backend, and it is also how Coolapk and XDA
# content is reached: their own search is unreachable from here, but 360 indexes
# Coolapk well (it surfaced the exact "can not found file flash_all_lock.bat"
# post). XDA is barely indexed by 360, so that backend is expected to return
# little *here* - it is still implemented, because the filtering above is a
# property of this sandbox, not of the user's machine, and a direct attempt costs
# one request before falling back.

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_BROWSER_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    # Some sites hand back gzip the stdlib will not decode for us.
    "Accept-Encoding": "identity",
}


def _browser_get(url: str, timeout: int = DEFAULT_TIMEOUT, referer: str = "") -> str:
    headers = dict(_BROWSER_HEADERS)
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


_RES_LIST_RE = re.compile(r'<li class="res-list[^"]*".*?</li>', re.S)
_RES_LINK_RE = re.compile(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_RES_DESC_RE = re.compile(r'<p class="res-desc"[^>]*>(.*?)</p>', re.S)
_RES_DATAURL_RE = re.compile(r'data-(?:mdurl|url)="([^"]+)"')


def _clean_fragment(fragment: str) -> str:
    import html as _html

    text = re.sub(r"<[^>]+>", "", fragment or "")
    return _html.unescape(text).strip()


# 360 answers inconsistently when hit several times at once - measured: the same
# `site:tieba.baidu.com ...` query returned 4 results, then 0 blocks moments later,
# while `site:zhihu.com ...` did the opposite. Four of the backends go through
# 360, so with parallel search they all arrive together. Requests are therefore
# serialised with a minimum gap, and an empty parse is retried once.
_SO360_LOCK = threading.Lock()
_SO360_LAST = 0.0
_SO360_MIN_INTERVAL = 0.7

# 360 eventually answers automated queries with an "访问异常页面" captcha. Returning
# an empty list then looks identical to "no results", which would quietly make the
# Coolapk / 贴吧 / 知乎 backends useless. The block is detected so it can be
# reported as what it is.
_ANTIBOT_MARKERS = ("访问异常", "安全验证", "请输入验证码", "captcha", "verify")
LAST_BLOCKED_AT: float = 0.0


class SearchBlocked(RuntimeError):
    """The search engine served an anti-bot page instead of results."""


def _looks_like_antibot(html: str) -> bool:
    if len(html) > 200_000:
        return False  # a real SERP is big; the captcha page is ~10 KB
    lowered = html.lower()
    return any(marker in html or marker in lowered for marker in _ANTIBOT_MARKERS)


def _so360_get(url: str, timeout: int) -> str:
    """Fetch from 360 with a global minimum gap between requests."""
    global _SO360_LAST, LAST_BLOCKED_AT
    with _SO360_LOCK:
        wait = _SO360_MIN_INTERVAL - (time.time() - _SO360_LAST)
        if wait > 0:
            time.sleep(wait)
        try:
            html = _browser_get(url, timeout=timeout)
        finally:
            _SO360_LAST = time.time()
        if _looks_like_antibot(html):
            LAST_BLOCKED_AT = time.time()
            logger.warning(
                "360 返回了访问异常页面（触发频率限制）。Coolapk / 贴吧 / 知乎 "
                "依赖 360 的索引，暂时会拿不到结果。"
            )
            raise SearchBlocked("360 触发频率限制（访问异常页面）")
        return html


def _parse_360(html: str, limit: int, origin: str) -> list[Source]:
    """Extract results from a 360 SERP.

    360 often wraps result links in a redirect (``www.so.com/link?...``). The real
    target is carried in a ``data-mdurl``/``data-url`` attribute when present, so
    that is preferred - citing a redirect URL would be useless to a reader.
    """
    results: list[Source] = []
    for block in _RES_LIST_RE.findall(html):
        link = _RES_LINK_RE.search(block)
        if not link:
            continue
        url = link.group(1)
        real = _RES_DATAURL_RE.search(block)
        if real:
            url = real.group(1)
        url = url.replace("&amp;", "&")
        title = _clean_fragment(link.group(2))
        snippet = ""
        desc = _RES_DESC_RE.search(block)
        if desc:
            snippet = _clean_fragment(desc.group(1))[:400]
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http") or not title:
            continue
        # 360 injects its own widgets (AI answers, a translation box) as results.
        # They are not sources: they have no author, cannot be cited, and fetching
        # them returns 360's chrome rather than content.
        if _is_search_engine_own(url):
            continue
        results.append(Source(title=title, url=url, snippet=snippet, origin=origin))
        if len(results) >= limit:
            break
    return results


# Hosts that are the search engine's own furniture rather than a source.
_ENGINE_OWN_HOSTS = (
    "so.com", "360.cn", "bing.com", "baidu.com", "sogou.com",
    "google.com", "googleusercontent.com", "yandex.",
)


def _is_search_engine_own(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host:
        return True
    return any(host == bad or host.endswith("." + bad) or bad in host
               for bad in _ENGINE_OWN_HOSTS)


def search_360(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """General web search via 360 (so.com)."""
    url = f"https://www.so.com/s?q={urllib.parse.quote(query)}"
    for attempt in range(2):
        try:
            html = _so360_get(url, timeout=timeout)
        except SearchBlocked:
            return []  # retrying a rate limit only makes it worse
        except Exception as exc:
            logger.debug("360 搜索失败: %s", exc)
            return []
        results = _parse_360(html, limit, "web360")
        if results or attempt:
            return results
        # 360 sometimes answers with no result blocks at all; one retry.
    return []


def _site_search(
    query: str, site: str, origin: str, limit: int, timeout: int
) -> list[Source]:
    """Search a specific site through 360's index."""
    url = f"https://www.so.com/s?q={urllib.parse.quote(f'site:{site} {query}')}"
    # Keep only the requested site: 360 sometimes pads with unrelated hits.
    keep = site.split(".")[0]

    for attempt in range(2):
        try:
            html = _so360_get(url, timeout=timeout)
        except SearchBlocked:
            return []
        except Exception as exc:
            logger.debug("%s 站内搜索失败: %s", site, exc)
            return []
        results = _parse_360(html, limit, origin)
        filtered = [
            s for s in results if keep in urllib.parse.urlparse(s.url).netloc
        ] or results
        if filtered or attempt:
            return filtered
    return []


def search_coolapk(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """酷安 (Coolapk) posts.

    Coolapk's own search is not reachable (the web path 404s and the API answers
    403), so this goes through 360's index, which covers Coolapk well. A direct
    attempt is made first in case the network allows it.
    """
    direct = f"https://www.coolapk.com/search?q={urllib.parse.quote(query)}"
    try:
        html = _browser_get(direct, timeout=min(timeout, 10))
        if len(html) > 2000:
            parsed = _parse_360(html, limit, "coolapk")
            if parsed:
                return parsed
    except Exception as exc:
        logger.debug("酷安直连失败（改走站内搜索）: %s", exc)
    return _site_search(query, "coolapk.com", "coolapk", limit, timeout)


def search_xda(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """XDA forum threads.

    Direct access answers 403 (Cloudflare) from this environment and XDA is barely
    present in 360's index, so this often returns nothing here. It is kept because
    the block is environmental: on a network that can reach XDA the direct attempt
    is what will work.
    """
    direct = f"https://xdaforums.com/search/?q={urllib.parse.quote(query)}"
    try:
        html = _browser_get(direct, timeout=min(timeout, 12))
        parsed = _parse_360(html, limit, "xda")
        if parsed:
            return parsed
    except Exception as exc:
        logger.debug("XDA 直连失败（改走站内搜索）: %s", exc)
    return _site_search(query, "xdaforums.com", "xda", limit, timeout)


_BILI_COOKIE_JAR: "http.cookiejar.CookieJar | None" = None


def _bilibili_opener():
    """An opener carrying Bilibili's bootstrap cookie.

    The search API answers HTTP 412 unless a ``buvid3`` cookie is present. Fetching
    the homepage first sets one, after which searches work - measured: 412 without,
    ``code=0`` with 20 results.
    """
    global _BILI_COOKIE_JAR
    import http.cookiejar

    if _BILI_COOKIE_JAR is None:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        try:
            request = urllib.request.Request("https://www.bilibili.com/", headers=_BROWSER_HEADERS)
            with opener.open(request, timeout=DEFAULT_TIMEOUT):
                pass
        except Exception as exc:
            logger.debug("B 站 cookie 引导失败: %s", exc)
        _BILI_COOKIE_JAR = jar
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_BILI_COOKIE_JAR))


def search_bilibili(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """Bilibili videos about the error.

    Only titles and descriptions can be read - the videos themselves cannot - so
    these are weaker sources than a written thread and are labelled as videos.
    They are still useful: searching "SP Flash Tool 4032" returns tutorials whose
    titles name the tool and the failure.
    """
    url = (
        "https://api.bilibili.com/x/web-interface/search/type"
        f"?search_type=video&keyword={urllib.parse.quote(query)}"
    )
    try:
        opener = _bilibili_opener()
        request = urllib.request.Request(
            url, headers={**_BROWSER_HEADERS, "Referer": "https://www.bilibili.com/"}
        )
        with opener.open(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        logger.debug("B 站搜索失败: %s", exc)
        return []

    if payload.get("code") != 0:
        logger.debug("B 站搜索返回 code=%s", payload.get("code"))
        return []

    results: list[Source] = []
    for item in (payload.get("data") or {}).get("result") or []:
        title = _clean_fragment(item.get("title") or "")
        bvid = item.get("bvid") or ""
        if not title or not bvid:
            continue
        description = _clean_fragment(item.get("description") or "")
        results.append(
            Source(
                title=f"[视频] {title}",
                url=f"https://www.bilibili.com/video/{bvid}",
                snippet=description[:400],
                origin="bilibili",
            )
        )
        if len(results) >= limit:
            break
    return results


def _parse_csdn_payload(payload: dict, limit: int) -> list[Source]:
    """Turn a CSDN search API response into sources."""
    results: list[Source] = []
    for item in payload.get("result_vos") or []:
        title = _clean_fragment(item.get("title") or "")
        link = (item.get("url") or "").strip()
        if not title or not link.startswith("http"):
            continue
        body = item.get("digest") or item.get("description") or ""
        author = item.get("author") or ""
        snippet = _clean_fragment(body)[:400]
        if author:
            snippet = f"作者 {author}：{snippet}"
        results.append(
            Source(title=title, url=link, snippet=snippet, origin="csdn")
        )
        if len(results) >= limit:
            break
    return results


def search_csdn(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """CSDN blog posts and downloads, via CSDN's own search API.

    CSDN's search *page* is a JavaScript shell, but the endpoint behind it returns
    clean JSON (measured: 30 results with title/url/description/author), so this
    uses the API rather than scraping. That also makes CSDN the one Chinese source
    that does **not** depend on 360's index, and therefore the one that keeps
    working when 360 rate-limits.
    """
    url = (
        "https://so.csdn.net/api/v3/search"
        f"?q={urllib.parse.quote(query)}&t=all&p=1&s=0&tm=0"
    )
    try:
        raw = _browser_get(url, timeout=timeout, referer="https://so.csdn.net/")
        payload = json.loads(raw)
    except Exception as exc:
        logger.debug("CSDN API 失败（改走站内搜索）: %s", exc)
        return _site_search(query, "blog.csdn.net", "csdn", limit, timeout)

    results = _parse_csdn_payload(payload, limit)
    if not results:
        return _site_search(query, "blog.csdn.net", "csdn", limit, timeout)
    return results


def search_tieba(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """百度贴吧 threads.

    Tieba answers 403 to direct search requests from here, so this goes through
    360's index - which covers it well (it surfaced the "MTK 常见错误指令" thread
    that explains what each SP Flash Tool error means).
    """
    direct = f"https://tieba.baidu.com/f/search/res?ie=utf-8&qw={urllib.parse.quote(query)}"
    try:
        html = _browser_get(direct, timeout=min(timeout, 10))
        parsed = _parse_360(html, limit, "tieba")
        if parsed:
            return parsed
    except Exception as exc:
        logger.debug("贴吧直连失败（改走站内搜索）: %s", exc)
    return _site_search(query, "tieba.baidu.com", "tieba", limit, timeout)


def search_zhihu(query: str, limit: int = MAX_SOURCES, timeout: int = DEFAULT_TIMEOUT) -> list[Source]:
    """知乎 questions and answers.

    Direct access is blocked (search page 403, API 400), so this uses 360's index.
    知乎 is less flashing-focused than the other sources, so it contributes fewer
    results - that is reported honestly rather than padded out.
    """
    direct = f"https://www.zhihu.com/search?type=content&q={urllib.parse.quote(query)}"
    try:
        html = _browser_get(direct, timeout=min(timeout, 10))
        parsed = _parse_360(html, limit, "zhihu")
        if parsed:
            return parsed
    except Exception as exc:
        logger.debug("知乎直连失败（改走站内搜索）: %s", exc)
    return _site_search(query, "zhihu.com", "zhihu", limit, timeout)


BACKENDS = {
    "github": search_github,
    "web360": search_360,
    "csdn": search_csdn,
    "coolapk": search_coolapk,
    "tieba": search_tieba,
    "zhihu": search_zhihu,
    "bilibili": search_bilibili,
    "xda": search_xda,
    "bing": search_bing,
}

# Display names for the settings page, with a short honest note about each.
# The notes matter: a user ticking "XDA" deserves to know it is often unreachable
# rather than silently getting nothing back.
BACKEND_LABELS: dict[str, tuple[str, str]] = {
    "github": ("GitHub", "报错原文最准"),
    "web360": ("通用网页 (360)", "覆盖面最广"),
    "csdn": ("CSDN", "技术博客多"),
    "coolapk": ("酷安", "小米社区经验"),
    "tieba": ("百度贴吧", "刷机吧/MTK吧"),
    "zhihu": ("知乎", "偏原理"),
    "bilibili": ("B站", "只有标题简介"),
    "xda": ("XDA", "常被墙"),
    "bing": ("Bing", "多词查询不准"),
}

# Backends that reach their site through 360's index rather than the site itself.
# Kept as a set so the app can warn: each one is another request to 360, and 360
# starts answering with a captcha page if asked too often.
VIA_360 = ("web360", "coolapk", "tieba", "zhihu", "xda")


# Sources that must never be cited.
#
# The project's own issue tracker is the clearest case: searching for an error
# string finds the issue that *reports the KB lacks coverage*, which then gets
# cited as the authority on the error. That is circular - the page would cite
# itself as its own source. Measured: this happened on the first enrichment run.
SOURCE_BLOCKLIST = (
    "github.com/travlli/recneko",
)


def _is_blocked(url: str) -> bool:
    lowered = (url or "").lower()
    return any(bad in lowered for bad in SOURCE_BLOCKLIST)


def search_web(
    query: str,
    backends: tuple[str, ...] = DEFAULT_BACKENDS,
    limit: int = MAX_SOURCES,
    timeout: int = DEFAULT_TIMEOUT,
    phrase: str = "",
) -> list[Source]:
    """Search every configured backend and merge the results, de-duplicated.

    Backends run **in parallel**: with seven of them, doing it sequentially made a
    lookup take the sum of every site's latency (10-20s). Running them together
    costs about as long as the slowest one.

    Results are then interleaved (one from each backend per round) rather than
    filling the quota from the first backend. Filling in order meant GitHub alone
    could consume every slot, so adding backends changed nothing - the whole point
    of having Coolapk / 贴吧 / Bilibili is that they get a turn.

    Every hit is checked against :func:`source_is_on_topic` first. Search engines
    match loosely - GitHub returned ``mkdocs/issues/4032`` for "SP Flash Tool 4032"
    because it shares the number - and a list of irrelevant links is worse than a
    short one.
    """
    import concurrent.futures

    usable = [name for name in backends if name in BACKENDS]
    for name in backends:
        if name not in BACKENDS:
            logger.debug("未知搜索后端：%s", name)

    if not usable:
        return []

    per_backend: list[list[Source]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(usable))) as pool:
        futures = {
            pool.submit(BACKENDS[name], query, limit, timeout): name for name in usable
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                found = future.result()
            except Exception as exc:
                # One broken backend must not take the whole lookup down.
                logger.debug("后端 %s 出错：%s", name, exc)
                continue
            if not found:
                continue
            kept = [
                source
                for source in found
                if source_is_on_topic(source) or _phrase_in_source(source, phrase)
            ]
            dropped = len(found) - len(kept)
            if dropped:
                logger.info("后端 %s：丢弃 %d 条与刷机无关的结果", name, dropped)
            if kept:
                per_backend.append(kept)

    merged: list[Source] = []
    seen: set[str] = set()
    for index in range(max((len(group) for group in per_backend), default=0)):
        for group in per_backend:
            if index >= len(group):
                continue
            source = group[index]
            key = source.url.rstrip("/")
            if not key or key in seen or _is_blocked(key):
                continue
            seen.add(key)
            merged.append(source)
            if len(merged) >= limit:
                return merged
    return merged


# --------------------------------------------------------------------------
# AI client
# --------------------------------------------------------------------------


class AiClient:
    """Minimal OpenAI-compatible chat client."""

    def __init__(self, config: AiConfig):
        self.config = config

    def chat(self, messages: list[dict], timeout: int | None = None) -> tuple[str, int]:
        """Return ``(text, total_tokens)``. Raises on failure."""
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        data = _http_post_json(url, payload, timeout or self.config.timeout, headers)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"模型没有返回内容：{str(data)[:200]}")
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        usage = data.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        return text, tokens


# --------------------------------------------------------------------------
# Relevance filtering
# --------------------------------------------------------------------------

# GitHub's issue search tokenises loosely: a query for
# `"remote: Check device console"` came back with cordova-android,
# ionic-framework and html5-qrcode threads, because they happen to contain the
# words "remote", "check", "device" and "console" somewhere. Feeding that to the
# model costs ~7000 tokens and produces "no idea" - measured on the first real
# run.
#
# Matching individual words is not enough to catch this: "check", "device" and
# "console" are common enough that a word-based filter still passed the junk.
# The check therefore requires the *phrase* (or a long contiguous window of it)
# to actually appear, which is what "this page is about my error" means.
_MIN_WINDOW_WORDS = 3


def relevance_phrase(query: str) -> str:
    """The literal phrase to look for, from a (possibly quoted) query.

    Only the quoted part is used. The query carries an appended domain hint
    ("… 刷机 MTK") to steer the search engines, but that hint must not become part
    of the phrase a page has to contain - no page writes "Antirollback check
    error 刷机" adjacently, so including it rejected every correct source.
    """
    quoted = re.findall(r'"([^"]+)"', query)
    if quoted:
        return re.sub(r"\s+", " ", quoted[0]).strip().lower()
    return re.sub(r"\s+", " ", query.replace('"', " ")).strip().lower()


def _phrase_windows(phrase: str, size: int) -> list[str]:
    words = [w for w in re.split(r"[^0-9a-z]+", phrase) if w]
    if len(words) < size:
        return []
    return [" ".join(words[i:i + size]) for i in range(len(words) - size + 1)]


def source_is_relevant(text: str, phrase: str) -> bool:
    """Whether a fetched page actually mentions the error being looked up.

    Accepts the full phrase, or - for long phrases - any window of at least
    ``_MIN_WINDOW_WORDS`` consecutive words, since pages often reword slightly
    around the quoted error.
    """
    if not phrase:
        return True
    lowered = re.sub(r"\s+", " ", text.lower())
    if phrase in lowered:
        return True
    words = [w for w in re.split(r"[^0-9a-z]+", phrase) if w]
    for size in range(len(words) - 1, _MIN_WINDOW_WORDS - 1, -1):
        if any(window in lowered for window in _phrase_windows(phrase, size)):
            return True
    return False


# --------------------------------------------------------------------------
# Is this result even about phone flashing?
# --------------------------------------------------------------------------
#
# Measured problem: searching "SP Flash Tool 4032" returned
#   github.com/mkdocs/mkdocs/issues/4032        (matched the number 4032)
#   github.com/zed-industries/zed/issues/35948  (unrelated)
#   bilibili "天际线2更新以后的红绿灯新模组 traffic tool essentials"
#   bilibili "拆包Flash游戏导出素材"
# None of those are about Android flashing. The relevance filter that already
# existed only inspects *fetched page bodies*, which happens after the result list
# is shown - so the user saw the junk.
#
# Only unambiguous terms count. "flash" alone is NOT enough: it matches Flash
# games and Adobe Flash. A result must contain a strong term, or the error phrase
# itself, to be kept.
DOMAIN_STRONG = (
    # Chinese
    "刷机", "线刷", "卡刷", "救砖", "变砖", "固件", "刷机包", "引导程序",
    "恢复模式", "分区表", "联发科", "高通", "骁龙", "小米", "红米", "魅族",
    "三星", "解锁bl", "面具", "magisk", "降级", "回滚", "驱动安装",
    # English (multi-word ones catch the real tool names)
    "fastboot", "bootloader", "recovery mode", "twrp", "brom", "edl",
    "9008", "preloader", "sahara", "firehose", "qfil", "miflash",
    "sp flash tool", "spflashtool", "mediatek", "qualcomm", "snapdragon",
    "xiaomi", "redmi", "poco", "vbmeta", "avb", "odin mode", "heimdall",
    "adb sideload", "dload", "emmc", "ufs", "da file", "scatter file",
    "flash_all", "rom 包", "官方rom", "ota 包",
)


def source_is_on_topic(source: Source) -> bool:
    """Whether a search hit plausibly concerns Android flashing.

    Titles and snippets are all that exist before fetching, so this is the only
    place to stop obvious junk from reaching the user or the model.
    """
    text = f"{source.title} {source.snippet}".lower()
    return any(term in text for term in DOMAIN_STRONG)


def _phrase_in_source(source: Source, phrase: str) -> bool:
    """Whether the error phrase appears in the hit's title/snippet."""
    if not phrase:
        return False
    text = re.sub(r"\s+", " ", f"{source.title} {source.snippet}".lower())
    return phrase in text


# --------------------------------------------------------------------------
# The research pipeline
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """你是小米/红米刷机报错排查专家。用户遇到了刷机报错，需要**一个能照着做的答案**。

你有两种依据，都要用：
- 【资料】= 刚从网上抓到的网页内容。用了就标注来源编号，例如 [1]。
- 你自己的知识 = 你对 MTK / 高通 / fastboot / recovery / AVB 报错的了解。
  用了就标注 [自身知识]。

硬性要求：
1. **必须给出可执行的解决方案**，不要用"资料不足，无法确认"来收尾。
   即使用户的描述很少，也要给出最可能的原因和排查步骤。
2. 【资料】里有的，优先采用，并标注 [编号]。
3. 资料里没有、但你知道的，用你自己的知识回答，标注 [自身知识]，
   并提醒用户这部分未经来源核实、请自行核对。
4. **不要编造**具体的文件名、命令、链接或错误码。不确定就写"不确定"，
   并说明怎么确认（例如"看设备管理器里端口号"）。
5. 涉及**清除数据 / 刷机 / 解锁 BL / 降级**等有风险的操作，必须写明风险，
   并给出更安全的先行动作。
6. 按可能性从高到低排列步骤，不要罗列一堆并列的可能。

输出格式（用这些小节标题）：
## 现象
## 最可能的原因
## 排查步骤
（编号步骤，每步标注 [编号] 或 [自身知识]）
## 风险提示
## 还需要你补充
## 依据
（列出用到的来源编号与链接；若用了自身知识也要写明）
"""


# Context appended to a search phrase. Without it a bare phrase attracts
# unrelated content: measured, `SP Flash Tool 4032` returned a Bilibili video
# about unpacking **Flash games**, because "flash tool" reads as an animation
# tool. Adding the domain word ("刷机") keeps the engines on topic.
_PLATFORM_HINT = {
    "mtk": "刷机 MTK",
    "qualcomm": "刷机 高通",
    "fastboot": "fastboot 刷机",
    "recovery": "recovery 刷机",
    "avb": "刷机 vbmeta",
}


def build_query(text: str, finding=None) -> str:
    """Turn a log excerpt into a search query.

    Phrase search (quoted) is used deliberately. Measured against the GitHub
    API: the bare word ``Antirollback`` returned registry/database projects that
    merely use the term, whereas ``"press any key to shutdown"`` returned 158
    hits whose top result was the exact failure. Quoting is what makes the search
    about *this* error instead of the topic in general.

    A platform hint is appended where one is known, because the phrase alone is
    often ambiguous outside the flashing domain.
    """
    from .ocr import extract_error_codes

    platform = getattr(finding, "platform", "") if finding else ""
    hint = _PLATFORM_HINT.get(platform, "刷机")

    def with_hint(phrase: str) -> str:
        return f"{phrase} {hint}" if phrase else ""

    codes = extract_error_codes(text)
    if codes:
        return with_hint(f'"ERROR {codes[0]}"')

    # A parenthesised fragment is usually the specific cause
    # ("data transfer failure (Too many links)" -> "Too many links").
    inner = re.search(r"\(([^()]{6,60})\)", text)
    if inner:
        phrase = _clean_phrase(inner.group(1))
        if phrase:
            return with_hint(f'"{phrase}"')

    # An underscore-style status token is highly distinctive on its own.
    token = re.search(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}\b", text)
    if token:
        return with_hint(f'"{token.group(0)}"')

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    phrase = _clean_phrase(first_line)
    if phrase:
        return with_hint(f'"{phrase}"')

    if platform and platform != "unknown":
        return f"{platform} 刷机 报错"
    return "安卓 刷机 报错"


# Noise that carries no search value inside a quoted phrase.
_QUERY_NOISE = re.compile(
    r"(?i)^(?:error|failed|failure|fatal|warning|err)\s*[:\-]?\s*"
)
_QUERY_STRIP = re.compile(r"[\[\]{}<>\"']|0x[0-9a-f]{6,}")


def _clean_phrase(line: str) -> str:
    """Reduce a log line to a short, quotable phrase."""
    if not line:
        return ""
    phrase = _QUERY_NOISE.sub("", line.strip())
    phrase = _QUERY_STRIP.sub(" ", phrase)

    # Users describe the screen in Chinese before quoting the English message
    # ("手机屏幕显示 press any key to shutdown"). Search engines do far better
    # with the Latin message alone.
    if re.search(r"[\u4e00-\u9fff]", phrase):
        latin = re.search(r"[A-Za-z][A-Za-z0-9 _.:'()/\-]{5,}", phrase)
        if latin:
            phrase = latin.group(0)

    phrase = re.sub(r"\s+", " ", phrase).strip(" .,:;-—")
    # Keep it short: a long quoted string matches nothing.
    words = phrase.split()
    if len(words) > 7:
        phrase = " ".join(words[:7])
    if len(phrase) < 4:
        return ""
    return phrase


def research(
    text: str,
    config: AiConfig | None = None,
    finding=None,
    query: str | None = None,
    client: AiClient | None = None,
    max_sources: int = MAX_SOURCES,
) -> OnlineAnswer:
    """Look an error up and return a solution.

    The web search **supplements** the model rather than gating it. An earlier
    version refused to answer unless a fetched page contained the error text,
    which threw away most of the feature's value: when the search was rate-limited
    or simply found nothing, the user got "no answer" for an error the model
    handles perfectly well from its own knowledge.

    So both are used, and the difference is made visible:
      * material from fetched pages is cited as ``[1]``, ``[2]`` … (checkable),
      * anything from the model's own knowledge is marked ``[自身知识]``
        (not checkable - the user is told to verify it).

    Returns a failure object (never raises) only when online lookup is disabled or
    unconfigured, or when the model call itself fails.
    """
    config = config or AiConfig.load()
    if not config.usable:
        if not config.enabled:
            return OnlineAnswer(error="联网查询未启用（默认关闭）")
        return OnlineAnswer(
            error="联网查询未配置：需要 base_url / api_key / model"
        )

    # 1) redact before anything leaves the machine
    safe_text = redact(text)
    search_query = query or build_query(safe_text, finding)
    answer = OnlineAnswer(queries=[search_query] if search_query else [])

    # 2) search - best effort. Failure here must not stop the answer.
    search_note = ""
    usable: list[Source] = []
    if search_query:
        try:
            candidates = search_web(
                search_query,
                backends=config.backends,
                limit=max_sources,
                phrase=relevance_phrase(search_query),
            )
        except Exception as exc:
            logger.debug("搜索失败，改为仅用模型自身知识：%s", exc)
            candidates = []
            search_note = f"（搜索出错：{type(exc).__name__}）"

        # 3) fetch the pages and keep only the ones that really mention the error
        phrase = relevance_phrase(search_query)
        budget = MAX_TOTAL_CHARS
        for source in candidates:
            if budget <= 0:
                break
            body = fetch_page(
                source.url, timeout=config.timeout, limit=min(MAX_SOURCE_CHARS, budget)
            )
            if body:
                source.snippet = body
                source.fetched = True
                budget -= len(body)

        fetched = [s for s in candidates if s.fetched and len(s.snippet) > 200]
        usable = [s for s in fetched if source_is_relevant(s.snippet, phrase)]

        if not candidates:
            search_note = search_note or "（没搜到和刷机相关的结果）"
        elif not fetched:
            search_note = "（搜到链接但抓不到正文）"
        elif not usable:
            search_note = f"（搜到 {len(fetched)} 个页面，但都没提到这个报错）"
        elif len(usable) < len(fetched):
            logger.info("丢弃 %d 个未提及该报错的来源", len(fetched) - len(usable))

    # If a rate limit is why we came up empty, say so - otherwise it looks like
    # "this error has no results anywhere". This takes priority over the generic
    # "nothing relevant found" note, because it is the actionable reason.
    if not usable and LAST_BLOCKED_AT and (time.time() - LAST_BLOCKED_AT) < 300:
        search_note = "（搜索引擎触发了频率限制，Coolapk / 贴吧 / 知乎 依赖它的索引，过几分钟再试）"

    answer.sources = usable
    answer.grounded = bool(usable)

    # 4) build the prompt. With material the model must prefer it; without any it
    #    answers from its own knowledge and says so.
    if usable:
        material = "\n\n".join(
            f"【资料 {i}】{s.title}\nURL: {s.url}\n{s.snippet}"
            for i, s in enumerate(usable, start=1)
        )
        material_block = (
            f"===== 资料开始 =====\n{material}\n===== 资料结束 =====\n\n"
            "优先使用上面的资料并标注 [编号]；资料没覆盖的部分用你自己的知识补全，"
            "标注 [自身知识]。"
        )
    else:
        material_block = (
            "本次**没有检索到可用资料**"
            f"{search_note}。\n"
            "请完全依靠你自己的知识回答，每条都标注 [自身知识]，"
            "并在开头说明这次没有联网来源可核对。"
        )

    user_prompt = (
        f"用户遇到的报错（已脱敏）：\n{safe_text[:4000]}\n\n"
        f"检索查询：{search_query or '(无)'}\n\n"
        f"{material_block}\n\n"
        "请按系统提示的格式给出**可执行的解决方案**，不要以"
        "\"资料不足\"作为结论。"
    )

    try:
        client = client or AiClient(config)
        text_out, tokens = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception as exc:
        answer.error = f"模型调用失败：{type(exc).__name__}: {exc}"
        return answer

    answer.model = config.model
    answer.tokens = tokens

    if not text_out:
        answer.error = "模型返回了空内容（可能是 max_tokens 太小，全部用在推理上）"
        return answer

    # 5) accept it. An answer from the model's own knowledge is still an answer -
    #    it is labelled as such rather than withheld.
    answer.text = text_out
    answer.used_own_knowledge = "[自身知识]" in text_out
    answer.ok = True
    if not answer.grounded:
        answer.error = (
            f"本次没有联网来源可核对{search_note}，"
            "以下方案来自模型自身知识，请自行验证。"
        )
    return answer


def render_answer(answer: OnlineAnswer) -> str:
    """Render an online answer for display, making its provenance obvious."""
    lines: list[str] = []
    if not answer.ok:
        lines.append("联网查询未给出结果。")
        if answer.error:
            lines.append(f"原因：{answer.error}")
        if answer.queries:
            lines.append(f"检索词：{answer.queries[0]}")
        if answer.sources:
            lines.append("")
            lines.append("找到但未能采用的链接：")
            for index, source in enumerate(answer.sources, start=1):
                mark = "已读正文" if source.fetched else "未读到正文"
                lines.append(f"  [{index}] {source.title}（{mark}）")
                lines.append(f"      {source.url}")
        return "\n".join(lines)

    if answer.grounded and answer.used_own_knowledge:
        lines.append(
            "以下方案综合了**联网来源**（标注 [编号]）和**模型自身知识**"
            "（标注 [自身知识]）。前者可点开核对，后者请自行验证。"
        )
    elif answer.grounded:
        lines.append(
            f"以下方案依据联网检索到的 {len(answer.sources)} 条来源，"
            "引用处标注了 [编号]，可点开核对。"
        )
    else:
        lines.append(
            "⚠️ **本次没有检索到可核对的联网来源**，以下方案完全来自模型自身知识。"
        )
        lines.append("刷机操作有风险，请先自行验证，或换个更具体的报错原文再查一次。")
        if answer.error:
            lines.append(f"（{answer.error}）")
    lines.append("")
    lines.append(answer.text.strip())

    if answer.sources:
        lines.append("")
        lines.append("-- 来源 --")
        for index, source in enumerate(answer.sources, start=1):
            origin = f"（{source.origin}）" if source.origin else ""
            lines.append(f"  [{index}] {source.title}{origin}")
            lines.append(f"      {source.url}")
    if answer.tokens:
        lines.append("")
        lines.append(f"（模型 {answer.model}，本次消耗 {answer.tokens} tokens）")
    return "\n".join(lines)
