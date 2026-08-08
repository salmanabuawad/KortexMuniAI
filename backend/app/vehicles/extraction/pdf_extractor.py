"""Native PDF text + word-coordinate extraction (Stage A).

Prefers PyMuPDF words (with coordinates). Falls back to pdfplumber. Detects when
a page is scanned (little/no native text) so the pipeline can OCR only then.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.vehicles.extraction.schemas import Word

logger = get_logger("muniai.vehicles.extraction.pdf")


def extract_pdf_words(path: str) -> tuple[dict[int, list[Word]], str, bool]:
    """Return (words_by_page, full_text, needs_ocr)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:  # pragma: no cover
        logger.warning("PyMuPDF not installed; cannot read PDF natively.")
        return {}, "", True

    words_by_page: dict[int, list[Word]] = {}
    texts: list[str] = []
    total_chars = 0
    with fitz.open(path) as doc:
        page_count = doc.page_count
        for idx, page in enumerate(doc, start=1):
            page_words: list[Word] = []
            # (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            for x0, y0, x1, y1, text, *_ in page.get_text("words"):
                if text.strip():
                    page_words.append(Word(text, x0, y0, x1, y1, page=idx,
                                           conf=1.0, source="pdf_text"))
            words_by_page[idx] = page_words
            page_text = page.get_text("text") or ""
            texts.append(page_text)
            total_chars += len(page_text.strip())

    needs_ocr = total_chars < 20 * max(1, page_count)
    return words_by_page, "\n".join(texts), needs_ocr
