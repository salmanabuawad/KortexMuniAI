"""Deterministic answers for structured vehicle-document questions.

Design principle (per product owner): for KNOWN structured fields, simple
deterministic Python beats asking a small local model to reason over flattened
RTL PDF chunks. The LLM is only used for genuinely open questions.

Flow for a question:
    detect_structured_intent(question)      # deterministic aliases, no LLM
        -> field
    read the field from the document's STORED extraction_json
        -> value + confidence + page
    if confidence high enough -> format a direct answer, cite ONE source

This module is intentionally free of DB/LLM imports in its core so it is trivially
unit-testable; the DB lookup lives in resolve_structured_answer().
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

# --------------------------------------------------------------------------- #
# Intent detection
# --------------------------------------------------------------------------- #

# Full-phrase patterns (unambiguous even inside a longer sentence). conf 0.97.
_FULL_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("vehicle_number", (
        r"מספר\s*(?:ה)?רכב", r"מס[׳'\"]?\s*רישוי", r"מספר\s*רישוי", r"מס[׳'\"]?\s*רכב",
        r"vehicle\s*(?:number|no\.?|registration)", r"plate\s*(?:number|no\.?|#)?",
        r"registration\s*(?:number|no\.?)", r"license\s*plate",
        r"رقم\s*(?:السيارة|المركبة|الترخيص)",
    )),
    ("policy_number", (
        r"מספר\s*(?:ה)?פוליסה", r"מס[׳'\"]?\s*פוליסה",
        r"policy\s*(?:number|no\.?)", r"رقم\s*(?:البوليصة|الوثيقة|وثيقة)",
    )),
    ("insurance_start", (
        r"תחילת\s*(?:ה)?ביטוח", r"מועד\s*תחילת\s*(?:ה)?ביטוח", r"תאריך\s*תחילה",
        r"מתי\s*(?:ה)?ביטוח\s*מתחיל", r"מתי\s*מתחיל",
        r"insurance\s*start", r"start\s*date", r"when\s*does\s*(?:the\s*)?insurance\s*start",
        r"بداية\s*التأمين", r"تاريخ\s*البداية", r"متى\s*يبدأ\s*التأمين",
    )),
    ("insurance_end", (
        r"(?:סיום|תום|פקיעת)\s*(?:ה)?ביטוח", r"מועד\s*פקיעת\s*(?:ה)?ביטוח", r"תאריך\s*סיום",
        r"תוקף\s*(?:ה)?ביטוח", r"עד\s*מתי", r"מתי\s*(?:ה)?ביטוח\s*נגמר", r"מתי\s*נגמר",
        r"insurance\s*(?:end|expiry|expiration)", r"end\s*date", r"expiry\s*date",
        r"when\s*does\s*(?:the\s*)?insurance\s*(?:end|expire)",
        r"نهاية\s*التأمين", r"انتهاء\s*التأمين", r"تاريخ\s*الانتهاء", r"صلاحية\s*التأمين",
        r"متى\s*ينتهي\s*التأمين",
    )),
    ("policy_holder", (
        r"בעל\s*(?:ה)?פוליסה", r"שם\s*(?:ה)?מבוטח", r"מי\s*(?:ה)?מבוטח",
        r"policy\s*holder", r"insured\s*(?:name|party)", r"صاحب\s*(?:البوليصة|الوثيقة)",
    )),
    ("id_number", (
        r"מספר\s*זהות", r"תעודת\s*זהות", r"ת[.\"׳']?\s*ז", r"ח[.\"׳']?\s*פ",
        r"id\s*(?:number|no\.?)", r"رقم\s*الهوية",
    )),
    ("insurer", (
        r"חברת\s*(?:ה)?ביטוח", r"מי\s*(?:ה)?מבטח", r"מי\s*(?:ה)?חברה",
        r"insurer", r"insurance\s*company", r"شركة\s*التأمين",
    )),
    ("premium", (
        r"דמי\s*ביטוח", r"פרמיה", r"עלות\s*(?:ה)?ביטוח", r"כמה\s*(?:עלה|שילמו|עולה)",
        r"premium", r"how\s*much", r"قسط\s*التأمين",
    )),
    ("manufacturer", (
        r"(?:יצרן|תוצר)\s*(?:ה)?רכב", r"manufacturer", r"make", r"صانع\s*(?:السيارة|المركبة)",
    )),
    ("production_year", (
        r"שנת\s*ייצור", r"production\s*year", r"model\s*year", r"سنة\s*الصنع",
    )),
    ("engine_capacity", (
        r"נפח\s*מנוע", r"engine\s*(?:capacity|size)", r"سعة\s*المحرك",
    )),
    ("chassis", (
        r"מספר\s*שלדה", r"מס[׳'\"]?\s*שלדה", r"(?:vin|chassis)\s*(?:number|no\.?)?",
        r"رقم\s*(?:الشاسيه|الهيكل)",
    )),
]

# Short aliases for terse follow-ups ("תחילה", "תום", "רכב"...). Applied ONLY to
# short queries so they never fire inside a long unstructured sentence. conf 0.9.
_SHORT_ALIASES: dict[str, str] = {
    # insurance_start
    "תחילה": "insurance_start", "התחלה": "insurance_start", "מתאריך": "insurance_start",
    "بداية": "insurance_start", "start": "insurance_start",
    # insurance_end
    "תום": "insurance_end", "סיום": "insurance_end", "פקיעה": "insurance_end",
    "תוקף": "insurance_end", "نهاية": "insurance_end", "انتهاء": "insurance_end",
    "expiry": "insurance_end", "expiration": "insurance_end",
    # vehicle_number
    "רכב": "vehicle_number", "רישוי": "vehicle_number", "مركبة": "vehicle_number",
    "سيارة": "vehicle_number", "plate": "vehicle_number",
    # policy_number
    "פוליסה": "policy_number", "بوليصة": "policy_number", "policy": "policy_number",
    # policy_holder
    "מבוטח": "policy_holder", "مؤمن": "policy_holder",
    # id_number
    "זהות": "id_number", "תז": "id_number", "هوية": "id_number",
    # premium
    "מחיר": "premium", "עלות": "premium", "פרמיה": "premium", "سعر": "premium",
    "قسط": "premium", "price": "premium", "cost": "premium",
    # insurer
    "מבטח": "insurer", "insurer": "insurer",
}

_SHORT_MAX_TOKENS = 3
_PUNCT = re.compile(r"[?.!,:;،؟\"'’“”׳״\-]+")


@dataclass
class Intent:
    field: str | None
    confidence: float

    def __bool__(self) -> bool:  # truthy when a field was detected
        return self.field is not None


def _normalize(q: str) -> str:
    q = _PUNCT.sub(" ", q or "")
    return re.sub(r"\s+", " ", q).strip()


def _strip_he_prefix(tok: str) -> str:
    # Drop a leading definite article/prepositions so "הרכב"/"בפוליסה" still match.
    return re.sub(r"^(ה|ל|ב|מ|ש|כ|ו)", "", tok) if len(tok) > 3 else tok


def detect_structured_intent(question: str) -> Intent:
    """Deterministically map a question to a structured field. No LLM."""
    norm = _normalize(question)
    if not norm:
        return Intent(None, 0.0)

    low = norm.lower()
    for field, patterns in _FULL_PATTERNS:
        if any(re.search(p, low, flags=re.IGNORECASE) for p in patterns):
            return Intent(field, 0.97)

    tokens = norm.split()
    if len(tokens) <= _SHORT_MAX_TOKENS:
        for tok in tokens:
            for cand in (tok, tok.lower(), _strip_he_prefix(tok)):
                if cand in _SHORT_ALIASES:
                    return Intent(_SHORT_ALIASES[cand], 0.9)
    return Intent(None, 0.0)


# --------------------------------------------------------------------------- #
# Reading a field from a stored extraction (extraction_json) or a live result
# --------------------------------------------------------------------------- #

@dataclass
class FieldValue:
    value: str
    confidence: float
    page: int
    label: str | None = None
    source: str | None = None


def field_from_extraction_json(extraction_json: dict, field: str) -> FieldValue | None:
    """Read a field from a stored ExtractionResult.as_dict() payload."""
    if not extraction_json:
        return None
    f = (extraction_json.get("fields") or {}).get(field)
    if not f or f.get("value") in (None, ""):
        return None
    return FieldValue(
        value=str(f["value"]).strip(),
        confidence=float(f.get("confidence") or 0.0),
        page=int(f.get("page") or 1),
        label=f.get("label_detected"),
        source=f.get("source"),
    )


# --------------------------------------------------------------------------- #
# Answer formatting
# --------------------------------------------------------------------------- #

_LABELS = {
    "he": {
        "vehicle_number": "מספר הרכב הוא", "policy_number": "מספר הפוליסה הוא",
        "insurance_start": "תחילת הביטוח היא", "insurance_end": "תום הביטוח הוא",
        "policy_holder": "בעל הפוליסה הוא", "id_number": "מספר הזהות הוא",
        "insurer": "חברת הביטוח היא", "premium": "דמי הביטוח הם",
        "manufacturer": "יצרן הרכב הוא", "production_year": "שנת הייצור היא",
        "engine_capacity": "נפח המנוע הוא", "chassis": "מספר השלדה הוא",
    },
    "ar": {
        "vehicle_number": "رقم المركبة هو", "policy_number": "رقم الوثيقة هو",
        "insurance_start": "بداية التأمين هي", "insurance_end": "نهاية التأمين هي",
        "policy_holder": "صاحب الوثيقة هو", "id_number": "رقم الهوية هو",
        "insurer": "شركة التأمين هي", "premium": "قسط التأمين هو",
        "manufacturer": "صانع المركبة هو", "production_year": "سنة الصنع هي",
        "engine_capacity": "سعة المحرك هي", "chassis": "رقم الشاسيه هو",
    },
    "en": {
        "vehicle_number": "Vehicle number:", "policy_number": "Policy number:",
        "insurance_start": "Insurance start:", "insurance_end": "Insurance end:",
        "policy_holder": "Policy holder:", "id_number": "ID number:",
        "insurer": "Insurer:", "premium": "Premium:",
        "manufacturer": "Manufacturer:", "production_year": "Production year:",
        "engine_capacity": "Engine capacity:", "chassis": "Chassis number:",
    },
}


def detect_language(text: str) -> str:
    if re.search(r"[؀-ۿ]", text or ""):
        return "ar"
    if re.search(r"[֐-׿]", text or ""):
        return "he"
    return "en"


def _display_value(field: str, value: str) -> str:
    if field in {"insurance_start", "insurance_end"} and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        y, m, d = value.split("-")
        return f"{d}/{m}/{y}"
    if field == "premium":
        num = value.replace("₪", "").strip()
        return f"{num} ₪"
    return value


def format_field_answer(field: str, value: str, lang: str) -> str:
    # No inline source marker — the frontend renders the single source separately.
    label = _LABELS.get(lang, _LABELS["en"]).get(field, field)
    return f"{label} **{_display_value(field, value)}**"


# --------------------------------------------------------------------------- #
# DB-backed resolution for the chat endpoint (reads STORED extraction_json)
# --------------------------------------------------------------------------- #

import uuid  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.vehicles import VehicleDocument  # noqa: E402

# Answer directly at/above this confidence; between MIN and this -> hedge; below
# MIN -> defer to RAG.
HIGH_CONFIDENCE = 0.85
MIN_CONFIDENCE = 0.60


@dataclass
class StructuredAnswer:
    content: str
    field: str
    value: str
    confidence: float
    document_id: str | None
    document_title: str | None
    page: int
    llm_called: bool = False
    debug: dict = dc_field(default_factory=dict)


def _target_document(db: Session, user, conversation) -> VehicleDocument | None:
    """Which vehicle document is the user talking about (Part 7 context)."""
    active_id = getattr(conversation, "active_document_id", None)
    if active_id:
        vd = db.get(VehicleDocument, active_id)
        if vd and vd.extraction_json:
            return vd
    # Most recent vehicle document uploaded by this user, else most recent overall.
    for stmt in (
        select(VehicleDocument).where(VehicleDocument.uploaded_by == user.id)
        .order_by(VehicleDocument.created_at.desc()),
        select(VehicleDocument).order_by(VehicleDocument.created_at.desc()),
    ):
        for vd in db.scalars(stmt.limit(10)):
            if vd.extraction_json:
                return vd
    return None


def resolve_structured_answer(db: Session, user, conversation, question: str) -> StructuredAnswer | None:
    """Deterministic structured answer for the chat endpoint, or None to defer to RAG."""
    intent = detect_structured_intent(question)
    debug = {"question": question, "detected_intent": intent.field,
             "intent_confidence": intent.confidence, "lookup_mode": "rag", "llm_called": True}
    if not intent.field or intent.confidence < 0.8:
        return None

    vd = _target_document(db, user, conversation)
    if not vd:
        return None

    fv = field_from_extraction_json(vd.extraction_json, intent.field)
    if not fv or fv.confidence < MIN_CONFIDENCE:
        return None

    lang = detect_language(question)
    body = format_field_answer(intent.field, fv.value, lang)
    if fv.confidence < HIGH_CONFIDENCE:
        # Hedge for medium confidence (Part 15).
        prefix = {"he": "מצאתי במסמך: ", "ar": "وجدت في المستند: ", "en": "Found in the document: "}[lang]
        body = prefix + body

    # Remember the active document for terse follow-ups ("תחילה", "תום").
    conversation.active_document_id = vd.id

    debug.update({"lookup_mode": "structured", "llm_called": False,
                  "field_value": fv.value, "field_confidence": fv.confidence,
                  "active_document": vd.original_filename})
    return StructuredAnswer(
        content=body, field=intent.field, value=fv.value, confidence=fv.confidence,
        document_id=str(vd.id), document_title=vd.original_filename, page=fv.page,
        llm_called=False, debug=debug,
    )
