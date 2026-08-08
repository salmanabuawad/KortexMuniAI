"""Extraction pipeline facade — multi-stage (spec §10).

Stage A: native PDF text + word coordinates.
Stage B: classify + rule-based, layout-aware field extraction.
Stage C: region OCR around an unresolved vehicle-number label.
Stage D: full-page OCR only if native text is missing/insufficient.
Stage E: candidate ranking + validation (inside the extractors/scoring).
"""

from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.vehicles.extraction.classifier import classify_document
from app.vehicles.extraction.extractors import (
    general_insurance,
    mandatory_insurance,
    vehicle_registration,
)
from app.vehicles.extraction.layout import LabelHit, find_label_hits
from app.vehicles.extraction.schemas import ExtractionResult, Word

logger = get_logger("muniai.vehicles.extraction.pipeline")

_EXTRACTORS = {
    "mandatory_insurance": mandatory_insurance.extract,
    "comprehensive_insurance": general_insurance.extract,
    "third_party_insurance": general_insurance.extract,
    "vehicle_registration": vehicle_registration.extract,
}


def _dispatch(key: str):
    return _EXTRACTORS.get(key, general_insurance.extract)


def extract_from_words(
    words_by_page: dict[int, list[Word]],
    filename: str = "",
    full_text: str | None = None,
    ocr_engine: str = "pdf_text",
) -> ExtractionResult:
    words: list[Word] = [w for page in words_by_page.values() for w in page]
    text = full_text if full_text is not None else " ".join(w.text for w in words)

    key, enum, conf = classify_document(text, filename)
    labels = find_label_hits(words)

    result = ExtractionResult(
        document_type=enum.value,
        document_type_confidence=conf,
        raw_text=text,
        ocr_engine=ocr_engine,
    )
    result.anchors_detected = sorted({h.text for h in labels})
    _dispatch(key)(result, words, labels, text)
    return result


def _region_for_label(lab: LabelHit) -> tuple[float, float, float, float]:
    w = lab.x1 - lab.x0 or 40
    h = lab.y1 - lab.y0 or 12
    # RTL: value below and to the left of the label; take a generous box.
    return (max(0.0, lab.x0 - 4 * w), lab.y0 - 0.3 * h, lab.x1 + w, lab.y0 + 8 * h)


def extract_document(path: str, file_type: str | None = None) -> ExtractionResult:
    ext = (file_type or Path(path).suffix.lstrip(".")).lower()

    if ext == "pdf":
        from app.vehicles.extraction.pdf_extractor import extract_pdf_words

        words_by_page, text, needs_ocr = extract_pdf_words(path)

        if not needs_ocr and any(words_by_page.values()):
            result = extract_from_words(words_by_page, Path(path).name, text, "pdf_text")

            # Stage C: region OCR if the vehicle number wasn't resolved natively.
            if "vehicle_number" not in result.fields:
                labels = find_label_hits([w for p in words_by_page.values() for w in p])
                veh_labels = [h for h in labels if h.field == "vehicle_number"]
                if veh_labels:
                    from app.vehicles.extraction.ocr_layout import ocr_region

                    for lab in veh_labels:
                        extra = ocr_region(path, lab.page, _region_for_label(lab))
                        if extra:
                            words_by_page.setdefault(lab.page, []).extend(extra)
                    result = extract_from_words(words_by_page, Path(path).name, text, "pdf_text+region_ocr")

            if "vehicle_number" in result.fields:
                return result
            # else fall through to full OCR (Stage D)

        # Stage D: full-page OCR.
        from app.vehicles.extraction.ocr_layout import ocr_pdf_words

        ocr_words = ocr_pdf_words(path)
        ocr_text = " ".join(w.text for p in ocr_words.values() for w in p)
        return extract_from_words(ocr_words, Path(path).name, ocr_text or text, "tesseract")

    if ext in ("png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp", "heic"):
        from app.vehicles.extraction.ocr_layout import ocr_image_words

        ocr_words = ocr_image_words(path)
        text = " ".join(w.text for p in ocr_words.values() for w in p)
        return extract_from_words(ocr_words, Path(path).name, text, "tesseract")

    # Plain text / other: no coordinates; classification + regex only.
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        raw = ""
    return extract_from_words({}, Path(path).name, raw, "text")
