"""Field-aware, layout-aware vehicle-document extraction.

Replaces naive "grab any number" OCR. The pipeline classifies the document, then
uses Hebrew label anchors + word coordinates (native PDF words or OCR word boxes)
to resolve each field to the value spatially/textually associated with its label.
Vehicle-number selection is a scored candidate ranking (see candidate_scoring).

Local-only: PyMuPDF / pdfplumber / Tesseract. No external AI, no API keys.
"""

from app.vehicles.extraction.pipeline import extract_document, extract_from_words  # noqa: F401
from app.vehicles.extraction.schemas import (  # noqa: F401
    Candidate,
    ExtractionResult,
    Field,
    Word,
)

__all__ = [
    "extract_document",
    "extract_from_words",
    "ExtractionResult",
    "Field",
    "Candidate",
    "Word",
]
