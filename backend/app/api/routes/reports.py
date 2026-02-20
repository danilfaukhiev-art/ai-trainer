"""
Weekly Report — aggregated stats for the last 7 days.
"""
from datetime import date, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.user import UserProfile
from app.models.workout import Workout
from app.models.progress import ProgressEntry, UserStreak
from app.models.nutrition import MealEntry
from app.services.ai.orchestrator import AIOrchestrator

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly")
async def get_weekly_report(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    week_start = today - timedelta(days=6)

    # ── Workouts ──────────────────────────────────────────────
    workouts_result = await db.execute(
        select(Workout).where(
            and_(
                Workout.user_id == user_id,
                Workout.scheduled_date >= week_start,
                Workout.scheduled_date <= today,
            )
        )
    )
    workouts = workouts_result.scalars().all()
    completed = [w for w in workouts if w.status == "completed"]
    avg_rpe = round(
        sum(w.rpe_score for w in completed if w.rpe_score) / len(completed), 1
    ) if completed else None

    # ── Weight ────────────────────────────────────────────────
    weight_result = await db.execute(
        select(ProgressEntry).where(
            and_(
                ProgressEntry.user_id == user_id,
                ProgressEntry.recorded_date >= week_start,
                ProgressEntry.recorded_date <= today,
                ProgressEntry.weight_kg.isnot(None),
            )
        ).order_by(ProgressEntry.recorded_date)
    )
    weight_entries = weight_result.scalars().all()
    weight_start = float(weight_entries[0].weight_kg) if weight_entries else None
    weight_end = float(weight_entries[-1].weight_kg) if weight_entries else None
    weight_change = round(weight_end - weight_start, 1) if (weight_start and weight_end) else None

    # ── Nutrition ─────────────────────────────────────────────
    nutrition_result = await db.execute(
        select(
            func.avg(MealEntry.calories).label("avg_cal"),
            func.avg(MealEntry.protein_g).label("avg_protein"),
            func.avg(MealEntry.carbs_g).label("avg_carbs"),
            func.avg(MealEntry.fats_g).label("avg_fat"),
            func.count(func.distinct(MealEntry.meal_date)).label("days_logged"),
        ).where(
            and_(
                MealEntry.user_id == user_id,
                MealEntry.meal_date >= week_start,
                MealEntry.meal_date <= today,
            )
        )
    )
    nut = nutrition_result.one()

    # ── Streak ────────────────────────────────────────────────
    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = streak_result.scalar_one_or_none()

    # ── AI Summary ────────────────────────────────────────────
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    stats_text = (
        f"Тренировок завершено: {len(completed)} из {len(workouts)}. "
        f"Средний RPE: {avg_rpe or 'нет данных'}. "
        f"Изменение веса: {f'{weight_change:+.1f} кг' if weight_change is not None else 'нет данных'}. "
        f"Калорий в день (среднее): {int(nut.avg_cal) if nut.avg_cal else 'нет данных'}. "
        f"Стрик: {streak.current_streak if streak else 0} дней."
    )

    ai_summary = None
    try:
        user_context = {
            "display_name": profile.display_name if profile else None,
            "goal": profile.goal if profile else "не указана",
            "fitness_level": profile.fitness_level if profile else "не указан",
            "motivation_type": profile.motivation_type if profile else None,
            "training_style": profile.training_style if profile else None,
            "medical_notes": profile.medical_notes if profile else None,
            "last_workout": "нет данных",
            "streak": streak.current_streak if streak else 0,
        }
        orchestrator = AIOrchestrator(UUID(user_id), user_context)
        ai_summary, _ = await orchestrator.chat(
            user_message=f"Дай краткий итог моей недели (2–3 предложения + совет на следующую неделю): {stats_text}",
            task="general",
        )
    except Exception:
        ai_summary = None

    return {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "workouts": {
            "completed": len(completed),
            "scheduled": len(workouts),
            "completion_rate": round(len(completed) / len(workouts) * 100) if workouts else 0,
            "avg_rpe": avg_rpe,
        },
        "weight": {
            "start": weight_start,
            "end": weight_end,
            "change": weight_change,
        },
        "nutrition": {
            "avg_calories": int(nut.avg_cal) if nut.avg_cal else None,
            "avg_protein": int(nut.avg_protein) if nut.avg_protein else None,
            "avg_carbs": int(nut.avg_carbs) if nut.avg_carbs else None,
            "avg_fat": int(nut.avg_fat) if nut.avg_fat else None,
            "days_logged": int(nut.days_logged) if nut.days_logged else 0,
        },
        "streak": {
            "current": streak.current_streak if streak else 0,
            "max": streak.max_streak if streak else 0,
        },
        "ai_summary": ai_summary,
    }
