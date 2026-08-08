"""Audit trail and external-AI escalation records (spec §7, §34).

Audit records intentionally do NOT store passwords, tokens, or full confidential
prompt/document contents.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class AuditEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(80))
    result: Mapped[str] = mapped_column(String(40), default="success")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    session_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    detail: Mapped[str | None] = mapped_column(Text)


class ExternalAIAudit(UUIDMixin, TimestampMixin, Base):
    """One record per external-AI (OpenAI) request (spec §19/§20).

    Never stores API keys, full prompts, or document contents — only metadata and
    usage counts.
    """

    __tablename__ = "external_ai_audit"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    document_id: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(40), default="openai")
    model: Mapped[str | None] = mapped_column(String(80))
    request_type: Mapped[str] = mapped_column(String(40), default="escalation")
    redaction_applied: Mapped[bool] = mapped_column(default=False)
    context_character_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(40))
    department: Mapped[str | None] = mapped_column(String(120))


class ExternalAIEscalation(UUIDMixin, TimestampMixin, Base):
    """Records a manual global-AI escalation event without duplicating sensitive
    prompt contents (spec §7)."""

    __tablename__ = "external_ai_escalations"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column()
    data_sensitivity: Mapped[str | None] = mapped_column(String(40))
    sensitive_types_detected: Mapped[list] = mapped_column(JSON, default=list)
    prompt_generated: Mapped[bool] = mapped_column(default=False)
    answer_imported: Mapped[bool] = mapped_column(default=False)
    approved_into_kb: Mapped[bool] = mapped_column(default=False)
