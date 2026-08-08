"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import LoginRequest, TokenResponse, UserOut
from app.audit import service as audit
from app.auth.deps import client_ip, get_current_user
from app.core.errors import MuniAIError
from app.db.session import get_db
from app.models.iam import User
from app.security.passwords import verify_password
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    ip = client_ip(request)
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        audit.record(
            db, action="login", result="failure", ip_address=ip,
            detail=f"failed login for {payload.email}",
        )
        raise MuniAIError("Invalid email or password.", status_code=401, code="bad_credentials")
    if not user.is_active:
        raise MuniAIError("Account is disabled.", status_code=403, code="inactive_user")

    token = create_access_token(str(user.id))
    audit.record(db, action="login", user_id=user.id, result="success", ip_address=ip)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    # JWT is stateless; logout is client-side token disposal. We still audit it.
    audit.record(db, action="logout", user_id=user.id, ip_address=client_ip(request))
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    out = UserOut.model_validate(user)
    out.permissions = sorted(user.permission_keys)
    return out
