"""Document access control for retrieval (spec §15, §62).

A single source of truth for "which documents can this user see", expressed both
as a pure predicate (unit-testable) and as a SQL filter (applied BEFORE vector
search, so restricted content never reaches the LLM).

Rule — a user may access a document if ANY of:
  * the user is a superuser;
  * the document is PUBLIC;
  * the user owns the document;
  * the document belongs to the user's department;
  * an explicit DocumentPermission grants the user, one of their roles,
    or their department.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentPermission
from app.models.enums import Classification
from app.models.iam import User


def can_access(user: User, doc: Document, grant_keys: set[str] | None = None) -> bool:
    """Pure predicate mirroring the SQL filter. ``grant_keys`` is the set of
    explicit grant identifiers for the doc, formatted ``user:<id>`` / ``role:<id>``
    / ``dept:<id>`` (used by tests; production uses the SQL path)."""
    if user.is_superuser:
        return True
    if doc.classification == Classification.PUBLIC:
        return True
    if doc.owner_id and doc.owner_id == user.id:
        return True
    if doc.department_id and user.department_id and doc.department_id == user.department_id:
        return True
    if grant_keys:
        wanted = {f"user:{user.id}", f"dept:{user.department_id}"}
        wanted |= {f"role:{r.id}" for r in user.roles}
        if wanted & grant_keys:
            return True
    return False


def accessible_document_ids(user: User) -> Select:
    """A SELECT of document IDs the user may access. Used as a subquery filter."""
    role_ids = [r.id for r in user.roles]

    grant_subq = select(DocumentPermission.document_id).where(
        or_(
            DocumentPermission.user_id == user.id,
            DocumentPermission.department_id == user.department_id
            if user.department_id
            else False,
            DocumentPermission.role_id.in_(role_ids) if role_ids else False,
        )
    )

    conditions = [
        Document.classification == Classification.PUBLIC,
        Document.owner_id == user.id,
        Document.id.in_(grant_subq),
    ]
    if user.department_id:
        conditions.append(Document.department_id == user.department_id)

    stmt = select(Document.id).where(Document.is_deleted.is_(False))
    if not user.is_superuser:
        stmt = stmt.where(or_(*conditions))
    return stmt


def user_can_access_document(db: Session, user: User, document_id: uuid.UUID) -> bool:
    """Authoritative single-document check for downloads / viewer access."""
    stmt = accessible_document_ids(user).where(Document.id == document_id)
    return db.scalar(stmt) is not None
