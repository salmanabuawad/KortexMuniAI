"""Mandatory (compulsory) insurance certificate extractor — תעודת ביטוח חובה."""

from __future__ import annotations

import re
from datetime import datetime

from app.models.enums import InsuranceType
from app.vehicles.extraction.extractors.base import (
    add_simple_fields,
    add_vehicle_number,
    detect_insurer,
)
from app.vehicles.extraction.extractors.general_insurance import extract as extract_insurance
from app.vehicles.extraction.layout import LabelHit
from app.vehicles.extraction.schemas import ExtractionResult, Field, Word

_DATE = r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})"


def _iso_date(value: str) -> str | None:
    value = value.replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _labelled_date(text: str, labels: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Extract a date immediately before or after a Hebrew date label.

    PyMuPDF commonly emits RTL lines as ``DATE :LABEL``; OCR often emits
    ``LABEL: DATE``.  Support both without asking an LLM to interpret prose.
    """
    for label in labels:
        esc = re.escape(label)
        patterns = (
            rf"{_DATE}\s*:?\s*{esc}",
            rf"{esc}\s*:?\s*{_DATE}",
        )
        for pat in patterns:
            m = re.search(pat, text or "")
            if m:
                # one of the alternatives contains the date as group 1
                raw = next((g for g in m.groups() if g and re.match(r"\d", g)), None)
                iso = _iso_date(raw or "")
                if iso:
                    return iso, label
    return None, None


def _premium(text: str) -> str | None:
    # RTL native PDF: "₪ 234.00 :דמי ביטוח" / "ש\"ח234.00 :סכום"
    pats = (
        r"₪\s*([0-9][0-9,]*\.\d{2})\s*:?\s*דמי\s*ביטוח",
        r"(?:ש\s*[\"׳״']?\s*ח|₪)?\s*([0-9][0-9,]*\.\d{2})\s*:?\s*סכום",
        r"דמי\s*ביטוח\s*:?\s*(?:₪|ש\s*[\"׳״']?\s*ח)?\s*([0-9][0-9,]*\.\d{2})",
    )
    for pat in pats:
        m = re.search(pat, text or "")
        if m:
            return m.group(1).replace(",", "")
    return None


def extract(result: ExtractionResult, words: list[Word], labels: list[LabelHit], text: str) -> None:
    extract_insurance(result, words, labels, text)

    # Mandatory-insurance certificates usually print these dates in a sentence,
    # not in isolated table cells.  Exact labelled regex is safer than picking the
    # nearest arbitrary date token from dense policy wording.
    start, start_label = _labelled_date(text, ("מועד תחילת הביטוח", "תחילת הביטוח"))
    end, end_label = _labelled_date(text, ("מועד פקיעת הביטוח", "פקיעת הביטוח", "תום הביטוח"))
    if start:
        result.fields["insurance_start"] = Field(
            value=start, confidence=0.98, source="labelled_regex", page=1,
            label_detected=start_label, reason="date adjacent to explicit insurance-start label",
        )
    if end:
        result.fields["insurance_end"] = Field(
            value=end, confidence=0.98, source="labelled_regex", page=1,
            label_detected=end_label, reason="date adjacent to explicit insurance-expiry label",
        )

    premium = _premium(text)
    if premium:
        result.fields["premium"] = Field(
            value=premium, confidence=0.97, source="labelled_regex", page=1,
            label_detected="דמי ביטוח/סכום", reason="amount adjacent to explicit premium label",
        )

    # Re-run insurer signature after generic extraction so common Hebrew words can
    # never leave a false company name such as "כלל" behind.
    insurer = detect_insurer(text)
    if insurer:
        result.fields["insurer"] = insurer

    result.fields["insurance_type"] = Field(
        value=InsuranceType.COMPULSORY.value,
        confidence=result.document_type_confidence,
        source="classifier",
        reason="mandatory-insurance document",
    )


__all__ = ["extract", "add_simple_fields", "add_vehicle_number", "detect_insurer"]
