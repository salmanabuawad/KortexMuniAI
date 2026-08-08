"""Data structures for the extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Word:
    """A positioned token from native PDF text or OCR word boxes.

    Coordinates are in a top-left origin (y grows downward), page-pixel or PDF
    units — only relative geometry matters to the scorer.
    """

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 1
    conf: float = 1.0
    source: str = "pdf_text"

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return max(1.0, self.y1 - self.y0)


@dataclass
class Field:
    value: str | None
    confidence: float = 0.0
    source: str = "pdf_text"          # pdf_text | pdf_text_layout | tesseract | regex | layout
    page: int = 1
    label_detected: str | None = None
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "page": self.page,
            "label_detected": self.label_detected,
            "reason": self.reason,
        }


@dataclass
class Candidate:
    value: str
    score: float
    label: str | None = None
    reason: str = ""
    page: int = 1
    selected: bool = False

    def as_dict(self) -> dict:
        return {
            "value": self.value,
            "score": round(self.score, 1),
            "label": self.label,
            "reason": self.reason,
            "page": self.page,
            "selected": self.selected,
        }


@dataclass
class ExtractionResult:
    document_type: str
    document_type_confidence: float
    fields: dict[str, Field] = field(default_factory=dict)
    vehicle_candidates: list[Candidate] = field(default_factory=list)
    anchors_detected: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_text: str = ""
    ocr_engine: str = "none"
    processing_version: str = "2.0"

    def field_value(self, name: str) -> str | None:
        f = self.fields.get(name)
        return f.value if f else None

    def as_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "document_type_confidence": round(self.document_type_confidence, 3),
            "fields": {k: v.as_dict() for k, v in self.fields.items()},
            "vehicle_candidates": [c.as_dict() for c in self.vehicle_candidates],
            "anchors_detected": self.anchors_detected,
            "warnings": self.warnings,
            "ocr_engine": self.ocr_engine,
            "processing_version": self.processing_version,
        }
