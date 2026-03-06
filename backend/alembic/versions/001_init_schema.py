"""Init schema: workspaces, users, meetings, action_items

Revision ID: 001
Revises:
Create Date: 2026-03-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "workspaces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default=sa.text("'free'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint("uq_workspaces_slug", "workspaces", ["slug"])

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            comment="Entspricht der Clerk User ID",
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'member'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])

    # MeetingStatus ENUM
    meeting_status_enum = postgresql.ENUM(
        "pending",
        "transcribing",
        "transcription_failed",
        "summarizing",
        "transcript_only",
        "indexing",
        "not_indexed",
        "done",
        name="meetingstatus",
        create_type=True,
    )
    meeting_status_enum.create(op.get_bind())

    op.create_table(
        "meetings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("audio_path", sa.Text, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "transcribing",
                "transcription_failed",
                "summarizing",
                "transcript_only",
                "indexing",
                "not_indexed",
                "done",
                name="meetingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column(
            "consent_given",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_text_version", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_meetings_workspace_id", "meetings", ["workspace_id"])
    op.create_index("ix_meetings_status", "meetings", ["status"])

    op.create_table(
        "action_items",
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
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("assignee_name", sa.String(100), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'open'")
        ),
        sa.Column("timestamp_sec", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("source_quote", sa.Text, nullable=True),
    )
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"])
    op.create_index("ix_action_items_workspace_id", "action_items", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("action_items")
    op.drop_table("meetings")
    op.execute("DROP TYPE IF EXISTS meetingstatus")
    op.drop_table("users")
    op.drop_table("workspaces")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
