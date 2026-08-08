"""Meta routes: health, branding, system status."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.ai.registry import get_provider
from app.api.v1.schemas import BrandingOut, ComponentHealth, HealthResponse
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)) -> HealthResponse:
    components: list[ComponentHealth] = []

    # Database
    try:
        db.execute(text("SELECT 1"))
        components.append(ComponentHealth(name="database", healthy=True))
    except Exception as exc:  # noqa: BLE001
        components.append(ComponentHealth(name="database", healthy=False, detail=str(exc)))

    # AI provider (local)
    try:
        h = await get_provider().health()
        components.append(
            ComponentHealth(name=f"ai:{h.provider}", healthy=h.healthy, detail=h.detail)
        )
    except Exception as exc:  # noqa: BLE001
        components.append(ComponentHealth(name="ai", healthy=False, detail=str(exc)))

    overall = "ok" if all(c.healthy for c in components) else "degraded"
    return HealthResponse(status=overall, version=__version__, components=components)


@router.get("/branding", response_model=BrandingOut)
def branding() -> BrandingOut:
    return BrandingOut(
        org_name=settings.org_name,
        accent_color=settings.org_accent_color,
        default_language=settings.default_language,
    )
