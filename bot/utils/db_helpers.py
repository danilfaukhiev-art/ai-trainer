"""Lightweight DB helpers for bot handlers."""
from typing import Optional, Tuple
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.models.user import User, UserProfile, OnboardingState
from app.models.subscription import Subscription


async def get_or_create_user(tg_user) -> Tuple[User, bool]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()
        is_new = False

        if not user:
            user = User(
                telegram_id=tg_user.id,
                telegram_username=getattr(tg_user, "username", None),
                language_code=getattr(tg_user, "language_code", "ru"),
            )
            db.add(user)
            await db.flush()  # get user.id

            onboarding = OnboardingState(user_id=user.id, step="name")
            db.add(onboarding)

            pro_sub = Subscription(
                user_id=user.id,
                tier="pro",
                status="active",
                payment_provider="manual",
            )
            db.add(pro_sub)

            await db.commit()
            await db.refresh(user)
            is_new = True

        return user, is_new


async def get_user_profile(user_id) -> Optional[UserProfile]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def get_today_workout(user_id) -> Optional[dict]:
    from datetime import date
    from sqlalchemy.orm import selectinload
    from app.models.workout import Workout

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workout)
            .where(
                Workout.user_id == user_id,
                Workout.scheduled_date == date.today(),
                Workout.status == "pending",
            )
            .options(selectinload(Workout.exercises))
        )
        workout = result.scalar_one_or_none()
        if not workout:
            return None

        return {
            "id": str(workout.id),
            "exercises": [
                {
                    "name": ex.exercise_name,
                    "sets": ex.sets,
                    "reps": f"{ex.reps_min}–{ex.reps_max}",
                    "rest_sec": ex.rest_seconds,
                }
                for ex in workout.exercises
            ],
        }
