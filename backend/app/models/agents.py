"""Agent framework and tool registry (spec §19, §36).

Agents are data-driven, not hard-coded per agent. Tools declare permissions and
risk level; high-risk tools require explicit user confirmation at call time.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Table, Column, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

agent_tools = Table(
    "agent_tools",
    Base.metadata,
    Column("agent_id", UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("tool_id", UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
)


class Tool(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    required_permission: Mapped[str | None] = mapped_column(String(80))
    risk_level: Mapped[str] = mapped_column(String(20), default="low")  # low|medium|high
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    icon: Mapped[str | None] = mapped_column(String(80))
    system_instructions: Mapped[str | None] = mapped_column(String(8000))
    model: Mapped[str | None] = mapped_column(String(120))
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    # Knowledge-base scoping (list of KB ids) — retrieval is still permission-filtered.
    allowed_knowledge_bases: Mapped[list] = mapped_column(JSON, default=list)

    tools: Mapped[list[Tool]] = relationship(secondary=agent_tools, lazy="selectin")
