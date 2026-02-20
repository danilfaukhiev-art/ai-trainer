import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, SmallInteger, Text, TIMESTAMP, ForeignKey, Date, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MealEntry(Base):
    __tablename__ = "meal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    meal_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # breakfast | lunch | dinner | snack
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    calories: Mapped[Optional[int]] = mapped_column(SmallInteger)
    protein_g: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    fats_g: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    carbs_g: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    portion_g: Mapped[Optional[int]] = mapped_column(SmallInteger)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class WaterLog(Base):
    __tablename__ = "water_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_ml: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
