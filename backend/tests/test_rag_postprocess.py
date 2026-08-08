"""Regression for the RAG answer-quality failure (spec §18).

The screenshot showed: duplicated paragraphs, inline [1]/[2] markers, overlapping
chunks dumped verbatim. These deterministic tests lock the fixes in.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.postprocess import (
    clean_answer,
    clean_context_text,
    dedupe_chunks,
    prepare_chunks,
    rerank,
)
from app.rag.service import build_context_block


@dataclass
class _Chunk:
    chunk_id: str
    document_id: str
    document_title: str
    page: int | None
    content: str
    score: float


_PARA = ("לפי הפוליסה המבטח פטור מחבות אם הנהג לא החזיק ברישיון נהיגה תקף המתאים "
         "לסוג הרכב, בכפוף לחריגים המפורטים בפוליסה.")


def test_dedupe_removes_near_duplicate_and_contained_chunks():
    chunks = [
        _Chunk("a", "d1", "sss.pdf", 1, _PARA, 0.9),
        _Chunk("b", "d1", "sss.pdf", 1, _PARA + " ", 0.8),          # near-duplicate
        _Chunk("c", "d1", "sss.pdf", 1, _PARA[:60], 0.7),           # contained
        _Chunk("d", "d1", "sss.pdf", 3, "נהג מורשה חייב להיות בגיל 24 ומעלה.", 0.6),
    ]
    kept = dedupe_chunks(chunks)
    contents = {k.content.strip() for k in kept}
    assert len(kept) == 2
    assert any("גיל 24" in c for c in contents)


def test_clean_answer_strips_markers_and_repeats():
    messy = f"{_PARA} [1] {_PARA} [2]\n{_PARA}\nנהג חייב רישיון תקף. נהג חייב רישיון תקף."
    out = clean_answer(messy)
    assert "[1]" not in out and "[2]" not in out
    # The repeated paragraph appears only once.
    assert out.count("פטור מחבות") == 1
    assert out.count("נהג חייב רישיון תקף") == 1


def test_clean_context_drops_page_numbers_and_citations():
    raw = "עמוד\n12\n[1] סעיף 3: הנהג חייב רישיון.\nסעיף 3: הנהג חייב רישיון.\n\n  "
    cleaned = clean_context_text(raw)
    assert "[1]" not in cleaned
    assert "\n12\n" not in cleaned
    assert cleaned.count("הנהג חייב רישיון") == 1  # consecutive duplicate removed


def test_rerank_prefers_keyword_and_same_document():
    chunks = [
        _Chunk("a", "d1", "sss.pdf", 1, "מידע כללי על החברה.", 0.7),
        _Chunk("b", "d1", "sss.pdf", 1, "רישיון נהיגה תקף נדרש לנהיגה ברכב.", 0.65),
    ]
    ranked = rerank(chunks, "האם צריך רישיון נהיגה תקף?", top=2)
    assert ranked[0].chunk_id == "b"  # keyword overlap wins despite lower vector


def test_build_context_block_caps_and_dedupes_sources():
    chunks = [_Chunk(f"c{i}", "d1", "sss.pdf", 1, f"{_PARA} וריאציה {i}", 0.9 - i * 0.05)
              for i in range(8)]
    context, citations = build_context_block(chunks, "רישיון נהיגה")
    assert context.count("CONTEXT") == 1
    # At most MAX_CONTEXT_CHUNKS, and sources deduped by (document, page) -> one.
    assert len(citations) == 1
    assert citations[0].document_title == "sss.pdf"


def test_answer_shorter_than_context():
    context = "\n".join([_PARA] * 8)
    answer = clean_answer(" ".join([_PARA] * 8))
    assert len(answer) < len(context)
