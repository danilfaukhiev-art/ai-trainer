from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

import json
from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.workout import Workout, WorkoutExercise, WorkoutSetLog, TrainingPlan
from app.models.user import UserProfile
from app.models.progress import UserStreak
from app.services.workout.generator import WorkoutGenerator, AdaptationEngine
from app.services.ai.orchestrator import AIOrchestrator
from app.core.config import settings
from openai import AsyncOpenAI
from datetime import date

router = APIRouter(prefix="/workouts", tags=["workouts"])


class SetLogItem(BaseModel):
    workout_exercise_id: str
    set_number: int
    reps_done: Optional[int] = None
    weight_kg: Optional[float] = None
    rpe: Optional[int] = None


class CompleteWorkoutRequest(BaseModel):
    rpe_score: int  # 1-10
    notes: Optional[str] = None
    sets_log: list[SetLogItem] = []


@router.get("/today")
async def get_today_workout(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    generator = WorkoutGenerator(db)
    workout = await generator.get_today_workout(UUID(user_id))

    if not workout:
        next_workout = await generator.get_next_workout(UUID(user_id))
        return {
            "today": None,
            "message": "На сегодня тренировок нет — день отдыха! 🛋️",
            "next_workout": _workout_preview(next_workout) if next_workout else None,
        }

    result = await db.execute(
        select(Workout)
        .where(Workout.id == workout.id)
        .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise))
    )
    workout = result.scalar_one()

    coach_intro = (workout.rich_plan or {}).get("coach_intro", "") if workout.rich_plan else ""

    return {
        "today": _format_workout(workout),
        "message": f"Сегодня: {len(workout.exercises)} упражнений 💪",
        "coach_intro": coach_intro,
    }


@router.get("/schedule")
async def get_schedule(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all workouts for the active plan (current week + upcoming)."""
    # Get active plan
    plan_result = await db.execute(
        select(TrainingPlan).where(
            and_(TrainingPlan.user_id == UUID(user_id), TrainingPlan.status == "active")
        ).order_by(TrainingPlan.started_at.desc()).limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        return {"workouts": [], "plan_name": None, "coach_intro": None}

    # Get all workouts for this plan ordered by date
    workouts_result = await db.execute(
        select(Workout)
        .where(Workout.plan_id == plan.id)
        .options(selectinload(Workout.exercises))
        .order_by(Workout.scheduled_date)
    )
    workouts = workouts_result.scalars().all()

    coach_intro = None
    if workouts:
        first_plan = workouts[0].rich_plan or {}
        coach_intro = first_plan.get("coach_intro")

    today = date.today()
    result = []
    for w in workouts:
        rp = w.rich_plan or {}
        exercises_preview = []
        for ex in (rp.get("exercises") or []):
            preview = {"name": ex.get("name", ""), "muscle_groups": ex.get("muscle_groups", [])}
            if ex.get("is_main_lift"):
                preview["weight"] = ex.get("top_set_weight")
                preview["sets"] = ex.get("top_set_sets")
                preview["reps"] = ex.get("top_set_reps")
            else:
                preview["weight"] = ex.get("weight_kg")
                preview["sets"] = ex.get("sets")
                preview["reps"] = f"{ex.get('reps_min', '')}–{ex.get('reps_max', '')}" if ex.get("reps_min") else str(ex.get("reps", ""))
            exercises_preview.append(preview)

        result.append({
            "id": str(w.id),
            "day": w.day_number,
            "week": w.week_number,
            "scheduled_date": w.scheduled_date.isoformat() if w.scheduled_date else None,
            "status": w.status,
            "is_today": w.scheduled_date == today if w.scheduled_date else False,
            "label": rp.get("label", f"День {w.day_number}"),
            "week_focus": rp.get("week_focus", []),
            "exercises": exercises_preview,
        })

    return {
        "workouts": result,
        "plan_name": plan.name,
        "coach_intro": coach_intro,
    }


@router.get("/{workout_id}")
async def get_workout(
    workout_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workout)
        .where(Workout.id == workout_id, Workout.user_id == user_id)
        .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise))
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return _format_workout(workout)


@router.post("/{workout_id}/complete")
async def complete_workout(
    workout_id: str,
    payload: CompleteWorkoutRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workout).where(
            Workout.id == workout_id, Workout.user_id == user_id
        )
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    if workout.status == "completed":
        raise HTTPException(status_code=400, detail="Already completed")

    # Mark complete
    workout.status = "completed"
    workout.completed_at = datetime.utcnow()
    workout.rpe_score = payload.rpe_score
    workout.notes = payload.notes

    # Save sets log
    for set_data in payload.sets_log:
        log = WorkoutSetLog(
            workout_id=workout.id,
            workout_exercise_id=set_data.workout_exercise_id,
            set_number=set_data.set_number,
            reps_done=set_data.reps_done,
            weight_kg=set_data.weight_kg,
            rpe=set_data.rpe,
        )
        db.add(log)

    # Update streak
    await _update_streak(UUID(user_id), db)

    # Generate AI feedback
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    user_context = {
        "display_name": profile.display_name if profile else None,
        "goal": profile.goal if profile else "не указана",
        "fitness_level": profile.fitness_level if profile else "не указан",
        "last_workout": "только что",
        "streak": await _get_streak(UUID(user_id), db),
    }

    orchestrator = AIOrchestrator(UUID(user_id), user_context)
    ai_feedback, _ = await orchestrator.chat(
        user_message="Тренировка завершена",
        task="post_workout",
        task_data={"rpe": payload.rpe_score, "notes": payload.notes or ""},
    )
    workout.ai_feedback = ai_feedback
    await db.flush()

    # Check if adaptation needed
    plan_result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.id == workout.plan_id
        )
    )
    plan = plan_result.scalar_one_or_none()
    adaptation = {}
    if plan:
        engine = AdaptationEngine(db)
        adaptation = await engine.check_and_adapt(UUID(user_id), plan)

    return {
        "status": "completed",
        "ai_feedback": ai_feedback,
        "adaptation": adaptation if adaptation.get("action") != "maintain" else None,
    }


@router.post("/{workout_id}/skip")
async def skip_workout(
    workout_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workout).where(
            Workout.id == workout_id, Workout.user_id == user_id
        )
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout.status = "skipped"
    return {"status": "skipped"}


@router.get("/{workout_id}/warmup")
async def get_workout_warmup(
    workout_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate professional warmup for the workout."""
    result = await db.execute(
        select(Workout)
        .where(Workout.id == workout_id, Workout.user_id == user_id)
        .options(selectinload(Workout.exercises))
    )
    workout = result.scalar_one_or_none()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    exercise_names = [ex.exercise_name for ex in (workout.exercises or [])]

    # Load user profile for personalized warmup
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    fitness_level = profile.fitness_level if profile else "beginner"
    injuries = profile.injuries if profile else []
    injuries_str = ', '.join(injuries) if injuries else 'нет'
    equipment = profile.equipment if profile else "gym"

    level_label = {"beginner": "новичок", "intermediate": "средний", "advanced": "продвинутый"}.get(fitness_level, fitness_level)
    equip_note = {"minimal": "только собственный вес и резинки", "home": "дома, есть гантели и турник"}.get(equipment, "тренажёрный зал")

    prompt = f"""Ты — профессиональный тренер-реабилитолог. Создай ЭФФЕКТИВНУЮ научно обоснованную разминку.

КОНТЕКСТ:
- Упражнения тренировки: {', '.join(exercise_names)}
- Уровень: {level_label}
- Травмы/ограничения: {injuries_str}
- Оборудование: {equip_note}

СТРУКТУРА (строго соблюдай последовательность):
1. КАРДИО-РАЗОГРЕВ: 1–2 упражнения по 60–90 сек — поднять ЧСС и температуру тела
2. СУСТАВНАЯ ГИМНАСТИКА: 2–3 упражнения — вращения в суставах, задействованных в тренировке
3. ДИНАМИЧЕСКАЯ РАСТЯЖКА: 2 упражнения — динамические движения для целевых мышц
4. НЕЙРОМЫШЕЧНАЯ АКТИВАЦИЯ: 1–2 упражнения — лёгкая нагрузка для «включения» мышц

ПРАВИЛА:
- Итого 7–8 упражнений, 10–12 минут
- В notes — объясни ЗАЧЕМ это упражнение нужно перед тренировкой И КАК правильно выполнять
- При травме колена: замени выпады/приседания на сгибания сидя/разгибания
- При травме спины: замени наклоны на кошку-корову и «птица-собака»
- Нарастай по интенсивности: от лёгкого к умеренному

Верни ТОЛЬКО валидный JSON:
{{
  "duration_min": 10,
  "exercises": [
    {{
      "name": "Бег на месте с высоким коленом",
      "duration_sec": 60,
      "reps": null,
      "notes": "Запускаем кровообращение и разогреваем мышцы. Поднимай колено до уровня таза, работай руками. Дыши носом."
    }},
    {{
      "name": "Вращения в плечевых суставах",
      "duration_sec": null,
      "reps": "15 вперёд + 15 назад",
      "notes": "Увеличиваем выработку синовиальной жидкости в плечах. Делай максимально большие круги, держи руки прямыми."
    }}
  ]
}}"""

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1800,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        warmup_data = json.loads(response.choices[0].message.content)
    except Exception:
        # Fallback warmup
        warmup_data = {
            "duration_min": 10,
            "exercises": [
                {"name": "Бег на месте с высоким коленом", "duration_sec": 60, "reps": None, "notes": "Разгоняем кровообращение, поднимаем температуру тела"},
                {"name": "Прыжки Jumping Jack", "duration_sec": 45, "reps": None, "notes": "Увеличиваем ЧСС и разогреваем все группы мышц"},
                {"name": "Вращения в плечевых суставах", "duration_sec": None, "reps": "15 вперёд + 15 назад", "notes": "Разогрев плечевых суставов, профилактика травм"},
                {"name": "Вращения в тазобедренных суставах", "duration_sec": None, "reps": "12 на каждую сторону", "notes": "Мобилизация тазобедренного сустава"},
                {"name": "Динамические выпады с разворотом", "duration_sec": None, "reps": "8 на каждую ногу", "notes": "Растягиваем сгибатели бедра и активируем ягодицы"},
                {"name": "Динамические наклоны с руками за головой", "duration_sec": None, "reps": "10", "notes": "Растяжка широчайших и подготовка спины"},
                {"name": "Планка с чередованием рук", "duration_sec": 30, "reps": None, "notes": "Активация кора перед тренировкой"},
                {"name": "Приседания с паузой внизу (бодивейт)", "duration_sec": None, "reps": "10 медленно", "notes": "Активация квадрицепсов и ягодиц, мобилизация голеностопа"},
            ],
        }

    return warmup_data


def _guess_muscle_groups(name: str) -> list[str]:
    n = name.lower()
    if any(k in n for k in ["жим лёж", "жим леж", "отжим", "грудь", "пектораль"]):
        return ["chest", "triceps", "shoulders"]
    if any(k in n for k in ["жим стоя", "жим сидя", "армейский", "дельт", "плечевой"]):
        return ["shoulders", "triceps"]
    if any(k in n for k in ["тяга", "подтяг", "тяга к груди", "тяга за голов", "широчайш"]):
        return ["back", "biceps"]
    if any(k in n for k in ["присед", "квадр", "выпад", "жим ног", "разгибан ног"]):
        return ["quadriceps", "glutes", "hamstrings"]
    if any(k in n for k in ["становая", "румынская", "ягодич", "мостик", "ягод"]):
        return ["glutes", "hamstrings", "back"]
    if any(k in n for k in ["бицепс", "сгибан", "молоток"]):
        return ["biceps", "forearms"]
    if any(k in n for k in ["трицепс", "разгибан рук", "французский", "жим узким"]):
        return ["triceps"]
    if any(k in n for k in ["пресс", "планка", "скручив", "подъем ног", "вакуум"]):
        return ["abs", "core"]
    if any(k in n for k in ["икр", "голень", "подъем на нос"]):
        return ["calves"]
    if any(k in n for k in ["жим", "отжим"]):
        return ["chest", "triceps"]
    if any(k in n for k in ["кардио", "бег", "прыж", "скакалк", "берпи"]):
        return ["cardio"]
    return []


def _format_workout(workout: Workout) -> dict:
    return {
        "id": str(workout.id),
        "week": workout.week_number,
        "day": workout.day_number,
        "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
        "status": workout.status,
        "rich_plan": workout.rich_plan,
        "exercises": [
            {
                "id": str(ex.id),
                "name": ex.exercise_name,
                "sets": ex.sets,
                "reps": f"{ex.reps_min}–{ex.reps_max}" if ex.reps_min and ex.reps_max else None,
                "rest_sec": ex.rest_seconds,
                "notes": ex.notes,
                "weight_kg": float(ex.weight_kg) if ex.weight_kg else None,
                "muscle_groups": (
                    ex.muscle_groups
                    or (ex.exercise.muscle_groups if ex.exercise and ex.exercise.muscle_groups else None)
                    or _guess_muscle_groups(ex.exercise_name or "")
                ),
                "gif_url": (
                    ex.gif_url
                    or (ex.exercise.gif_url if ex.exercise else None)
                ),
            }
            for ex in (workout.exercises or [])
        ],
        "rpe_score": workout.rpe_score,
        "ai_feedback": workout.ai_feedback,
    }


def _workout_preview(workout: Workout) -> dict:
    return {
        "id": str(workout.id),
        "scheduled_date": workout.scheduled_date.isoformat() if workout.scheduled_date else None,
        "week": workout.week_number,
        "day": workout.day_number,
    }


async def _update_streak(user_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = result.scalar_one_or_none()
    today = date.today()

    if not streak:
        streak = UserStreak(user_id=user_id, current_streak=1, max_streak=1, last_activity=today)
        db.add(streak)
    else:
        from datetime import timedelta
        if streak.last_activity == today - timedelta(days=1):
            streak.current_streak += 1
        elif streak.last_activity != today:
            streak.current_streak = 1

        if streak.current_streak > streak.max_streak:
            streak.max_streak = streak.current_streak
        streak.last_activity = today


async def _get_streak(user_id: UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = result.scalar_one_or_none()
    return streak.current_streak if streak else 0
