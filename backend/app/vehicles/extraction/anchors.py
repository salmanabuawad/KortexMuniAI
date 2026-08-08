"""Hebrew field-label anchors and fuzzy matching.

Uses rapidfuzz when available (fast, better Unicode handling); falls back to
stdlib difflib so the core logic and tests run without the optional dependency.
"""

from __future__ import annotations

from app.vehicles.extraction.normalizer import normalize_label

try:  # optional dependency
    from rapidfuzz import fuzz as _rf

    def _ratio(a: str, b: str) -> float:
        return _rf.ratio(a, b) / 100.0
except ImportError:  # pragma: no cover - fallback
    from difflib import SequenceMatcher

    def _ratio(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()


# field_key -> list of accepted Hebrew label variants.
ANCHORS: dict[str, list[str]] = {
    "vehicle_number": [
        "מס' רישוי", "מספר רישוי", "מס רישוי", "מס׳ רישוי",
        "מספר הרכב", "מס' רכב", "מספר רכב", "מס הרכב", "רישוי",
    ],
    "id_number": [
        "מס' זהות / ח\"פ", "מס' זהות", "מספר זהות", "ת.ז", "ת\"ז", "תעודת זהות",
        "ח.פ", "ח\"פ", "ח.פ.", "מספר עוסק",
    ],
    "policy_number": [
        "מס' פוליסה", "מספר פוליסה", "פוליסה מספר", "פוליסה מס'", "מס פוליסה",
    ],
    "policy_holder": [
        "בעל הפוליסה", "שם בעל הפוליסה", "שם המבוטח", "המבוטח", "בעל הרכב",
    ],
    "agent_number": ["מס' סוכן", "מספר סוכן", "סוכן"],
    "chassis": ["מספר שלדה", "מס' שלדה", "שלדה"],
    "manufacturer": ["תוצר", "יצרן"],
    "model": ["דגם"],
    "engine_capacity": ["נפח מנוע", "נפח"],
    "production_year": ["שנת ייצור", "שנת יצור", "שנה"],
    "insurance_start": ["תחילת הביטוח", "תחילת ביטוח", "מתאריך", "בתוקף מ", "החל מ", "תקופת הביטוח מ"],
    "insurance_end": ["תום הביטוח", "סיום הביטוח", "עד תאריך", "בתוקף עד", "תקופת הביטוח עד"],
    "premium": ["פרמיה", "דמי ביטוח", "סה\"כ לתשלום", "סך לתשלום"],
    "insurer": ["חברת הביטוח", "המבטח", "שם המבטח"],
}

# Document-classification term sets.
DOC_TERMS: dict[str, list[str]] = {
    "mandatory_insurance": [
        "תעודת ביטוח חובה", "ביטוח חובה", "פקודת ביטוח רכב מנועי", "פקודת ביטוח",
    ],
    "third_party_insurance": ["צד ג'", "צד ג", "צד שלישי"],
    "comprehensive_insurance": ["ביטוח מקיף", "מקיף"],
    "vehicle_registration": [
        "רישיון רכב", "רשיון רכב", "משרד התחבורה", "אגף הרכב",
    ],
    "vehicle_test": ["טסט", "מבחן רכב", "בדיקת רכב", "תקינות"],
    "protection_approval": ["אישור מיגון", "מיגון"],
    "repair_invoice": ["חשבונית", "מוסך", "תיקון", "חשבונית מס"],
    "warranty": ["אחריות", "כתב אחריות"],
}

MATCH_THRESHOLD = 0.82


def best_field_for_phrase(phrase: str) -> tuple[str | None, float]:
    """Return (field_key, score) for the anchor best matching a label phrase."""
    norm = normalize_label(phrase)
    if not norm:
        return None, 0.0
    best_key: str | None = None
    best_score = 0.0
    for key, variants in ANCHORS.items():
        for v in variants:
            nv = normalize_label(v)
            # exact/substring gives a strong score; otherwise fuzzy ratio.
            if norm == nv:
                score = 1.0
            elif nv in norm or norm in nv:
                score = 0.95
            else:
                score = _ratio(norm, nv)
            if score > best_score:
                best_score, best_key = score, key
    return (best_key, best_score) if best_score >= MATCH_THRESHOLD else (None, best_score)
