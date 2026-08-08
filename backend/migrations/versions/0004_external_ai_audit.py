"""Add external_ai_audit table (OpenAI request metadata + usage).

Revision ID: 0004_external_ai_audit
Revises: 0003_convo_active_doc
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_external_ai_audit"
down_revision = "0003_convo_active_doc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_ai_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("document_id", sa.String(length=80)),
        sa.Column("provider", sa.String(length=40), server_default="openai"),
        sa.Column("model", sa.String(length=80)),
        sa.Column("request_type", sa.String(length=40), server_default="escalation"),
        sa.Column("redaction_applied", sa.Boolean(), server_default=sa.false()),
        sa.Column("context_character_count", sa.Integer(), server_default="0"),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("success", sa.Boolean(), server_default=sa.false()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_code", sa.String(length=40)),
        sa.Column("department", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("external_ai_audit")
