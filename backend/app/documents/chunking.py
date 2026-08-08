"""Deterministic text chunking for RAG.

Splits extracted text into overlapping, roughly token-bounded chunks while
preserving page attribution. Pure function — unit-tested without a DB/model.
Token count is approximated by whitespace words (good enough for sizing; the
embedding model enforces its own limits).
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CHUNK_WORDS = 220
DEFAULT_OVERLAP_WORDS = 40


@dataclass(frozen=True)
class Chunk:
    position: int
    content: str
    page: int | None = None


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def _split_words(text: str) -> list[str]:
    return text.split()


def chunk_page_text(
    pages: list[PageText],
    *,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[Chunk]:
    """Chunk a list of pages, keeping each chunk within a single page so the
    citation's page number stays accurate."""
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    overlap = max(0, min(overlap_words, chunk_words - 1))
    step = chunk_words - overlap

    chunks: list[Chunk] = []
    pos = 0
    for page in pages:
        words = _split_words(page.text)
        if not words:
            continue
        i = 0
        while i < len(words):
            window = words[i : i + chunk_words]
            content = " ".join(window).strip()
            if content:
                chunks.append(Chunk(position=pos, content=content, page=page.page))
                pos += 1
            if i + chunk_words >= len(words):
                break
            i += step
    return chunks


def chunk_plain_text(
    text: str,
    *,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[Chunk]:
    return chunk_page_text(
        [PageText(page=1, text=text)],
        chunk_words=chunk_words,
        overlap_words=overlap_words,
    )
