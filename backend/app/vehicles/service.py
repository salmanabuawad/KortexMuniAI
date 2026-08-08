"""Vehicle-document processing service.

Ties together storage, deterministic extraction (app/vehicles/ocr.py), vehicle
matching, insurance-policy creation, and the deterministic conflict engine
(app/vehicles/insurance_rules.py). AI is never the source of truth for
overlap/duplicate/expiry — those are computed here in plain Python.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.documents.extraction import extract_text
from app.documents.storage import compute_hash, store_blob
from app.models.enums import InsuranceType, PolicyStatus, Severity
from app.models.vehicles import (
    InsuranceConflict,
    InsurancePolicy,
    Vehicle,
    VehicleAlert,
    VehicleDocument,
    VehicleDocumentExtraction,
)
from app.vehicles import ocr
from app.vehicles.insurance_rules import PolicyLike, find_conflicts
from app.vehicles.normalization import normalize_registration

logger = get_logger("muniai.vehicles.service")


def _ocr_image(path: str) -> str:
    """Best-effort local OCR for images. Uses pytesseract if installed (heb+eng)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning("pytesseract/Pillow not installed; image OCR unavailable.")
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path), lang="heb+eng")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Image OCR failed: %s", exc)
        return ""


def _extract_text(storage_path: str, file_type: str) -> str:
    result = extract_text(storage_path, file_type)
    if result.pages:
        return "\n".join(p.text for p in result.pages)
    if result.needs_ocr:
        return _ocr_image(storage_path)
    return ""


def _match_or_create_vehicle(db: Session, plate: str | None) -> Vehicle | None:
    norm = normalize_registration(plate)
    if not norm:
        return None  # never attach a document without an identifiable vehicle
    vehicle = db.scalar(select(Vehicle).where(Vehicle.normalized_number == norm))
    if not vehicle:
        vehicle = Vehicle(registration_number=plate or norm, normalized_number=norm)
        db.add(vehicle)
        db.flush()
    return vehicle


def process_vehicle_document(
    db: Session, *, filename: str, data: bytes, uploaded_by: uuid.UUID
) -> VehicleDocument:
    content_hash = compute_hash(data)
    existing = db.scalar(select(VehicleDocument).where(VehicleDocument.content_hash == content_hash))
    if existing:
        logger.info("Duplicate vehicle document (hash); reusing %s", existing.id)
        return existing

    _, storage_path = store_blob(data)
    file_type = Path(filename).suffix.lstrip(".").lower()
    text = _extract_text(storage_path, file_type)
    ex = ocr.extract(text, filename)

    plate_field = ex.fields.get("registration_number")
    vehicle = _match_or_create_vehicle(db, plate_field.value if plate_field else None)

    doc = VehicleDocument(
        vehicle_id=vehicle.id if vehicle else None,
        document_type=ex.document_type,
        original_filename=filename,
        storage_path=storage_path,
        content_hash=content_hash,
        page_count=None,
        ocr_text=text or None,
        classification_confidence=ex.fields["document_type"].confidence,
        review_status="needs_review",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.flush()

    for name, f in ex.fields.items():
        db.add(VehicleDocumentExtraction(
            document_id=doc.id, field_name=name, ocr_original_value=f.value,
            confidence=f.confidence, source_page=f.source_page, verified=False,
        ))

    # Create an insurance policy for insurance documents (unverified; user confirms).
    if ex.insurance_type and vehicle:
        _create_policy(db, vehicle, doc, ex)
        run_conflict_scan(db, vehicle.id)

    db.commit()
    # NB: no db.refresh() — the session keeps attributes after commit
    # (expire_on_commit=False), so doc.document_type stays an enum instance.
    logger.info("Processed vehicle document %s (type=%s, vehicle=%s)",
                doc.id, ex.document_type.value, vehicle.id if vehicle else None)
    return doc


def _to_date(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def _create_policy(db: Session, vehicle: Vehicle, doc: VehicleDocument, ex) -> InsurancePolicy:
    policy = InsurancePolicy(
        vehicle_id=vehicle.id,
        document_id=doc.id,
        policy_number=(ex.fields.get("policy_number").value if ex.fields.get("policy_number") else None),
        insurance_type=ex.insurance_type or InsuranceType.OTHER,
        insurer=(ex.fields.get("insurer").value if ex.fields.get("insurer") else None),
        start_date=_to_date(ex.fields["start_date"].value) if "start_date" in ex.fields else None,
        end_date=_to_date(ex.fields["end_date"].value) if "end_date" in ex.fields else None,
        status=PolicyStatus.NEEDS_REVIEW,
        confidence=0.5,
        verified=False,
    )
    db.add(policy)
    db.flush()
    return policy


def run_conflict_scan(db: Session, vehicle_id: uuid.UUID) -> list[InsuranceConflict]:
    """Recompute insurance conflicts for a vehicle deterministically and persist
    them (replacing prior auto-detected, unreviewed conflicts)."""
    policies = list(db.scalars(select(InsurancePolicy).where(InsurancePolicy.vehicle_id == vehicle_id)))
    likes = [
        PolicyLike(
            # Coerce to enum: columns are stored as strings and reload as str.
            id=str(p.id), vehicle_number=str(vehicle_id),
            insurance_type=InsuranceType(str(p.insurance_type)),
            policy_number=p.policy_number, insurer=p.insurer,
            start_date=p.start_date, end_date=p.end_date,
            file_hash=None,
        )
        for p in policies
    ]
    conflicts = find_conflicts(likes)

    # Clear previously auto-detected, still-unreviewed conflicts for this vehicle.
    for old in db.scalars(
        select(InsuranceConflict).where(
            InsuranceConflict.vehicle_id == vehicle_id,
            InsuranceConflict.status == "needs_review",
        )
    ):
        db.delete(old)
    db.flush()

    saved: list[InsuranceConflict] = []
    for c in conflicts:
        row = InsuranceConflict(
            vehicle_id=vehicle_id,
            policy_a_id=uuid.UUID(c.policy_a_id),
            policy_b_id=uuid.UUID(c.policy_b_id),
            conflict_type=c.conflict_type,
            overlap_start=c.overlap_start,
            overlap_end=c.overlap_end,
            overlap_days=c.overlap_days,
            severity=c.severity,
            status="needs_review",
            notes=c.message,
        )
        db.add(row)
        saved.append(row)
        if c.severity in (Severity.HIGH, Severity.CRITICAL):
            db.add(VehicleAlert(
                vehicle_id=vehicle_id, kind="conflict", severity=c.severity,
                message=c.message,
            ))
    db.flush()
    return saved
