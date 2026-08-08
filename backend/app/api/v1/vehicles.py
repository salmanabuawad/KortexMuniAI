"""Vehicle-document intelligence API: upload, review, conflicts (spec ADDITION)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    ConflictOut,
    ExtractionCorrection,
    ExtractionOut,
    InsurancePolicyOut,
    VehicleDocumentOut,
    VehicleOut,
)
from app.audit import service as audit
from app.auth.deps import client_ip, get_current_user, require_permission
from app.core.errors import MuniAIError
from app.db.session import get_db
from app.models.iam import User
from app.models.vehicles import (
    InsuranceConflict,
    InsurancePolicy,
    Vehicle,
    VehicleDocument,
    VehicleDocumentExtraction,
)
from app.vehicles.service import process_vehicle_document, run_conflict_scan

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.normalized_number).limit(500)))


@router.post("/documents", response_model=VehicleDocumentOut)
async def upload_vehicle_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_permission("UPLOAD")),
    db: Session = Depends(get_db),
) -> VehicleDocument:
    data = await file.read()
    doc = process_vehicle_document(
        db, filename=file.filename or "upload", data=data, uploaded_by=user.id
    )
    audit.record(
        db, action="vehicle_document_uploaded", user_id=user.id,
        resource_type="vehicle_document", resource_id=doc.id, ip_address=client_ip(request),
        detail=getattr(doc.document_type, "value", str(doc.document_type)),
    )
    return doc


@router.get("/documents/{document_id}/extractions", response_model=list[ExtractionOut])
def list_extractions(
    document_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VehicleDocumentExtraction]:
    return list(db.scalars(
        select(VehicleDocumentExtraction).where(VehicleDocumentExtraction.document_id == document_id)
    ))


@router.post("/documents/{document_id}/verify", response_model=list[ExtractionOut])
def verify_extractions(
    document_id: uuid.UUID,
    corrections: list[ExtractionCorrection],
    request: Request,
    user: User = Depends(require_permission("EDIT")),
    db: Session = Depends(get_db),
) -> list[VehicleDocumentExtraction]:
    doc = db.get(VehicleDocument, document_id)
    if not doc:
        raise MuniAIError("Vehicle document not found.", status_code=404, code="not_found")
    by_name = {c.field_name: c.corrected_value for c in corrections}
    rows = list(db.scalars(
        select(VehicleDocumentExtraction).where(VehicleDocumentExtraction.document_id == document_id)
    ))
    for row in rows:
        if row.field_name in by_name:
            row.corrected_value = by_name[row.field_name]
        row.verified = True
        row.verified_by = user.id
    doc.review_status = "verified"
    db.commit()
    # Re-run deterministic conflict scan with corrected data.
    if doc.vehicle_id:
        run_conflict_scan(db, doc.vehicle_id)
        db.commit()
    audit.record(
        db, action="vehicle_extraction_verified", user_id=user.id,
        resource_type="vehicle_document", resource_id=doc.id, ip_address=client_ip(request),
    )
    return rows


@router.get("/conflicts", response_model=list[ConflictOut])
def list_conflicts(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[InsuranceConflict]:
    return list(db.scalars(
        select(InsuranceConflict).order_by(InsuranceConflict.created_at.desc()).limit(500)
    ))


@router.get("/{vehicle_id}/policies", response_model=list[InsurancePolicyOut])
def vehicle_policies(
    vehicle_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InsurancePolicy]:
    return list(db.scalars(select(InsurancePolicy).where(InsurancePolicy.vehicle_id == vehicle_id)))
