"""Deterministic RAG text hygiene: dedupe/rerank chunks, clean context, clean the
final answer. Pure functions (no DB/LLM) so they are easy to unit-test.

These fix the observed failure where a small local model echoed duplicated,
overlapping RTL chunks with inline [n] markers instead of answering concisely.
"""

from __future__ import annotations

import re
from dataclasses import replace

try:  # optional, better Unicode ratio
    from rapidfuzz.fuzz import ratio as _rf_ratio

    def _sim(a: str, b: str) -> float:
        return _rf_ratio(a, b) / 100.0
except ImportError:  # pragma: no cover
    from difflib import SequenceMatcher

    def _sim(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

_WS = re.compile(r"\s+")
_PAGE_LINE = re.compile(r"^\s*[-–—]?\s*\d{1,4}\s*[-–—]?\s*$")   # standalone page numbers
_CITE = re.compile(r"\s*\[\s*\d{1,3}\s*\]")                       # [1], [ 2 ]
_SENT_SPLIT = re.compile(r"(?<=[.!?׃؟])\s+|\n+")


def normalize(text: str) -> str:
    return _WS.sub(" ", (text or "")).strip()


# --------------------------------------------------------------------------- #
# Chunk dedupe + rerank
# --------------------------------------------------------------------------- #

def dedupe_chunks(chunks: list, *, threshold: float = 0.85) -> list:
    """Drop near-duplicate / contained chunks, keeping the higher-scoring one.

    Works on any object exposing .content and .score (RetrievedChunk)."""
    kept: list = []
    for c in sorted(chunks, key=lambda x: getattr(x, "score", 0.0), reverse=True):
        cn = normalize(c.content).lower()
        dup = False
        for k in kept:
            kn = normalize(k.content).lower()
            if not cn or not kn:
                continue
            if cn in kn or kn in cn or _sim(cn, kn) >= threshold:
                dup = True
                break
        if not dup:
            kept.append(c)
    return kept


def _keyword_overlap(query: str, content: str) -> float:
    q = {t for t in re.split(r"\W+", (query or "").lower()) if len(t) > 2}
    if not q:
        return 0.0
    c = {t for t in re.split(r"\W+", (content or "").lower()) if len(t) > 2}
    return len(q & c) / len(q)


def rerank(chunks: list, query: str, *, top: int = 4) -> list:
    """Blend vector score, keyword overlap and same-document continuity, then cap.

    final = 0.65*vector + 0.25*keyword + 0.10*same_doc_bonus
    """
    if not chunks:
        return []
    top_doc = max(chunks, key=lambda c: getattr(c, "score", 0.0)).document_id
    scored = []
    for c in chunks:
        vec = float(getattr(c, "score", 0.0))
        kw = _keyword_overlap(query, c.content)
        same = 1.0 if c.document_id == top_doc else 0.0
        final = 0.65 * vec + 0.25 * kw + 0.10 * same
        scored.append((final, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _, c in scored[:top]]


def prepare_chunks(chunks: list, query: str, *, top: int = 4) -> list:
    """Full pre-LLM pipeline: dedupe overlapping, rerank, cap, and clean text."""
    deduped = dedupe_chunks(chunks)
    ranked = rerank(deduped, query, top=top)
    return [replace(c, content=clean_context_text(c.content)) for c in ranked]


# --------------------------------------------------------------------------- #
# Text cleaning
# --------------------------------------------------------------------------- #

def clean_context_text(text: str) -> str:
    """Strip page-number lines, inline citation markers, collapse whitespace and
    drop consecutive duplicate lines — without altering meaning."""
    out_lines: list[str] = []
    prev = None
    for raw in (text or "").splitlines():
        line = _CITE.sub("", raw).strip()
        if not line or _PAGE_LINE.match(line):
            continue
        norm = normalize(line).lower()
        if norm == prev:
            continue
        prev = norm
        out_lines.append(_WS.sub(" ", line))
    return "\n".join(out_lines).strip()


# Prompt-scaffold leakage a small model sometimes echoes instead of answering
# (e.g. "context>.pdf>", "SOURCES:"). Strip these fragments wherever they appear.
_SCAFFOLD = re.compile(r"(?i)\b(context|sources)\b\s*:?|\S*\.pdf[>\]]?|<[^>]*>|[<>]+")


def has_content(text: str) -> bool:
    """True if the text has enough real letters (he/ar/latin) to be an answer."""
    letters = re.findall(r"[A-Za-z֐-׿؀-ۿ]", text or "")
    return len(letters) >= 8


def clean_answer(text: str) -> str:
    """Post-process an LLM answer: strip prompt scaffolding + inline [n] markers and
    repeated sentences/paragraphs (small models loop), collapse whitespace. Never
    edits factual content — only removes duplicates and metadata."""
    text = _SCAFFOLD.sub(" ", text or "")
    text = _CITE.sub("", text)
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    kept: list[str] = []
    seen: list[str] = []
    for s in sentences:
        norm = normalize(s).lower()
        if any(norm == k or _sim(norm, k) >= 0.9 for k in seen):
            continue  # drop repeated / near-repeated sentence
        seen.append(norm)
        kept.append(s)
    result = " ".join(kept)
    return _WS.sub(" ", result).strip()
