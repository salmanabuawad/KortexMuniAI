"""Document management API: upload/index, list, metadata, download, viewer."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import DocumentOut
from app.audit import service as audit
from app.auth.deps import client_ip, get_current_user, require_permission
from app.core.config import settings
from app.core.errors import MuniAIError
from app.db.session import get_db
from app.documents.service import ingest_document
from app.models.documents import Document
from app.models.enums import Classification
from app.models.iam import User
from app.rag.access import accessible_document_ids, user_can_access_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Document]:
    allowed = accessible_document_ids(user).subquery()
    stmt = (
        select(Document)
        .where(Document.id.in_(select(allowed.c.id)))
        .order_by(Document.created_at.desc())
        .limit(200)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=DocumentOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    classification: str = Form("INTERNAL"),
    title: str | None = Form(None),
    user: User = Depends(require_permission("UPLOAD")),
    db: Session = Depends(get_db),
) -> Document:
    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise MuniAIError(
            f"File exceeds the {settings.max_upload_mb} MB limit.",
            status_code=413, code="file_too_large",
        )
    try:
        cls = Classification(classification.upper())
    except ValueError:
        cls = Classification.INTERNAL

    doc = await ingest_document(
        db,
        filename=file.filename or "upload",
        data=data,
        owner_id=user.id,
        department_id=user.department_id,
        classification=cls,
        title=title,
    )
    audit.record(
        db, action="document_uploaded", user_id=user.id, resource_type="document",
        resource_id=doc.id, ip_address=client_ip(request),
        detail=f"{doc.original_filename} ({doc.processing_status.value})",
    )
    return doc


def _get_accessible(db: Session, user: User, document_id: uuid.UUID) -> Document:
    doc = db.get(Document, document_id)
    if not doc or doc.is_deleted or not user_can_access_document(db, user, document_id):
        raise MuniAIError("Document not found.", status_code=404, code="not_found")
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    return _get_accessible(db, user, document_id)


@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_permission("DOWNLOAD")),
    db: Session = Depends(get_db),
) -> FileResponse:
    doc = _get_accessible(db, user, document_id)
    if not doc.storage_path or not Path(doc.storage_path).exists():
        raise MuniAIError("File is not available.", status_code=404, code="not_found")
    audit.record(
        db, action="document_downloaded", user_id=user.id, resource_type="document",
        resource_id=doc.id, ip_address=client_ip(request),
    )
    return FileResponse(
        doc.storage_path,
        filename=doc.original_filename,
        media_type="application/octet-stream",
    )
