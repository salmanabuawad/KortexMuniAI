"""Initial MuniAI schema (all core + vehicle-module tables).

This first migration provisions the pgvector extension and creates the full
schema directly from the SQLAlchemy metadata, so the database matches the models
exactly without hand-transcribing ~30 tables. Subsequent changes use normal
Alembic autogenerate migrations.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-08
"""

from __future__ import annotations

from alembic import op

# Importing the models registers every table on Base.metadata.
from app.db.base import Base
import app.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # pgvector must exist before creating the embeddings table's Vector column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)

    # Approximate-nearest-neighbour index for semantic search (cosine).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_hnsw "
        "ON embeddings USING hnsw (vector vector_cosine_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_hnsw")
    Base.metadata.drop_all(bind=bind)
