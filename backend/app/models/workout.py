import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    String, SmallInteger, Text, Boolean,
    TIMESTAMP, ForeignKey, JSON, Date, ARRAY, Numeric
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Exercise(Base):
    """Global exercise library"""
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[Optional[str]] = mapped_column(String(128))
    muscle_groups: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(32)))
    equipment: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(32)))
    difficulty: Mapped[Optional[str]] = mapped_column(String(16))
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    video_url: Mapped[Optional[str]] = mapped_column(String(256))
    gif_url: Mapped[Optional[str]] = mapped_column(String(512))
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False)


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[Optional[str]] = mapped_column(String(128))
    goal: Mapped[Optional[str]] = mapped_column(String(500))
    weeks_total: Mapped[int] = mapped_column(SmallInteger, default=4)
    current_week: Mapped[int] = mapped_column(SmallInteger, default=1)
    split_type: Mapped[Optional[str]] = mapped_column(String(32))
    # full_body | upper_lower | ppl | home
    status: Mapped[str] = mapped_column(String(16), default="active")
    # active | completed | paused
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    plan_data: Mapped[Optional[dict]] = mapped_column(JSON)  # full AI-generated plan
    started_at: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )

    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_plans.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    week_number: Mapped[int] = mapped_column(SmallInteger)
    day_number: Mapped[int] = mapped_column(SmallInteger)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending | completed | skipped
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    rpe_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    ai_feedback: Mapped[Optional[str]] = mapped_column(Text)
    rich_plan: Mapped[Optional[dict]] = mapped_column(JSON)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="workouts")
    user: Mapped["User"] = relationship(back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index"
    )
    sets_log: Mapped[list["WorkoutSetLog"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workouts.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="SET NULL")
    )
    exercise_name: Mapped[Optional[str]] = mapped_column(String(128))  # fallback
    order_index: Mapped[int] = mapped_column(SmallInteger, default=0)
    sets: Mapped[Optional[int]] = mapped_column(SmallInteger)
    reps_min: Mapped[Optional[int]] = mapped_column(SmallInteger)
    reps_max: Mapped[Optional[int]] = mapped_column(SmallInteger)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    rest_seconds: Mapped[Optional[int]] = mapped_column(SmallInteger)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    gif_url: Mapped[Optional[str]] = mapped_column(String(512))
    muscle_groups: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(32)))

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
    exercise: Mapped[Optional["Exercise"]] = relationship(foreign_keys=[exercise_id])


class WorkoutSetLog(Base):
    __tablename__ = "workout_sets_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workouts.id", ondelete="CASCADE")
    )
    workout_exercise_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workout_exercises.id", ondelete="SET NULL")
    )
    set_number: Mapped[int] = mapped_column(SmallInteger)
    reps_done: Mapped[Optional[int]] = mapped_column(SmallInteger)
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    rpe: Mapped[Optional[int]] = mapped_column(SmallInteger)
    logged_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )

    workout: Mapped["Workout"] = relationship(back_populates="sets_log")
