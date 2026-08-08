"""Shared insurance extractor (comprehensive / third-party / base for mandatory)."""

from __future__ import annotations

from app.vehicles.extraction.extractors.base import (
    add_simple_fields,
    add_vehicle_number,
    detect_insurer,
)
from app.vehicles.extraction.layout import LabelHit
from app.vehicles.extraction.schemas import ExtractionResult, Word


def extract(result: ExtractionResult, words: list[Word], labels: list[LabelHit], text: str) -> None:
    add_vehicle_number(result, words, labels)
    add_simple_fields(
        result, words, labels,
        numeric=("id_number", "agent_number", "engine_capacity", "production_year"),
        raw=("policy_number", "premium"),
        text=("policy_holder", "manufacturer", "model"),
        dates=("insurance_start", "insurance_end"),
    )
    ins = detect_insurer(text)
    if ins and "insurer" not in result.fields:
        result.fields["insurer"] = ins
