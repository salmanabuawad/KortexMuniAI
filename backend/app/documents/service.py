"""Document ingestion + indexing service.

For the MVP this runs synchronously within the request (small documents). The
pipeline is structured so it can be moved to a Celery worker unchanged: each
stage is a discrete function and progress is reflected on the Document row.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.registry import get_provider
from app.core.config import settings
from app.core.logging import get_logger
from app.documents.chunking import PageText, chunk_page_text
from app.documents.extraction import extract_text
from app.documents.ocr import ocr_document
from app.documents.storage import compute_hash, store_blob
from app.models.documents import Document, DocumentChunk, Embedding
from app.models.enums import Classification, ProcessingStatus

logger = get_logger("muniai.documents.service")


async def ingest_document(
    db: Session,
    *,
    filename: str,
    data: bytes,
    owner_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    classification: Classification = Classification.INTERNAL,
    title: str | None = None,
) -> Document:
    """Store, extract, chunk, embed and index a document. Returns the Document."""
    content_hash = compute_hash(data)
    existing = db.scalar(
        select(Document).where(Document.content_hash == content_hash, Document.is_deleted.is_(False))
    )
    if existing:
        logger.info("Duplicate upload (hash match); reusing document %s", existing.id)
        return existing

    _, storage_path = store_blob(data)
    file_type = Path(filename).suffix.lstrip(".").lower()

    doc = Document(
        title=title or filename,
        original_filename=filename,
        file_type=file_type,
        storage_path=storage_path,
        content_hash=content_hash,
        owner_id=owner_id,
        department_id=department_id,
        classification=classification,
        processing_status=ProcessingStatus.RUNNING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        result = extract_text(storage_path, file_type)

        if result.needs_ocr:
            # Scanned/photographed document — run local OCR (Tesseract he/ar/en).
            ocr_pages = ocr_document(storage_path, file_type)
            if ocr_pages:
                pages = [PageText(page=p.page, text=p.text) for p in ocr_pages]
                doc.ocr_status = "ocr_done"
                doc.language = "ocr"
            else:
                pages = [PageText(page=p.page, text=p.text) for p in result.pages]
                doc.ocr_status = "ocr_unavailable"
        else:
            pages = [PageText(page=p.page, text=p.text) for p in result.pages]
            doc.ocr_status = "not_required"

        doc.page_count = len(pages)

        if not any(p.text.strip() for p in pages):
            doc.processing_status = ProcessingStatus.READY
            doc.indexing_status = "skipped_no_text"
            db.commit()
            logger.info("Document %s stored; no extractable text.", doc.id)
            return doc

        chunks = chunk_page_text(pages)
        _persist_chunks(db, doc, chunks)
        await _embed_chunks(db, doc)

        doc.processing_status = ProcessingStatus.READY
        doc.indexing_status = "indexed"
        db.commit()
        logger.info("Indexed document %s (%d chunks).", doc.id, len(chunks))
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = ProcessingStatus.FAILED
        doc.indexing_status = f"error: {exc}"[:20]
        db.commit()
        logger.exception("Indexing failed for %s: %s", doc.id, exc)
    return doc


def _persist_chunks(db: Session, doc: Document, chunks) -> None:
    for ch in chunks:
        db.add(DocumentChunk(
            document_id=doc.id, position=ch.position, page=ch.page,
            content=ch.content, token_count=len(ch.content.split()),
        ))
    db.commit()


async def _embed_chunks(db: Session, doc: Document) -> None:
    chunks = list(db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.position)
    ))
    if not chunks:
        return
    provider = get_provider()
    vectors = await provider.embeddings([c.content for c in chunks])
    model = settings.ollama_embed_model
    for chunk, vector in zip(chunks, vectors):
        if vector:
            db.add(Embedding(chunk_id=chunk.id, model=model, vector=vector))
    db.commit()
