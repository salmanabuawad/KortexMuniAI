"""Agent listing (data-driven agent framework)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import AgentOut
from app.auth.deps import get_current_user
from app.db.session import get_db
from app.models.agents import Agent
from app.models.iam import User

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Agent]:
    return list(db.scalars(select(Agent).where(Agent.enabled.is_(True)).order_by(Agent.name)))
