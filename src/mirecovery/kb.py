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
# Tokenisation / matching helpers
# --------------------------------------------------------------------------

# Tokens shorter than this are too noisy to be useful as standalone terms.
MIN_TOKEN_LEN = 2

_WORD_RE = re.compile(r"[a-z0-9_./\\-]{2,}", re.IGNORECASE)


def normalise(text: str) -> str:
    """Lower-case and collapse whitespace so matching is case-insensitive."""
    return re.sub(r"\s+", " ", text.casefold()).strip()


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
    ) -> "KB":
        """Load the bundled JSON knowledge base.

        Resolution order:
        1. an explicit ``path`` argument,
        2. ``$MIRECOVERY_KB`` (handy for testing a rebuilt KB),
        3. any ``extra_paths`` (used by the GUI to consult the app's own
           resource directory, which is how BeeWare lays apps out on Android),
        4. ``data/kb.json`` next to this module (normal bundled case),
        5. beside the frozen executable (PyInstaller onefile layout).
        """
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
        for candidate in unique:
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                last_error = exc
                continue
            entries = [Entry.from_dict(item) for item in payload.get("entries", [])]
            return cls(entries, version=str(payload.get("version", "")))

        raise FileNotFoundError(
            "找不到知识库数据文件 kb.json。已尝试: "
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

    def search(self, text: str, limit: int = 5, platform: str | None = None) -> list[Match]:
        """Rank entries against pasted log/error text.

        Scoring is deliberately simple and explainable:

        1. a curated keyword appearing verbatim in the query is the strongest
           signal (longer phrases are worth more),
        2. then individual query tokens that hit this entry's curated
           keyword/tag blob, weighted by how *rare* the token is across the
           knowledge base,
        3. then loose token overlap with the whole page (low weight).
        """
        query = normalise(text)
        if not query:
            return []

        tokens = tokenize(text)
        token_counts: dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

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
            hits: list[str] = []

            # 1. Curated keywords present in the query. Short keywords must
            #    appear verbatim; multi-word keywords may match on their
            #    distinctive words (so "SP Flash Tool" still matches) while
            #    ubiquitous vocabulary is filtered out by document frequency.
            for keyword in entry.keywords:
                needle = normalise(keyword)
                if len(needle) < 2:
                    continue
                if needle in query:
                    score += 22.0
                    hits.append(keyword)
                    continue

                words = [w for w in tokenize(needle) if not is_cjk(w)]
                if len(words) < 2:
                    continue
                # Drop words that appear on too many pages to be meaningful.
                distinctive = [w for w in words if doc_freq.get(w, 0) <= max(2, total_docs * 0.4)]
                if not distinctive:
                    continue
                matched = [w for w in distinctive if token_present(w, query)]
                if len(matched) == len(distinctive):
                    score += 8.0 + 2.0 * len(matched)
                    hits.append(keyword)

            # 2. Query tokens found in the curated keyword/tag blob, boosted by
            #    rarity so that error codes dominate generic vocabulary.
            for token, count in token_counts.items():
                if not token_present(token, entry._keyword_blob):
                    continue
                freq = doc_freq.get(token, 0)
                idf = 1.0 + (total_docs / freq if freq else total_docs)
                score += 4.0 * min(count, 3) * idf
                if token not in hits:
                    hits.append(token)

            # 3. Loose overlap with the whole page (capped, low weight).
            loose = sum(
                1 for token in token_counts if token_present(token, entry._haystack)
            )
            score += min(loose, 25) * 0.6

            if score > 0:
                matches.append(
                    Match(
                        entry=entry,
                        score=round(score, 2),
                        hits=hits[:8],
                        reason=self._explain(entry, hits),
                    )
                )

        matches.sort(key=lambda m: (-m.score, m.entry.title))
        return matches[:limit]

    @staticmethod
    def _explain(entry: Entry, hits: list[str]) -> str:
        if hits:
            return "命中关键词: " + "、".join(hits)
        return f"平台 {entry.platform} 相关，文本部分重合"
