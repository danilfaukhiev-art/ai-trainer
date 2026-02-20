import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, SmallInteger, Text, TIMESTAMP, ForeignKey, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ProgressEntry(Base):
    __tablename__ = "progress_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    body_fat_pct: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    chest_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    waist_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    hips_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    bicep_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    forearm_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    thigh_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    calf_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    storage_key: Mapped[Optional[str]] = mapped_column(String(256))
    taken_date: Mapped[Optional[date]] = mapped_column(Date)
    type: Mapped[Optional[str]] = mapped_column(String(16))
    # front | side | back
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class UserStreak(Base):
    __tablename__ = "user_streaks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    current_streak: Mapped[int] = mapped_column(SmallInteger, default=0)
    max_streak: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_activity: Mapped[Optional[date]] = mapped_column(Date)
