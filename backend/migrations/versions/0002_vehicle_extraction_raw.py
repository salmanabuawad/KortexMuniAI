"""Add raw-extraction columns to vehicle_documents.

Stores the full structured extraction (fields + candidates + debug), the OCR
engine used, and the processing version — so re-runs keep provenance and the
debug view can explain why a field was chosen.

Revision ID: 0002_vehicle_extraction_raw
Revises: 0001_initial
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_vehicle_extraction_raw"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicle_documents",
                  sa.Column("extraction_json", sa.JSON(), nullable=True))
    op.add_column("vehicle_documents",
                  sa.Column("ocr_engine", sa.String(length=40), nullable=True))
    op.add_column("vehicle_documents",
                  sa.Column("processing_version", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicle_documents", "processing_version")
    op.drop_column("vehicle_documents", "ocr_engine")
    op.drop_column("vehicle_documents", "extraction_json")
