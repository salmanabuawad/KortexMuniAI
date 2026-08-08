from __future__ import annotations

from app.documents.chunking import PageText, chunk_page_text, chunk_plain_text


def test_short_text_single_chunk():
    chunks = chunk_plain_text("hello world this is short")
    assert len(chunks) == 1
    assert chunks[0].position == 0
    assert chunks[0].page == 1


def test_long_text_splits_with_overlap():
    words = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_plain_text(words, chunk_words=100, overlap_words=20)
    assert len(chunks) > 1
    # positions are sequential
    assert [c.position for c in chunks] == list(range(len(chunks)))
    # overlap: last 20 words of chunk 0 reappear at start of chunk 1
    c0_tail = chunks[0].content.split()[-20:]
    c1_head = chunks[1].content.split()[:20]
    assert c0_tail == c1_head


def test_chunks_never_cross_pages():
    pages = [PageText(1, " ".join(f"a{i}" for i in range(300))),
             PageText(2, " ".join(f"b{i}" for i in range(300)))]
    chunks = chunk_page_text(pages, chunk_words=100, overlap_words=10)
    for c in chunks:
        toks = set(c.content.split())
        assert not (any(t.startswith("a") for t in toks) and any(t.startswith("b") for t in toks))


def test_empty_pages_skipped():
    chunks = chunk_page_text([PageText(1, ""), PageText(2, "real content here")])
    assert len(chunks) == 1
    assert chunks[0].page == 2
