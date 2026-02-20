import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, SmallInteger, Text, Boolean, ARRAY
from sqlalchemy import TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64))
    language_code: Mapped[str] = mapped_column(String(8), default="ru")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    data_consent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    onboarding: Mapped[Optional["OnboardingState"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(64))
    goal: Mapped[Optional[str]] = mapped_column(String(500))
    gender: Mapped[Optional[str]] = mapped_column(String(16))
    # male | female | other
    age: Mapped[Optional[int]] = mapped_column(SmallInteger)
    height_cm: Mapped[Optional[int]] = mapped_column(SmallInteger)
    weight_kg: Mapped[Optional[float]] = mapped_column()
    fitness_level: Mapped[Optional[str]] = mapped_column(String(16))
    # beginner | intermediate | advanced
    equipment: Mapped[Optional[str]] = mapped_column(String(32))
    # home | gym | minimal
    injuries: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), default=list)
    available_days: Mapped[Optional[int]] = mapped_column(SmallInteger)
    session_minutes: Mapped[Optional[int]] = mapped_column(SmallInteger)
    medical_notes: Mapped[Optional[str]] = mapped_column(Text)
    motivation_type: Mapped[Optional[str]] = mapped_column(String(32))
    training_style: Mapped[Optional[str]] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class OnboardingState(Base):
    __tablename__ = "onboarding_state"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    step: Mapped[str] = mapped_column(String(32), default="name")
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped["User"] = relationship(back_populates="onboarding")
