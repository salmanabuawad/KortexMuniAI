"""Deterministic field extraction from vehicle-document text.

Text comes from PDF/text extraction or an OCR backend. Extraction here is
deterministic (regex + keyword lists) and every field carries a confidence and is
marked unverified until a user confirms it (spec ADDITION). The local LLM may
later refine ambiguous fields, but is never the source of truth.

Supports Hebrew + English keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from dateutil import parser as dateparser

from app.models.enums import InsuranceType, VehicleDocumentType
from app.vehicles.normalization import normalize_registration

# Known Israeli insurers (Hebrew + a few English forms).
INSURERS = [
    "הראל", "כלל", "מגדל", "הפניקס", "מנורה", "איילון", "שלמה", "ביטוח ישיר",
    "הכשרה", "AIG", "Harel", "Clal", "Migdal", "Phoenix", "Menora",
]

_PLATE_RE = re.compile(r"\b\d{2,3}-?\d{2,3}-?\d{2,3}\b")
_DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b")
_POLICY_RE = re.compile(
    r"(?:פוליסה|מספר פוליסה|policy(?:\s*(?:no|number|#))?)\D{0,10}([A-Za-z0-9\-/]{5,20})",
    re.IGNORECASE,
)
_VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")


@dataclass
class ExtractedField:
    value: str | None
    confidence: float
    source_page: int | None = 1


@dataclass
class VehicleExtraction:
    document_type: VehicleDocumentType
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    insurance_type: InsuranceType | None = None
    dates: list[date] = field(default_factory=list)


def classify_document(text: str, filename: str = "") -> tuple[VehicleDocumentType, float]:
    t = text.lower()
    if any(k in text for k in ("רישיון רכב", "רשיון רכב")) or "vehicle registration" in t:
        return VehicleDocumentType.VEHICLE_REGISTRATION, 0.8
    if "חובה" in text or "compulsory" in t:
        return VehicleDocumentType.COMPULSORY_INSURANCE, 0.75
    if "מקיף" in text or "comprehensive" in t:
        return VehicleDocumentType.COMPREHENSIVE_INSURANCE, 0.75
    if "צד ג" in text or "צד שלישי" in text or "third party" in t:
        return VehicleDocumentType.THIRD_PARTY_INSURANCE, 0.75
    if "טסט" in text or "inspection" in t or "roadworthiness" in t:
        return VehicleDocumentType.VEHICLE_TEST, 0.6
    return VehicleDocumentType.UNKNOWN_VEHICLE_DOCUMENT, 0.3


def _insurance_type(text: str) -> InsuranceType | None:
    if "מקיף" in text or "comprehensive" in text.lower():
        return InsuranceType.COMPREHENSIVE
    if "חובה" in text or "compulsory" in text.lower():
        return InsuranceType.COMPULSORY
    if "צד ג" in text or "צד שלישי" in text or "third party" in text.lower():
        return InsuranceType.THIRD_PARTY
    return None


def _parse_dates(text: str) -> list[date]:
    out: list[date] = []
    for m in _DATE_RE.finditer(text):
        try:
            out.append(dateparser.parse(m.group(0), dayfirst=True).date())
        except (ValueError, OverflowError):
            continue
    return sorted(set(out))


def extract(text: str, filename: str = "") -> VehicleExtraction:
    doc_type, doc_conf = classify_document(text, filename)
    ex = VehicleExtraction(document_type=doc_type)
    ex.fields["document_type"] = ExtractedField(doc_type.value, doc_conf)

    plate = _PLATE_RE.search(text)
    if plate:
        ex.fields["registration_number"] = ExtractedField(
            normalize_registration(plate.group(0)), 0.7
        )

    vin = _VIN_RE.search(text)
    if vin:
        ex.fields["vin"] = ExtractedField(vin.group(0), 0.7)

    policy = _POLICY_RE.search(text)
    if policy:
        ex.fields["policy_number"] = ExtractedField(policy.group(1), 0.6)

    for insurer in INSURERS:
        if insurer in text:
            ex.fields["insurer"] = ExtractedField(insurer, 0.6)
            break

    ex.insurance_type = _insurance_type(text)
    if ex.insurance_type:
        ex.fields["insurance_type"] = ExtractedField(ex.insurance_type.value, 0.6)

    ex.dates = _parse_dates(text)
    if ex.dates:
        # Heuristic: earliest = start/issue, latest = end/expiry. Low confidence —
        # user review required (deterministic dedup/overlap runs on confirmed data).
        ex.fields["start_date"] = ExtractedField(ex.dates[0].isoformat(), 0.4)
        ex.fields["end_date"] = ExtractedField(ex.dates[-1].isoformat(), 0.4)
    return ex
