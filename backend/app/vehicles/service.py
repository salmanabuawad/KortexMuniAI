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
from app.documents.storage import compute_hash, store_blob
from app.models.enums import InsuranceType, PolicyStatus, Severity, VehicleDocumentType
from app.models.vehicles import (
    InsuranceConflict,
    InsurancePolicy,
    Vehicle,
    VehicleAlert,
    VehicleDocument,
    VehicleDocumentExtraction,
)
from app.vehicles.extraction import ExtractionResult, extract_document
from app.vehicles.insurance_rules import PolicyLike, find_conflicts
from app.vehicles.normalization import normalize_registration

logger = get_logger("muniai.vehicles.service")

# Only auto-attach a document to a vehicle when the number is reasonably certain.
VEHICLE_MATCH_MIN_CONFIDENCE = 0.6


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

    # Field-aware, layout-aware extraction (native PDF -> region OCR -> full OCR).
    result = extract_document(storage_path, file_type)
    doc_type = VehicleDocumentType(result.document_type)

    # Only match a vehicle when the registration number is confident enough —
    # never silently attach a document to an uncertain vehicle (spec §4/§16).
    veh_field = result.fields.get("vehicle_number")
    plate = veh_field.value if veh_field and veh_field.confidence >= VEHICLE_MATCH_MIN_CONFIDENCE else None
    vehicle = _match_or_create_vehicle(db, plate)

    doc = VehicleDocument(
        vehicle_id=vehicle.id if vehicle else None,
        document_type=doc_type,
        original_filename=filename,
        storage_path=storage_path,
        content_hash=content_hash,
        page_count=None,
        ocr_text=(result.raw_text or None),
        extraction_json=result.as_dict(),
        ocr_engine=result.ocr_engine,
        processing_version=result.processing_version,
        classification_confidence=result.document_type_confidence,
        review_status="needs_review",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.flush()

    for name, f in result.fields.items():
        db.add(VehicleDocumentExtraction(
            document_id=doc.id, field_name=name, ocr_original_value=f.value,
            confidence=f.confidence, source_page=f.page, verified=False,
        ))

    # Create an insurance policy for insurance documents (unverified; user confirms).
    insurance_type = _insurance_type_from(result)
    if insurance_type and vehicle:
        _create_policy(db, vehicle, doc, result, insurance_type)
        run_conflict_scan(db, vehicle.id)

    db.commit()
    logger.info("Processed vehicle document %s (type=%s, vehicle_number=%s, engine=%s)",
                doc.id, doc_type.value, plate, result.ocr_engine)
    return doc


def _insurance_type_from(result: ExtractionResult) -> InsuranceType | None:
    val = result.field_value("insurance_type")
    if val:
        try:
            return InsuranceType(val)
        except ValueError:
            return None
    return None


def _to_date(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def _create_policy(db: Session, vehicle: Vehicle, doc: VehicleDocument,
                   result: ExtractionResult, insurance_type: InsuranceType) -> InsurancePolicy:
    policy = InsurancePolicy(
        vehicle_id=vehicle.id,
        document_id=doc.id,
        policy_number=result.field_value("policy_number"),
        insurance_type=insurance_type,
        insurer=result.field_value("insurer"),
        start_date=_to_date(result.field_value("insurance_start")),
        end_date=_to_date(result.field_value("insurance_end")),
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
