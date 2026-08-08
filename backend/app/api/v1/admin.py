"""Admin center API (spec §31): users, audit, integrations, models, stats.

All endpoints require the ADMIN permission.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.registry import get_provider
from app.api.v1.schemas import (
    AdminStats,
    AdminUserCreate,
    AuditOut,
    IntegrationOut,
    UserOut,
)
from app.audit import service as audit
from app.auth.deps import client_ip, require_permission
from app.core.errors import MuniAIError
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.chat import Conversation
from app.models.documents import Document
from app.models.iam import Role, User
from app.models.system import Integration
from app.models.vehicles import InsuranceConflict, Vehicle
from app.security.passwords import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(require_permission("ADMIN")), db: Session = Depends(get_db)) -> AdminStats:
    def count(model) -> int:
        return db.scalar(select(func.count()).select_from(model)) or 0

    return AdminStats(
        users=count(User),
        documents=count(Document),
        conversations=count(Conversation),
        vehicles=count(Vehicle),
        conflicts=count(InsuranceConflict),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_permission("ADMIN")), db: Session = Depends(get_db)) -> list[User]:
    users = list(db.scalars(select(User).order_by(User.created_at.desc()).limit(500)))
    out = []
    for u in users:
        o = UserOut.model_validate(u)
        o.permissions = sorted(u.permission_keys)
        out.append(o)
    return out


@router.post("/users", response_model=UserOut)
def create_user(
    payload: AdminUserCreate,
    request: Request,
    admin: User = Depends(require_permission("ADMIN")),
    db: Session = Depends(get_db),
) -> UserOut:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise MuniAIError("A user with this email already exists.", status_code=409, code="conflict")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_superuser=payload.is_superuser,
    )
    if payload.role_names:
        user.roles = list(db.scalars(select(Role).where(Role.name.in_(payload.role_names))))
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, action="user_created", user_id=admin.id, resource_type="user",
                 resource_id=user.id, ip_address=client_ip(request))
    out = UserOut.model_validate(user)
    out.permissions = sorted(user.permission_keys)
    return out


@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    _: User = Depends(require_permission("ADMIN")),
    db: Session = Depends(get_db),
    limit: int = 100,
) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(min(limit, 500))))


@router.get("/integrations", response_model=list[IntegrationOut])
def list_integrations(
    _: User = Depends(require_permission("ADMIN")), db: Session = Depends(get_db)
) -> list[Integration]:
    return list(db.scalars(select(Integration).order_by(Integration.name)))


@router.get("/models")
async def list_models(_: User = Depends(require_permission("ADMIN"))) -> dict:
    provider = get_provider()
    health = await provider.health()
    return {
        "provider": provider.name,
        "healthy": health.healthy,
        "detail": health.detail,
        "models": health.models,
    }
