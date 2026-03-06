"""Add pgvector: embeddings table with HNSW index

Revision ID: 002
Revises: 001
Create Date: 2026-03-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding-Dimension (384 für all-MiniLM-L6-v2)
# ACHTUNG: Wechsel auf OpenAI (1536 dim) erfordert Migration + Re-Embedding aller Daten
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "embeddings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("start_sec", sa.Float, nullable=True),
        sa.Column("end_sec", sa.Float, nullable=True),
        sa.Column(
            "embedding",
            sa.Text,  # Placeholder — pgvector type wird via raw SQL gesetzt
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )

    # embedding Spalte auf vector(384) setzen (pgvector-Typ)
    op.execute(f"ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM})")

    op.create_index("ix_embeddings_meeting_id", "embeddings", ["meeting_id"])
    op.create_index("ix_embeddings_workspace_id", "embeddings", ["workspace_id"])

    # HNSW-Index für schnelle Cosine-Similarity-Suche
    op.execute("""
        CREATE INDEX ix_embeddings_hnsw
        ON embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)
    """)


def downgrade() -> None:
    op.drop_table("embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
