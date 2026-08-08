"""Israeli vehicle registration license extractor — רישיון רכב."""

from __future__ import annotations

from app.vehicles.extraction.extractors.base import add_simple_fields, add_vehicle_number
from app.vehicles.extraction.layout import LabelHit
from app.vehicles.extraction.schemas import ExtractionResult, Word


def extract(result: ExtractionResult, words: list[Word], labels: list[LabelHit], text: str) -> None:
    add_vehicle_number(result, words, labels)
    add_simple_fields(
        result, words, labels,
        numeric=("engine_capacity", "production_year", "id_number"),
        raw=("chassis",),
        text=("manufacturer", "model"),
        dates=(),
    )
