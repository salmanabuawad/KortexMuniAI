"""Mandatory (compulsory) insurance certificate extractor — תעודת ביטוח חובה."""

from __future__ import annotations

from app.models.enums import InsuranceType
from app.vehicles.extraction.extractors.base import (
    add_simple_fields,
    add_vehicle_number,
    detect_insurer,
)
from app.vehicles.extraction.extractors.general_insurance import extract as extract_insurance
from app.vehicles.extraction.layout import LabelHit
from app.vehicles.extraction.schemas import ExtractionResult, Field, Word


def extract(result: ExtractionResult, words: list[Word], labels: list[LabelHit], text: str) -> None:
    extract_insurance(result, words, labels, text)
    result.fields["insurance_type"] = Field(
        value=InsuranceType.COMPULSORY.value, confidence=result.document_type_confidence,
        source="classifier", reason="mandatory-insurance document",
    )


__all__ = ["extract", "add_simple_fields", "add_vehicle_number", "detect_insurer"]
