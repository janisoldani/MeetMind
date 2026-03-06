import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MeetingStatus(str, enum.Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    TRANSCRIPTION_FAILED = "transcription_failed"
    SUMMARIZING = "summarizing"
    TRANSCRIPT_ONLY = "transcript_only"  # LLM fehlgeschlagen, Transkript vorhanden
    INDEXING = "indexing"
    NOT_INDEXED = "not_indexed"  # Embeddings fehlgeschlagen
    DONE = "done"


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meetingstatus", create_type=False),
        nullable=False,
        default=MeetingStatus.PENDING,
    )
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # DSGVO Consent
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_text_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="meetings")  # noqa: F821
    action_items: Mapped[list["ActionItem"]] = relationship(  # noqa: F821
        back_populates="meeting", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["Embedding"]] = relationship(  # noqa: F821
        back_populates="meeting", cascade="all, delete-orphan"
    )
