"""Deterministic answers for structured vehicle-document questions.

Small local chat models can hallucinate when an RTL insurance table is flattened
into RAG chunks.  For exact field questions (plate, policy number, dates, etc.)
we therefore re-use the deterministic vehicle-document extractor on the source
PDF instead of asking the LLM to infer a value from token order.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.documents import Document
from app.rag.retrieval import RetrievedChunk
from app.vehicles.extraction import extract_document

logger = get_logger("muniai.rag.structured_qa")


@dataclass(frozen=True)
class StructuredAnswer:
    content: str
    field_name: str
    value: str
    source_chunk: RetrievedChunk


# Order matters: use specific intents before generic vehicle wording.
_FIELD_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("vehicle_number", (
        r"מספר\s*(?:ה)?רכב", r"מס[׳'\"]?\s*רישוי", r"מספר\s*רישוי",
        r"plate\s*(?:number|no\.?|#)?", r"registration\s*(?:number|no\.?)",
        r"رقم\s*(?:السيارة|المركبة|الترخيص)",
    )),
    ("policy_number", (
        r"מספר\s*(?:ה)?פוליסה", r"מס[׳'\"]?\s*פוליסה",
        r"policy\s*(?:number|no\.?)", r"رقم\s*(?:البوليصة|الوثيقة)",
    )),
    ("insurance_start", (
        r"תחילת\s*(?:ה)?ביטוח", r"מועד\s*תחילת\s*(?:ה)?ביטוח",
        r"insurance\s*start", r"start\s*date", r"بداية\s*التأمين",
    )),
    ("insurance_end", (
        r"(?:סיום|תום|פקיעת)\s*(?:ה)?ביטוח", r"מועד\s*פקיעת\s*(?:ה)?ביטוח",
        r"insurance\s*(?:end|expiry|expiration)", r"end\s*date",
        r"نهاية\s*التأمين", r"انتهاء\s*التأمين",
    )),
    ("policy_holder", (
        r"בעל\s*(?:ה)?פוליסה", r"שם\s*(?:ה)?מבוטח",
        r"policy\s*holder", r"insured\s*(?:name|party)", r"صاحب\s*(?:البوليصة|الوثيقة)",
    )),
    ("id_number", (
        r"מספר\s*זהות", r"ת[.\"׳']?ז", r"id\s*(?:number|no\.?)", r"رقم\s*الهوية",
    )),
    ("insurer", (
        r"חברת\s*(?:ה)?ביטוח", r"מי\s*(?:ה)?מבטח", r"insurer", r"insurance\s*company",
        r"شركة\s*التأمين",
    )),
    ("premium", (
        r"(?:דמי\s*ביטוח|פרמיה|עלות\s*(?:ה)?ביטוח)", r"premium", r"قسط\s*التأمين",
    )),
    ("manufacturer", (
        r"(?:יצרן|תוצר)\s*(?:ה)?רכב", r"manufacturer", r"صانع\s*(?:السيارة|المركبة)",
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

_LABELS_HE = {
    "vehicle_number": "מספר הרכב",
    "policy_number": "מספר הפוליסה",
    "insurance_start": "תחילת הביטוח",
    "insurance_end": "תום הביטוח",
    "policy_holder": "בעל הפוליסה",
    "id_number": "מספר הזהות",
    "insurer": "חברת הביטוח",
    "premium": "דמי הביטוח",
    "manufacturer": "יצרן הרכב",
    "production_year": "שנת הייצור",
    "engine_capacity": "נפח המנוע",
    "chassis": "מספר השלדה",
}

_LABELS_AR = {
    "vehicle_number": "رقم المركبة",
    "policy_number": "رقم الوثيقة",
    "insurance_start": "بداية التأمين",
    "insurance_end": "نهاية التأمين",
    "policy_holder": "صاحب الوثيقة",
    "id_number": "رقم الهوية",
    "insurer": "شركة التأمين",
    "premium": "قسط التأمين",
    "manufacturer": "صانع المركبة",
    "production_year": "سنة الصنع",
    "engine_capacity": "سعة المحرك",
    "chassis": "رقم الشاسيه",
}

_LABELS_EN = {
    "vehicle_number": "Vehicle number",
    "policy_number": "Policy number",
    "insurance_start": "Insurance start",
    "insurance_end": "Insurance end",
    "policy_holder": "Policy holder",
    "id_number": "ID number",
    "insurer": "Insurer",
    "premium": "Insurance premium",
    "manufacturer": "Manufacturer",
    "production_year": "Production year",
    "engine_capacity": "Engine capacity",
    "chassis": "Chassis number",
}


def detect_field_intent(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    for field, patterns in _FIELD_PATTERNS:
        if any(re.search(p, q, flags=re.IGNORECASE) for p in patterns):
            return field
    return None


def _language(query: str) -> str:
    if re.search(r"[\u0600-\u06ff]", query or ""):
        return "ar"
    if re.search(r"[\u0590-\u05ff]", query or ""):
        return "he"
    return "en"


def _format_value(field: str, value: str, lang: str) -> str:
    if field in {"insurance_start", "insurance_end"} and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        y, m, d = value.split("-")
        value = f"{d}/{m}/{y}"
    if field == "premium" and value:
        value = f"{value} ₪" if "₪" not in value else value
    labels = _LABELS_HE if lang == "he" else _LABELS_AR if lang == "ar" else _LABELS_EN
    label = labels.get(field, field)
    if lang == "he":
        return f"{label} הוא **{value}**. [1]"
    if lang == "ar":
        return f"{label} هو **{value}**. [1]"
    return f"{label}: **{value}**. [1]"


def resolve_structured_question(
    db: Session,
    query: str,
    chunks: list[RetrievedChunk],
    *,
    min_confidence: float = 0.70,
) -> StructuredAnswer | None:
    """Resolve an exact vehicle-document field question from the source file.

    Only runs for explicit field intents. It never guesses from flattened RAG
    text. Documents are tried in retrieval rank order; the first confident
    extracted value wins.
    """
    field = detect_field_intent(query)
    if not field or not chunks:
        return None

    seen: set[str] = set()
    for chunk in chunks:
        if chunk.document_id in seen:
            continue
        seen.add(chunk.document_id)

        try:
            doc = db.get(Document, uuid.UUID(chunk.document_id))
        except Exception:  # UUID coercion / stale row; let normal RAG handle it
            doc = None
        if not doc or not doc.storage_path:
            continue

        path = Path(doc.storage_path)
        if not path.exists():
            logger.warning("Structured QA source file missing: %s", path)
            continue

        try:
            result = extract_document(str(path), doc.file_type or path.suffix.lstrip("."))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structured extraction failed for %s: %s", path, exc)
            continue

        extracted = result.fields.get(field)
        if not extracted or not extracted.value or extracted.confidence < min_confidence:
            continue

        value = str(extracted.value).strip()
        if not value:
            continue

        return StructuredAnswer(
            content=_format_value(field, value, _language(query)),
            field_name=field,
            value=value,
            source_chunk=chunk,
        )

    return None
