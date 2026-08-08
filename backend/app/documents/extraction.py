"""Text extraction from uploaded documents.

Supported without OCR: TXT, PDF (PyMuPDF), DOCX (python-docx), CSV.
Scanned/image PDFs and images require OCR (app/documents/ocr.py) — wired in the
document pipeline. Heavy libraries are imported lazily so the core API runs even
when the optional ``documents`` extra is not installed.

Returns pages (with page numbers) so chunking can preserve citations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger("muniai.documents.extraction")


@dataclass
class ExtractionResult:
    pages: list  # list[PageText-like]: objects with .page and .text
    language: str | None = None
    needs_ocr: bool = False


@dataclass
class _Page:
    page: int
    text: str


def _from_txt(path: Path) -> list[_Page]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [_Page(1, text)]


def _from_pdf(path: Path) -> tuple[list[_Page], bool]:
    """Extract per-page text with PyMuPDF. Returns (pages, needs_ocr)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning("PyMuPDF not installed; cannot extract PDF text.")
        return [], True

    pages: list[_Page] = []
    total_chars = 0
    with fitz.open(path) as doc:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            total_chars += len(text.strip())
            pages.append(_Page(idx, text))
    # A PDF with almost no extractable text is almost certainly scanned images.
    needs_ocr = total_chars < 20 * max(1, len(pages))
    return pages, needs_ocr


def _from_docx(path: Path) -> list[_Page]:
    try:
        import docx  # python-docx
    except ImportError:  # pragma: no cover
        logger.warning("python-docx not installed; cannot extract DOCX text.")
        return []
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return [_Page(1, text)]


def extract_text(path: str | Path, file_type: str | None = None) -> ExtractionResult:
    p = Path(path)
    ext = (file_type or p.suffix.lstrip(".")).lower()

    if ext in ("txt", "md", "csv", "log"):
        return ExtractionResult(pages=_from_txt(p))
    if ext == "pdf":
        pages, needs_ocr = _from_pdf(p)
        return ExtractionResult(pages=pages, needs_ocr=needs_ocr)
    if ext in ("docx",):
        return ExtractionResult(pages=_from_docx(p))
    if ext in ("png", "jpg", "jpeg", "tif", "tiff", "heic"):
        # Images always need OCR.
        return ExtractionResult(pages=[], needs_ocr=True)

    logger.info("Unsupported extension '%s'; treating as plain text.", ext)
    return ExtractionResult(pages=_from_txt(p))
