"""Permission-aware hybrid retrieval (spec §13).

Pipeline: permission filter -> (semantic via pgvector) + (keyword via ILIKE) ->
merge/dedupe -> top-K chunks with document + page for citations.

Embeddings come from the local provider. If embeddings are unavailable (e.g. no
Ollama), we degrade gracefully to keyword-only retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.registry import get_provider
from app.core.logging import get_logger
from app.models.documents import Document, DocumentChunk, Embedding
from app.models.iam import User
from app.rag.access import accessible_document_ids

logger = get_logger("muniai.rag")


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    page: int | None
    content: str
    score: float


async def _embed_query(text: str) -> list[float] | None:
    try:
        vectors = await get_provider().embeddings([text])
        return vectors[0] if vectors else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query embedding failed (%s); falling back to keyword search.", exc)
        return None


def _keyword_search(db: Session, user: User, query: str, limit: int) -> list[RetrievedChunk]:
    allowed = accessible_document_ids(user).subquery()
    like = f"%{query.strip()}%"
    stmt = (
        select(DocumentChunk, Document.title)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.document_id.in_(select(allowed.c.id)))
        .where(DocumentChunk.content.ilike(like))
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(str(c.id), str(c.document_id), title, c.page, c.content, 0.5)
        for c, title in rows
    ]


def _semantic_search(
    db: Session, user: User, vector: list[float], limit: int
) -> list[RetrievedChunk]:
    allowed = accessible_document_ids(user).subquery()
    distance = Embedding.vector.cosine_distance(vector)
    stmt = (
        select(DocumentChunk, Document.title, distance.label("distance"))
        .join(Embedding, Embedding.chunk_id == DocumentChunk.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.document_id.in_(select(allowed.c.id)))
        .order_by(distance)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(str(c.id), str(c.document_id), title, c.page, c.content,
                       max(0.0, 1.0 - float(dist)))
        for c, title, dist in rows
    ]


async def retrieve(
    db: Session, user: User, query: str, *, top_k: int = 6
) -> list[RetrievedChunk]:
    """Return the top-K permission-filtered chunks for a query."""
    # Cheap short-circuit: if the user can see no documents, skip entirely.
    has_any = db.scalar(
        select(func.count()).select_from(accessible_document_ids(user).subquery())
    )
    if not has_any:
        return []

    results: dict[str, RetrievedChunk] = {}

    vector = await _embed_query(query)
    if vector is not None:
        for rc in _semantic_search(db, user, vector, top_k):
            results[rc.chunk_id] = rc

    for rc in _keyword_search(db, user, query, top_k):
        # Keyword hits reinforce/attach; keep the higher score if already present.
        if rc.chunk_id in results:
            existing = results[rc.chunk_id]
            if rc.score > existing.score:
                results[rc.chunk_id] = rc
        else:
            results[rc.chunk_id] = rc

    ranked = sorted(results.values(), key=lambda r: r.score, reverse=True)
    return ranked[:top_k]
