"""
Workout generation service.
Generates plans, schedules workouts, handles adaptation.
"""
import hashlib
import json
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile
from app.models.workout import TrainingPlan, Workout, WorkoutExercise
from app.services.ai.orchestrator import AIOrchestrator
from app.services.workout.exercise_gif import fetch_exercise_data_bulk


class WorkoutGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_plan(self, user_id: UUID, profile: UserProfile) -> TrainingPlan:
        """Generate 4-week AI training plan for user."""

        profile_dict = {
            "goal": profile.goal,
            "fitness_level": profile.fitness_level,
            "equipment": profile.equipment,
            "available_days": profile.available_days,
            "session_minutes": profile.session_minutes,
            "injuries": profile.injuries or [],
            "medical_notes": profile.medical_notes or "",
            "gender": profile.gender or "male",
            "age": profile.age,
            "weight_kg": float(profile.weight_kg) if profile.weight_kg else None,
            "height_cm": profile.height_cm,
            "display_name": profile.display_name,
            "sport_background": getattr(profile, "sport_background", None),
        }

        # Check if same plan already exists (dedup)
        prompt_hash = hashlib.md5(
            json.dumps(profile_dict, sort_keys=True).encode()
        ).hexdigest()

        existing = await self.db.execute(
            select(TrainingPlan).where(
                and_(
                    TrainingPlan.user_id == user_id,
                    TrainingPlan.ai_prompt_hash == prompt_hash,
                    TrainingPlan.status == "active",
                )
            )
        )
        if existing_plan := existing.scalar_one_or_none():
            return existing_plan

        # Deactivate current active plan
        old_plans = await self.db.execute(
            select(TrainingPlan).where(
                and_(TrainingPlan.user_id == user_id, TrainingPlan.status == "active")
            )
        )
        for p in old_plans.scalars():
            p.status = "paused"

        # Generate via AI
        orchestrator = AIOrchestrator(user_id=user_id, user_context=profile_dict)
        plan_data = await orchestrator.generate_workout_plan(profile_dict)

        plan = TrainingPlan(
            user_id=user_id,
            name=plan_data.get("name", "Твоя программа"),
            goal=profile.goal,
            split_type=plan_data.get("split_type", "full_body"),
            plan_data=plan_data,
            ai_prompt_hash=prompt_hash,
            started_at=date.today(),
        )
        self.db.add(plan)
        await self.db.flush()

        # Schedule workouts for week 1
        await self._schedule_week(plan, plan_data, week_number=1)

        return plan

    async def _schedule_week(
        self, plan: TrainingPlan, plan_data: dict, week_number: int
    ):
        """Create Workout records for given week (supports both rich and legacy formats)."""
        # Support new rich format (days at top level) and legacy (weeks[].days)
        days_list = plan_data.get("days") or next(
            (w.get("days", []) for w in plan_data.get("weeks", []) if w.get("week") == week_number),
            [],
        )
        if not days_list:
            return

        start_date = date.today()

        for day_data in days_list:
            day_num = day_data.get("day", 1)
            day_offset = day_num - 1
            scheduled = start_date + timedelta(days=day_offset)

            exercises_data = day_data.get("exercises", [])

            # Fetch GIF URLs + instructions for all exercises in bulk
            names_en = [e.get("name_en", "") for e in exercises_data if e.get("name_en")]
            ex_data_map: dict[str, dict] = {}
            try:
                ex_data_map = await fetch_exercise_data_bulk(names_en)
            except Exception:
                pass

            # Attach gif_url + instructions into exercises_data for rich_plan storage
            exercises_with_gifs = []
            for e in exercises_data:
                entry = dict(e)
                fetched = ex_data_map.get(e.get("name_en", ""), {})
                entry["gif_url"] = fetched.get("gif_url")
                entry["instructions"] = fetched.get("instructions", [])
                exercises_with_gifs.append(entry)

            # Build rich_plan for this day
            rich_plan = {
                "label": day_data.get("label", day_data.get("focus", f"День {day_num}")),
                "week_focus": plan_data.get("week_focus", []),
                "weekly_rules": plan_data.get("weekly_rules", []),
                "weekly_goal": plan_data.get("weekly_goal", ""),
                "coach_intro": plan_data.get("coach_intro", ""),
                "exercises": exercises_with_gifs,
            }

            workout = Workout(
                plan_id=plan.id,
                user_id=plan.user_id,
                week_number=week_number,
                day_number=day_num,
                scheduled_date=scheduled,
                rich_plan=rich_plan,
            )
            self.db.add(workout)
            await self.db.flush()

            for idx, ex_data in enumerate(exercises_data):
                name_en = ex_data.get("name_en", "")
                gif_url = ex_data_map.get(name_en, {}).get("gif_url")
                muscle_groups = ex_data.get("muscle_groups") or []

                # Determine tracking weight/sets from rich structure
                is_main = ex_data.get("is_main_lift", False)
                if is_main and ex_data.get("top_set_weight"):
                    weight = ex_data["top_set_weight"]
                    sets = ex_data.get("top_set_sets", 3)
                    reps_min = reps_max = ex_data.get("top_set_reps", 5)
                else:
                    weight = ex_data.get("weight_kg")
                    sets = ex_data.get("sets", 3)
                    reps_min = ex_data.get("reps_min")
                    reps_max = ex_data.get("reps_max")
                    if not reps_min:
                        reps_val = ex_data.get("reps", 10)
                        reps_min = reps_max = reps_val

                notes = ex_data.get("coach_note") or ex_data.get("notes") or ex_data.get("technique")

                ex = WorkoutExercise(
                    workout_id=workout.id,
                    exercise_name=ex_data.get("name"),
                    order_index=idx,
                    sets=sets,
                    reps_min=reps_min,
                    reps_max=reps_max,
                    weight_kg=float(weight) if weight else None,
                    rest_seconds=ex_data.get("rest_sec"),
                    notes=notes,
                    gif_url=gif_url,
                    muscle_groups=muscle_groups if muscle_groups else None,
                )
                self.db.add(ex)

    async def get_today_workout(self, user_id: UUID) -> Optional[Workout]:
        """Get today's scheduled workout."""
        today = date.today()
        result = await self.db.execute(
            select(Workout).where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date == today,
                    Workout.status == "pending",
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_next_workout(self, user_id: UUID) -> Optional[Workout]:
        """Get next pending workout."""
        today = date.today()
        result = await self.db.execute(
            select(Workout).where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date >= today,
                    Workout.status == "pending",
                )
            ).order_by(Workout.scheduled_date).limit(1)
        )
        return result.scalar_one_or_none()


class AdaptationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_adapt(self, user_id: UUID, plan: TrainingPlan) -> dict:
        """Analyse recent workouts and apply weight adjustments to pending workouts."""
        fourteen_days_ago = date.today() - timedelta(days=14)

        result = await self.db.execute(
            select(Workout).where(
                and_(
                    Workout.user_id == user_id,
                    Workout.scheduled_date >= fourteen_days_ago,
                )
            )
        )
        recent = result.scalars().all()

        if not recent:
            return {"action": "maintain", "reason": "Нет данных"}

        total = len(recent)
        completed = [w for w in recent if w.status == "completed"]
        skipped = [w for w in recent if w.status == "skipped"]
        with_rpe = [w for w in completed if w.rpe_score is not None]

        skip_rate = len(skipped) / total if total else 0
        avg_rpe = sum(w.rpe_score for w in with_rpe) / len(with_rpe) if with_rpe else 5.0

        if skip_rate >= 0.4 or avg_rpe >= 9:
            await self._adjust_pending_weights(user_id, multiplier=0.75)
            return {
                "action": "deload",
                "reason": f"Пропуски: {len(skipped)}/{total}, RPE: {avg_rpe:.1f}",
                "adjustment": "Снижаем нагрузку на 25% на следующих тренировках",
            }

        if avg_rpe <= 5 and len(completed) >= 6:
            await self._adjust_pending_weights(user_id, multiplier=1.075)
            return {
                "action": "progress",
                "reason": f"RPE слишком низкий: {avg_rpe:.1f}",
                "adjustment": "Увеличиваем вес на 7.5% на следующих тренировках",
            }

        if len(completed) < 3 and total >= 6:
            return {
                "action": "plan_revision",
                "reason": "Слишком мало выполненных тренировок",
                "adjustment": "Пересматриваем расписание",
            }

        return {"action": "maintain", "reason": "Прогресс в норме"}

    async def _adjust_pending_weights(self, user_id: UUID, multiplier: float):
        """Apply weight multiplier to all pending workout exercises."""
        pending_result = await self.db.execute(
            select(Workout).where(
                and_(
                    Workout.user_id == user_id,
                    Workout.status == "pending",
                    Workout.scheduled_date > date.today(),
                )
            )
        )
        pending_workouts = pending_result.scalars().all()

        for workout in pending_workouts:
            ex_result = await self.db.execute(
                select(WorkoutExercise).where(WorkoutExercise.workout_id == workout.id)
            )
            exercises = ex_result.scalars().all()
            for ex in exercises:
                if ex.weight_kg:
                    raw = float(ex.weight_kg) * multiplier
                    # Round to nearest 2.5 kg
                    ex.weight_kg = round(raw / 2.5) * 2.5
