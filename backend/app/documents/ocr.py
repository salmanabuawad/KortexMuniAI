"""Local OCR for scanned/photographed documents (spec §12).

Uses Tesseract (via pytesseract) with Arabic + Hebrew + English by default. For
scanned PDFs, pages are rendered to images with PyMuPDF and OCR'd per page so
citations keep their page numbers. All heavy imports are lazy so the core API
runs even when the OCR extra is not installed.

The original OCR text is what gets indexed; nothing is sent to any cloud service.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger("muniai.documents.ocr")

# Tesseract language codes. Requires: tesseract-ocr-ara, -heb, -eng on the host.
OCR_LANGS = "ara+heb+eng"
RENDER_DPI = 300


@dataclass
class OcrPage:
    page: int
    text: str


def _register_heif() -> None:
    """Enable HEIC/HEIF (iPhone photos) in Pillow if pillow-heif is installed."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except Exception:  # noqa: BLE001 — optional
        pass


_register_heif()


def _tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def ocr_image_bytes(data: bytes, langs: str = OCR_LANGS) -> str:
    import pytesseract
    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        return pytesseract.image_to_string(img, lang=langs) or ""


def ocr_image_file(path: str, langs: str = OCR_LANGS) -> str:
    import pytesseract
    from PIL import Image

    with Image.open(path) as img:
        return pytesseract.image_to_string(img, lang=langs) or ""


def ocr_pdf_pages(path: str, langs: str = OCR_LANGS) -> list[OcrPage]:
    """Render each PDF page to an image and OCR it. Returns per-page text."""
    import fitz  # PyMuPDF

    pages: list[OcrPage] = []
    with fitz.open(path) as doc:
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=RENDER_DPI)
            text = ocr_image_bytes(pix.tobytes("png"), langs)
            pages.append(OcrPage(idx, text))
    return pages


def ocr_document(path: str, file_type: str, langs: str = OCR_LANGS) -> list[OcrPage]:
    """OCR an image or scanned PDF into per-page text. Empty list if OCR is
    unavailable or yields nothing."""
    if not _tesseract_available():
        logger.warning("Tesseract/Pillow not installed; OCR unavailable.")
        return []
    ext = (file_type or "").lower()
    try:
        if ext == "pdf":
            return [p for p in ocr_pdf_pages(path, langs) if p.text.strip()]
        if ext in ("png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp", "heic"):
            text = ocr_image_file(path, langs)
            return [OcrPage(1, text)] if text.strip() else []
    except Exception as exc:  # noqa: BLE001 — OCR must never crash ingestion
        logger.warning("OCR failed for %s: %s", path, exc)
    return []
