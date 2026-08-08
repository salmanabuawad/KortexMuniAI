"""OCR that preserves word coordinates (Stages C/D) + image preprocessing.

pytesseract.image_to_data gives per-word boxes + confidence, so OCR output feeds
the SAME layout/scoring engine as native PDF words. Preprocessing (grayscale,
denoise, adaptive threshold, deskew) improves scanned-document accuracy while
preserving Hebrew.
"""

from __future__ import annotations

import io

from app.core.logging import get_logger
from app.vehicles.extraction.schemas import Word

logger = get_logger("muniai.vehicles.extraction.ocr")

OCR_LANGS = "heb+eng"
RENDER_DPI = 300


def _preprocess(pil_img):
    """Grayscale + denoise + adaptive threshold + deskew using OpenCV if present."""
    try:
        import cv2
        import numpy as np
    except ImportError:  # pragma: no cover — OpenCV optional
        return pil_img.convert("L")

    import numpy as np  # noqa: F811
    img = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    # Deskew based on text pixel orientation.
    coords = np.column_stack(np.where(thr < 255))
    if coords.size:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            h, w = thr.shape
            m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            thr = cv2.warpAffine(thr, m, (w, h), flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
    from PIL import Image
    return Image.fromarray(thr)


def _words_from_image(pil_img, page: int, langs: str) -> list[Word]:
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(pil_img, lang=langs, output_type=Output.DICT)
    words: list[Word] = []
    for i, text in enumerate(data["text"]):
        if not text.strip():
            continue
        conf = float(data["conf"][i])
        if conf < 0:
            conf = 0.0
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append(Word(text, x, y, x + w, y + h, page=page,
                          conf=conf / 100.0, source="tesseract"))
    return words


def ocr_pdf_words(path: str, langs: str = OCR_LANGS) -> dict[int, list[Word]]:
    """Render each PDF page and OCR to positioned words."""
    try:
        import fitz
        from PIL import Image
    except ImportError:  # pragma: no cover
        logger.warning("PyMuPDF/Pillow missing; cannot OCR PDF.")
        return {}
    out: dict[int, list[Word]] = {}
    with fitz.open(path) as doc:
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=RENDER_DPI)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            try:
                img = _preprocess(img)
                out[idx] = _words_from_image(img, idx, langs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OCR failed on page %d: %s", idx, exc)
                out[idx] = []
    return out


def ocr_region(path: str, page_no: int, rect_pts: tuple[float, float, float, float],
               langs: str = OCR_LANGS) -> list[Word]:
    """OCR a rectangular region (in PDF points) of one page (Stage C).

    Returns words in the SAME point coordinate space as native PDF words, so they
    merge cleanly for scoring."""
    try:
        import fitz
        from PIL import Image
    except ImportError:  # pragma: no cover
        return []
    x0, y0, x1, y1 = rect_pts
    scale = RENDER_DPI / 72.0
    try:
        with fitz.open(path) as doc:
            page = doc[page_no - 1]
            clip = fitz.Rect(x0, y0, x1, y1)
            pix = page.get_pixmap(dpi=RENDER_DPI, clip=clip)
            img = _preprocess(Image.open(io.BytesIO(pix.tobytes("png"))))
            px_words = _words_from_image(img, page_no, langs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Region OCR failed: %s", exc)
        return []
    # Convert pixel boxes back to page points and offset by the clip origin.
    out: list[Word] = []
    for w in px_words:
        out.append(Word(
            w.text,
            x0 + w.x0 / scale, y0 + w.y0 / scale,
            x0 + w.x1 / scale, y0 + w.y1 / scale,
            page=page_no, conf=w.conf, source="tesseract_region",
        ))
    return out


def ocr_image_words(path: str, langs: str = OCR_LANGS) -> dict[int, list[Word]]:
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return {}
    try:
        img = _preprocess(Image.open(path))
        return {1: _words_from_image(img, 1, langs)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed for image %s: %s", path, exc)
        return {1: []}
