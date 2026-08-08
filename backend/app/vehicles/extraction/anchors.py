"""Hebrew field-label anchors and conservative fuzzy matching.

The extractor must prefer precision over recall.  A false label hit is far more
harmful than a missed label because it can assign an ID/date/amount to the wrong
vehicle field.  In particular, short generic Hebrew words ("ביטוח", "רכב",
"סוכן", etc.) are never allowed to match a longer label merely because they are
substrings of it.
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


# Keep anchors specific.  Avoid generic one-word aliases such as "רישוי",
# "סוכן", "שנה", "נפח" or "המבוטח" which occur throughout policy wording and
# previously created hundreds of false field labels.
ANCHORS: dict[str, list[str]] = {
    "vehicle_number": [
        "מס' רישוי", "מספר רישוי", "מס רישוי", "מס׳ רישוי",
        "מספר הרכב", "מס' רכב", "מספר רכב", "מס הרכב",
    ],
    "id_number": [
        "מס' זהות / ח\"פ", "מס' זהות", "מספר זהות", "ת.ז", "ת\"ז",
        "תעודת זהות", "ח.פ", "ח\"פ", "ח.פ.", "מספר עוסק",
    ],
    "policy_number": [
        "מס' פוליסה", "מספר פוליסה", "פוליסה מספר", "פוליסה מס'", "מס פוליסה",
    ],
    "policy_holder": [
        "שם בעל הפוליסה", "בעל הפוליסה", "שם המבוטח",
    ],
    "address": ["כתובת בעל הפוליסה", "כתובת המבוטח"],
    "agent_number": ["מס' סוכן", "מספר סוכן", "מס' סוכן משני", "מספר סוכן משני"],
    "chassis": ["מספר שלדה", "מס' שלדה"],
    "manufacturer": ["שם היצרן והדגם", "שם היצרן", "יצרן", "תוצר"],
    "model": ["דגם הרכב", "דגם"],
    "engine_capacity": ["נפח מנוע", "נפח מנוע / הספק"],
    "production_year": ["שנת ייצור", "שנת יצור", "שנת ייצור / מועד עליה לכביש"],
    "insurance_start": [
        "מועד תחילת הביטוח", "תחילת הביטוח", "תחילת ביטוח", "מתאריך",
        "בתוקף מ", "החל מ", "תקופת הביטוח מ",
    ],
    "insurance_end": [
        "מועד פקיעת הביטוח", "פקיעת הביטוח", "תום הביטוח", "סיום הביטוח",
        "עד תאריך", "בתוקף עד", "תקופת הביטוח עד",
    ],
    "premium": ["דמי ביטוח", "פרמיה", "סה\"כ לתשלום", "סך לתשלום", "סכום"],
    "insurer": ["חברת הביטוח", "שם המבטח"],
}

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

MATCH_THRESHOLD = 0.86


def _word_count(s: str) -> int:
    return len([p for p in s.split() if p])


def best_field_for_phrase(phrase: str) -> tuple[str | None, float]:
    """Return (field_key, score) for a phrase that genuinely looks like a label.

    Important asymmetry: an anchor may be contained in a slightly longer phrase
    (e.g. ``"מס' רישוי רכב"``), but a short phrase is *not* accepted merely
    because it is contained inside a longer anchor.  That old behaviour made
    ``"תעודת"`` match ``"תעודת זהות"`` and ``"ביטוח"`` match many date fields.
    """
    norm = normalize_label(phrase)
    if not norm:
        return None, 0.0

    best_key: str | None = None
    best_score = 0.0
    n_words = _word_count(norm)

    for key, variants in ANCHORS.items():
        for v in variants:
            nv = normalize_label(v)
            v_words = _word_count(nv)

            if norm == nv:
                score = 1.0
            elif v_words >= 2 and nv in norm and n_words <= v_words + 1:
                # Label with one harmless surrounding word.
                score = 0.90
            else:
                # Fuzzy matching is only for similarly-sized phrases, which
                # catches OCR errors without matching unrelated fragments.
                if abs(n_words - v_words) > 0 or abs(len(norm) - len(nv)) > max(3, len(nv) // 4):
                    score = 0.0
                else:
                    score = _ratio(norm, nv)
            if score > best_score:
                best_score, best_key = score, key

    return (best_key, best_score) if best_score >= MATCH_THRESHOLD else (None, best_score)
