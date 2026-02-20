import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, SmallInteger, Text, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4
    )
    role: Mapped[str] = mapped_column(String(16))
    # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    tokens_used: Mapped[Optional[int]] = mapped_column(SmallInteger)
    model: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    storage_key: Mapped[Optional[str]] = mapped_column(String(256))
    exercise_name: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending | processing | done | failed
    errors_found: Mapped[Optional[list]] = mapped_column(JSON)
    corrections: Mapped[Optional[list]] = mapped_column(JSON)
    checklist: Mapped[Optional[list]] = mapped_column(JSON)
    overall_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Это рекомендации по технике, не медицинский совет. При болях — обратитесь к врачу."
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
