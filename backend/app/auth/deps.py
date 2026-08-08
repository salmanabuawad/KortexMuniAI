"""Authentication / authorization dependencies.

RBAC is enforced here in the backend — the LLM is never the security boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import MuniAIError
from app.db.session import get_db
from app.models.iam import User
from app.security.tokens import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise MuniAIError("Not authenticated.", status_code=401, code="not_authenticated")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise MuniAIError("Invalid or expired token.", status_code=401, code="invalid_token")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise MuniAIError("Invalid token subject.", status_code=401, code="invalid_token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise MuniAIError("User not found or inactive.", status_code=401, code="inactive_user")
    return user


def require_permission(action: str, resource: str = "*") -> Callable[..., User]:
    """Dependency factory enforcing that the user holds ``ACTION:resource``.

    A superuser (``*``) or an exact ``ACTION:*`` grant also satisfies the check.
    """

    wanted = f"{action}:{resource}"
    wanted_wildcard = f"{action}:*"

    def _checker(user: User = Depends(get_current_user)) -> User:
        keys = user.permission_keys
        if "*" in keys or wanted in keys or wanted_wildcard in keys:
            return user
        raise MuniAIError(
            f"Missing permission: {wanted}", status_code=403, code="forbidden"
        )

    return _checker


def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
