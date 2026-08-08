"""Add conversations.active_document_id (structured follow-up context).

Revision ID: 0003_conversation_active_document
Revises: 0002_vehicle_extraction_raw
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_convo_active_doc"
down_revision = "0002_vehicle_extraction_raw"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations",
                  sa.Column("active_document_id", UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "active_document_id")
