"""Knowledge base loading and retrieval.

The knowledge base is consumed as a generated JSON file (``data/kb.json``)
that is produced from the dsh-kb Obsidian wiki by ``tools/build_kb.py``.
Bundling a pre-built JSON keeps runtime free of a Markdown parser and makes
the payload identical on desktop (exe) and Android (apk).
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class KBLoadError(RuntimeError):
    """The knowledge base could not be loaded (missing, unreadable, malformed)."""


# --------------------------------------------------------------------------
# Tokenisation / matching helpers
# --------------------------------------------------------------------------

# Tokens shorter than this are too noisy to be useful as standalone terms.
MIN_TOKEN_LEN = 2

_WORD_RE = re.compile(r"[a-z0-9_./\\-]{2,}", re.IGNORECASE)


def normalise(text: str) -> str:
    """Lower-case and collapse whitespace so matching is case-insensitive."""
    return re.sub(r"\s+", " ", text.casefold()).strip()


# Separators that mean the same thing to a user pasting a log, but are different
# bytes: `ERROR 2004`, `ERROR: 2004`, `ERROR:2004` and `ERROR : 2004` are all the
# same error. `scanner.py` already treats these as equivalent when extracting
# codes; the keyword matcher used to disagree, which is why pasting the *real*
# message sometimes scored lower than a typo.
_LOOSE_RE = re.compile(r"[\s:_\-/\\]+")


def loose(text: str) -> str:
    """Normalise for keyword matching: whitespace, colons, underscores, dashes."""
    return _LOOSE_RE.sub(" ", normalise(text)).strip()


_SQUASH_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def squash(text: str) -> str:
    """Strip every separator, keeping only alphanumerics and CJK.

    OCR inserts spaces inside compound words: measured, Windows OCR reads
    ``dm-verity corruption`` as ``d m-verity corruption``, and the keyword then
    failed to match even though the text was correct. Comparing a separator-free
    form recovers that case without loosening ordinary word matching.
    """
    return _SQUASH_RE.sub("", normalise(text))


# Words that carry no discriminating power in this domain. Without this list the
# unbounded IDF term let a single common word dominate: measured, the query
# "the the the" scored 228.6 while the real keyword "BROM" scored only 38.6, so
# garbage input outranked every correct match. Which page won was also arbitrary
# - it depended on which author happened to list that word as a keyword.
#
# Only genuine function words are listed. Domain words such as "error",
# "failed" and "device" are deliberately NOT stopped: they are what identifies a
# log line as a failure, and removing them measurably broke a real case
# ("Download Fail: Sahara Fail: ..." stopped ranking to the Sahara page).
STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "not", "no", "is", "are", "was", "were",
    "be", "been", "being", "in", "on", "at", "to", "of", "for", "by", "with",
    "it", "its", "this", "that", "these", "those", "as", "if", "then", "than",
    "from", "into", "out", "up", "down", "can", "could", "would", "should",
    "will", "shall", "may", "might", "must", "do", "does", "did", "has",
    "have", "had", "you", "your", "my", "me", "we", "our", "they", "them",
    "he", "she", "his", "her", "there", "here", "when", "where", "which",
    "who", "what", "how", "why", "all", "any", "some", "more", "most", "other",
    "such", "only", "own", "same", "so", "too", "very", "just", "now", "also",
    "please",
})

# Upper bound on the IDF multiplier. With only ~18 documents the raw term
# `total_docs / freq` explodes for a word that appears on one page, which is
# exactly how a stopword outscored a real error code.
MAX_IDF = 4.0

# Below this score a match is noise, not an answer.
#
# Derived from measurement, not taste. Re-derived after the KB was enriched to 25
# entries (adding pages shifts every score, because the token weight uses IDF):
#
#   should match  : 34.6 - 189.1   (19 cases, incl. OCR spacing variants)
#   should NOT    :  0.0 -  17.2   (11 cases: still-uncovered errors + junk)
#
# 26.0 sits in the gap. The worst legitimate case is the OCR-mangled
# "d m-verity corruption" (34.6), which only matches through the separator-free
# path; the best illegitimate case is the junk string "今天天气不错" (17.2).
#
# The threshold is corpus-dependent and MUST be re-derived when entries are added
# in bulk. tests/test_kb.py asserts the separation, so a drift fails loudly
# instead of silently degrading into wrong answers.
MIN_RELEVANCE = 26.0


def tokenize(text: str) -> list[str]:
    """Split text into matchable tokens.

    Both latin tokens (``error 4032``, ``flash write failure``) and CJK
    character runs are produced, because Chinese log/UI text has no spaces.
    """
    lowered = text.casefold()
    tokens = [t for t in _WORD_RE.findall(lowered) if len(t) >= MIN_TOKEN_LEN]
    # CJK runs: treat each character as a token so that "无法开机" can match
    # a keyword of "无法开机" or a symptom sentence containing it.
    for run in re.findall(r"[\u4e00-\u9fff]+", lowered):
        tokens.extend(run)
        if len(run) >= 2:
            tokens.append(run)
    return tokens


def is_cjk(token: str) -> bool:
    """True if the token is made of CJK characters only."""
    return bool(token) and all("\u4e00" <= char <= "\u9fff" for char in token)


def token_present(token: str, haystack: str) -> bool:
    """Whether ``token`` occurs in ``haystack`` as a real word.

    A plain substring test is wrong here: the token ``flash`` would otherwise
    match inside ``flashing``, which made unrelated pages outrank the correct
    one. Latin tokens therefore require word boundaries; CJK has no spaces, so
    substring matching is the correct semantics there.
    """
    if not token:
        return False
    if is_cjk(token):
        return token in haystack
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) is not None


@dataclass
class Entry:
    """One knowledge-base page."""

    slug: str
    title: str
    platform: str
    category: str
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    # raw/ material this page was distilled from (schema requirement). Kept on
    # the entry so the UI can show provenance, and so tests can assert that a
    # page is not just plausible-sounding prose with nothing behind it.
    sources: list[str] = field(default_factory=list)
    symptom: str = ""
    cause: str = ""
    steps: str = ""
    verify: str = ""
    todo: str = ""
    body: str = ""
    path: str = ""

    # Pre-computed search surface (see KB._prepare).
    _haystack: str = ""
    _keyword_blob: str = ""
    _doc_tokens: set[str] = field(default_factory=set)

    @property
    def summary(self) -> str:
        """First meaningful line of the symptom section, for list display."""
        for chunk in (self.symptom, self.body):
            for line in chunk.splitlines():
                line = line.strip().strip("#").strip()
                if line and not line.startswith("```"):
                    return line[:160]
        return self.title

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "platform": self.platform,
            "category": self.category,
            "tags": self.tags,
            "keywords": self.keywords,
            "sources": self.sources,
            "symptom": self.symptom,
            "cause": self.cause,
            "steps": self.steps,
            "verify": self.verify,
            "todo": self.todo,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "Entry":
        return cls(
            slug=raw.get("slug", ""),
            title=raw.get("title", ""),
            platform=raw.get("platform", ""),
            category=raw.get("category", ""),
            tags=list(raw.get("tags") or []),
            keywords=list(raw.get("keywords") or []),
            sources=list(raw.get("sources") or []),
            symptom=raw.get("symptom", "") or "",
            cause=raw.get("cause", "") or "",
            steps=raw.get("steps", "") or "",
            verify=raw.get("verify", "") or "",
            todo=raw.get("todo", "") or "",
            body=raw.get("body", "") or "",
            path=raw.get("path", "") or "",
        )


@dataclass
class Match:
    """A scored search hit."""

    entry: Entry
    score: float
    hits: list[str] = field(default_factory=list)
    reason: str = ""


# --------------------------------------------------------------------------
# Knowledge base
# --------------------------------------------------------------------------


class KB:
    """In-memory knowledge base with keyword-weighted retrieval."""

    def __init__(self, entries: Iterable[Entry] | None = None, version: str = "") -> None:
        self.entries: list[Entry] = []
        self.version = version
        for entry in entries or []:
            self.add(entry)

    # -- construction ------------------------------------------------------

    def add(self, entry: Entry) -> None:
        self._prepare(entry)
        self.entries.append(entry)

    @staticmethod
    def _prepare(entry: Entry) -> None:
        """Pre-compute the text surfaces used for scoring."""
        # `keywords` are curated by the KB authors and are the strongest
        # signal, so they are stored separately and weighted highest.
        entry._keyword_blob = normalise(" ".join(entry.keywords) + " " + " ".join(entry.tags))
        searchable = "\n".join(
            [
                entry.title,
                entry.platform,
                " ".join(entry.tags),
                " ".join(entry.keywords),
                entry.symptom,
                entry.cause,
                entry.steps,
                entry.verify,
                entry.body,
            ]
        )
        entry._haystack = normalise(searchable)
        # Query tokens that hit this entry, used for inverse-document-frequency
        # weighting: rare, distinctive tokens (error codes) must outweigh
        # generic ones that occur on every platform page ("flash", "错误").
        entry._doc_tokens = {token for token in set(tokenize(searchable)) if token_present(token, entry._haystack)}

    # -- loading -----------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: str | os.PathLike[str] | None = None,
        extra_paths: Iterable[str | os.PathLike[str]] | None = None,
        strict: bool | None = None,
    ) -> "KB":
        """Load the JSON knowledge base.

        Resolution order (first readable file wins):
        1. an explicit ``path`` argument,
        2. ``$MIRECOVERY_KB`` (handy for testing a rebuilt KB),
        3. any ``extra_paths`` (used by the GUI to consult the app's own
           resource directory, which is how BeeWare lays apps out on Android),
        4. ``data/kb.json`` next to this module (normal bundled case),
        5. ``_MEIPASS`` / beside the frozen executable (PyInstaller layouts).

        ``strict`` controls what happens when a candidate exists but cannot be
        parsed. It defaults to **True when an explicit ``path`` was given** and
        False otherwise.

        That default matters: previously ``KB.load(some_path)`` silently fell
        through to the bundled knowledge base whenever ``some_path`` was
        missing or corrupt, so a caller could pass a typo'd path and quietly get
        a *different* database than the one it asked for - with no error. An
        explicit path is now authoritative: if it cannot be read, that is an
        error, not a fallback.
        """
        if strict is None:
            strict = path is not None

        candidates: list[Path] = []
        if path is not None:
            candidates.append(Path(path))
        env = os.environ.get("MIRECOVERY_KB")
        if env:
            candidates.append(Path(env))
        for extra in extra_paths or []:
            candidates.append(Path(extra))
        candidates.append(Path(__file__).resolve().parent / "data" / "kb.json")
        # PyInstaller puts bundled data in _MEIPASS, which may differ from the
        # package directory once frozen.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "mirecovery" / "data" / "kb.json")
            candidates.append(Path(meipass) / "data" / "kb.json")
        # Last resort: next to the running executable.
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "kb.json")

        seen: set[str] = set()
        unique: list[Path] = []
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique.append(candidate)

        last_error: Exception | None = None
        for index, candidate in enumerate(unique):
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                last_error = exc
                if strict and index == 0:
                    # The caller named this file. Do not silently use another.
                    raise KBLoadError(
                        f"指定的知识库文件无法读取：{candidate}\n"
                        f"原因：{type(exc).__name__}: {exc}\n"
                        "（已显式指定路径，因此不会回退到内置知识库）"
                    ) from exc
                continue

            if not isinstance(payload, dict) or "entries" not in payload:
                last_error = ValueError("缺少 entries 字段")
                if strict and index == 0:
                    raise KBLoadError(
                        f"指定的知识库文件格式不正确（缺少 entries 字段）：{candidate}"
                    )
                continue

            entries = [Entry.from_dict(item) for item in payload.get("entries", [])]
            return cls(entries, version=str(payload.get("version", "")))

        raise KBLoadError(
            "找不到可用的知识库数据文件 kb.json。已尝试: "
            + ", ".join(str(c) for c in unique)
            + (f"（最后一个错误: {last_error}）" if last_error else "")
        )

    # -- querying ----------------------------------------------------------

    def platforms(self) -> list[str]:
        seen: list[str] = []
        for entry in self.entries:
            if entry.platform and entry.platform not in seen:
                seen.append(entry.platform)
        return sorted(seen)

    def search(
        self,
        text: str,
        limit: int = 5,
        platform: str | None = None,
        min_score: float | None = None,
    ) -> list[Match]:
        """Rank entries against pasted log/error text.

        Scoring is deliberately simple and explainable:

        1. a curated keyword appearing verbatim in the query is the strongest
           signal (longer phrases are worth more),
        2. then individual query tokens that hit this entry's curated
           keyword/tag blob, weighted by how *rare* the token is across the
           knowledge base (capped, and stopwords excluded),
        3. then loose token overlap with the whole page (low weight).

        Matches below ``min_score`` (default :data:`MIN_RELEVANCE`) are dropped,
        so an error the KB does not cover returns an empty list instead of five
        unrelated "solutions". Pass ``min_score=0`` for diagnostics.
        """
        query = normalise(text)
        if not query:
            return []

        # Punctuation-insensitive view, so `ERROR: 2004` matches a keyword
        # written as `ERROR 2004`.
        loose_query = loose(text)
        # Separator-free view, for OCR output that splits compound words.
        squashed_query = squash(text)

        tokens = tokenize(text)
        token_counts: dict[str, int] = {}
        for token in tokens:
            if token in STOPWORDS:
                continue
            token_counts[token] = token_counts.get(token, 0) + 1

        floor = MIN_RELEVANCE if min_score is None else float(min_score)

        # Inverse document frequency: how many entries contain each token?
        candidates = [
            entry for entry in self.entries if not platform or entry.platform == platform
        ]
        doc_freq: dict[str, int] = {}
        for token in token_counts:
            doc_freq[token] = sum(1 for entry in candidates if token in entry._doc_tokens)
        total_docs = max(len(candidates), 1)

        matches: list[Match] = []
        for entry in candidates:
            score = 0.0
            keyword_hits: list[str] = []
            token_hits: list[str] = []

            # 1. Curated keywords present in the query. Short keywords must
            #    appear verbatim; multi-word keywords may match on their
            #    distinctive words (so "SP Flash Tool" still matches) while
            #    ubiquitous vocabulary is filtered out by document frequency.
            for keyword in entry.keywords:
                needle = normalise(keyword)
                if len(needle) < 2:
                    continue
                if needle in query or loose(keyword) in loose_query:
                    score += 22.0
                    keyword_hits.append(keyword)
                    continue

                # Separator-free comparison. Length-guarded so short keywords
                # cannot match by accident once the separators are gone.
                squashed_keyword = squash(keyword)
                if len(squashed_keyword) >= 6 and squashed_keyword in squashed_query:
                    score += 18.0
                    keyword_hits.append(keyword)
                    continue

                words = [w for w in tokenize(needle) if not is_cjk(w)]
                if len(words) < 2:
                    continue
                # Drop words that appear on too many pages to be meaningful.
                distinctive = [w for w in words if doc_freq.get(w, 0) <= max(2, total_docs * 0.4)]
                if not distinctive:
                    continue
                matched = [w for w in distinctive if token_present(w, loose_query)]
                if len(matched) == len(distinctive):
                    score += 8.0 + 2.0 * len(matched)
                    keyword_hits.append(keyword)

            # 2. Query tokens found in the curated keyword/tag blob, boosted by
            #    rarity so that error codes dominate generic vocabulary.
            for token, count in token_counts.items():
                if not token_present(token, entry._keyword_blob):
                    continue
                freq = doc_freq.get(token, 0)
                idf = min(1.0 + (total_docs / freq if freq else total_docs), MAX_IDF)
                # Repeats are capped at 2: a word appearing 50 times in a log is
                # not 3x more meaningful than one appearing twice.
                score += 4.0 * min(count, 2) * idf
                if token not in token_hits:
                    token_hits.append(token)

            # 3. Loose overlap with the whole page (capped, low weight).
            overlap = sum(
                1 for token in token_counts if token_present(token, entry._haystack)
            )
            score += min(overlap, 25) * 0.6

            if score < floor or score <= 0:
                continue

            matches.append(
                Match(
                    entry=entry,
                    score=round(score, 2),
                    hits=(keyword_hits + token_hits)[:8],
                    reason=self._explain(entry, keyword_hits, token_hits),
                )
            )

        matches.sort(key=lambda m: (-m.score, m.entry.title))
        return matches[:limit]

    @staticmethod
    def _explain(entry: Entry, keyword_hits: list[str], token_hits: list[str]) -> str:
        """Say *how* the entry matched.

        The distinction matters to the user: "命中关键词: and" was reported for a
        query token that merely coincided with a word on the page, which reads
        like the author had listed ``and`` as a keyword.
        """
        if keyword_hits:
            return "命中关键词: " + "、".join(keyword_hits[:6])
        if token_hits:
            return "文本重合: " + "、".join(token_hits[:6])
        return f"平台 {entry.platform} 相关，文本部分重合"
