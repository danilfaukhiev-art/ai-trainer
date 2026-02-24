from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.user import User, UserProfile, OnboardingState
from app.services.workout.generator import WorkoutGenerator

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Onboarding steps in order — consent MUST be first
STEPS = [
    "consent",
    "name",
    "goal",
    "gender",
    "sport_background",
    "age",
    "height",
    "weight",
    "fitness_level",
    "equipment",
    "inventory",
    "injuries",
    "medical_notes",
    "available_days",
    "session_minutes",
    "motivation_type",
    "training_style",
]

STEP_NEXT = {s: STEPS[i + 1] for i, s in enumerate(STEPS[:-1])}
STEP_NEXT[STEPS[-1]] = "complete"

STEP_QUESTIONS = {
    "consent": {
        "question": "Условия использования",
        "type": "consent",
    },
    "name": {
        "question": "Как тебя зовут?",
        "type": "text",
        "placeholder": "Введи своё имя",
    },
    "goal": {
        "question": "Какова твоя главная цель?",
        "options": [
            {"value": "fat_loss", "label": "Похудеть", "emoji": "🔥"},
            {"value": "muscle_gain", "label": "Набрать мышцы", "emoji": "💪"},
            {"value": "health", "label": "Здоровье и тонус", "emoji": "❤️"},
            {"value": "endurance", "label": "Выносливость", "emoji": "⚡"},
            {"value": "custom", "label": "Своя цель", "sub": "напишу сам", "emoji": "✏️"},
        ],
    },
    "gender": {
        "question": "Твой пол?",
        "options": [
            {"value": "male", "label": "Мужской", "emoji": "💪"},
            {"value": "female", "label": "Женский", "emoji": "🌸"},
        ],
    },
    "sport_background": {
        "question": "Есть ли у тебя спортивные регалии?",
        "options": [
            {"value": "none", "label": "Нет, начинаю с нуля", "emoji": "🌱"},
            {"value": "amateur", "label": "Любитель — хожу в зал для себя", "emoji": "🏃"},
            {"value": "semi_pro", "label": "Участвовал в соревнованиях", "emoji": "🏅"},
            {"value": "pro", "label": "Профессиональный спортсмен", "emoji": "🏆"},
        ],
    },
    "age": {"question": "Сколько тебе лет?", "type": "number", "min": 14, "max": 80},
    "height": {"question": "Твой рост (см)?", "type": "number", "min": 140, "max": 220},
    "weight": {"question": "Твой вес (кг)?", "type": "number", "min": 40, "max": 200},
    "fitness_level": {
        "question": "Твой уровень подготовки?",
        "options": [
            {"value": "beginner", "label": "Новичок", "sub": "до 6 месяцев", "emoji": "🌱"},
            {"value": "intermediate", "label": "Средний", "sub": "6 месяцев – 2 года", "emoji": "📈"},
            {"value": "advanced", "label": "Продвинутый", "sub": "более 2 лет", "emoji": "🚀"},
        ],
    },
    "equipment": {
        "question": "Где планируешь тренироваться?",
        "options": [
            {"value": "gym", "label": "Тренажёрный зал", "emoji": "🏋️"},
            {"value": "home", "label": "Дома", "emoji": "🏠"},
            {"value": "street", "label": "На улице / парк", "emoji": "🌳"},
        ],
    },
    "inventory": {
        "question": "Какой инвентарь есть в наличии?",
        "options": [
            {"value": "barbell", "label": "Штанга и гантели", "emoji": "🏋️"},
            {"value": "dumbbells", "label": "Только гантели", "emoji": "💪"},
            {"value": "bands", "label": "Резинки / петли", "emoji": "🎽"},
            {"value": "none", "label": "Нет инвентаря", "sub": "только собственный вес", "emoji": "🤸"},
        ],
    },
    "injuries": {
        "question": "Есть ли ограничения или травмы?",
        "type": "multiselect",
        "options": [
            {"value": "none", "label": "Нет ограничений", "emoji": "✅"},
            {"value": "back", "label": "Спина / позвоночник", "emoji": "🦴"},
            {"value": "knees", "label": "Колени", "emoji": "🦵"},
            {"value": "shoulders", "label": "Плечи", "emoji": "💆"},
            {"value": "wrists", "label": "Запястья", "emoji": "🤲"},
        ],
    },
    "medical_notes": {
        "question": "Есть ли медицинские особенности?",
        "type": "text",
        "placeholder": "Астма, диабет, проблемы с сердцем, аллергии... или оставь пустым",
    },
    "available_days": {
        "question": "Сколько дней в неделю готов тренироваться?",
        "options": [
            {"value": 1, "label": "1 день", "sub": "минимальная нагрузка", "emoji": "🌱"},
            {"value": 2, "label": "2 дня", "sub": "лёгкий старт", "emoji": "🌿"},
            {"value": 3, "label": "3 дня", "sub": "оптимально для начала", "emoji": "📅"},
            {"value": 4, "label": "4 дня", "sub": "хороший баланс", "emoji": "🗓"},
            {"value": 5, "label": "5 дней", "sub": "серьёзный подход", "emoji": "💯"},
            {"value": 6, "label": "6 дней", "sub": "максимальный прогресс", "emoji": "⚡"},
        ],
    },
    "session_minutes": {
        "question": "Сколько времени на тренировку?",
        "options": [
            {"value": 30, "label": "30 минут", "sub": "быстро и эффективно", "emoji": "⏱"},
            {"value": 45, "label": "45 минут", "sub": "золотой стандарт", "emoji": "⏰"},
            {"value": 60, "label": "60 минут", "sub": "полноценная тренировка", "emoji": "🕐"},
            {"value": 90, "label": "90 минут", "sub": "для опытных", "emoji": "🔥"},
        ],
    },
    "motivation_type": {
        "question": "Что тебя двигает вперёд?",
        "options": [
            {"value": "results", "label": "Вижу результат — иду дальше", "sub": "прогресс в цифрах и зеркале", "emoji": "📈"},
            {"value": "competitive", "label": "Соревновательный дух", "sub": "лучше других и лучше себя", "emoji": "🏆"},
            {"value": "health", "label": "Здоровье и энергия", "sub": "долго и качественно жить", "emoji": "❤️"},
            {"value": "stress_relief", "label": "Сброс стресса", "sub": "тренировка как терапия", "emoji": "🧘"},
        ],
    },
    "training_style": {
        "question": "Как ты предпочитаешь тренироваться?",
        "options": [
            {"value": "strict", "label": "Чёткий план", "sub": "выполняю всё строго по программе", "emoji": "📋"},
            {"value": "flexible", "label": "Гибко", "sub": "адаптирую под настроение и силы", "emoji": "🌊"},
            {"value": "variety", "label": "Люблю разнообразие", "sub": "не люблю повторяться", "emoji": "🎲"},
            {"value": "data_driven", "label": "Цифры и аналитика", "sub": "слежу за всеми метриками", "emoji": "📊"},
        ],
    },
}


class OnboardingStatusResponse(BaseModel):
    step: str
    is_complete: bool
    question: Optional[dict]
    answers: dict
    progress_pct: int


class OnboardingStepRequest(BaseModel):
    step: str
    answer: Any


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OnboardingState).where(OnboardingState.user_id == user_id)
    )
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(status_code=404, detail="Onboarding not found")

    step_index = STEPS.index(state.step) if state.step in STEPS else 0
    progress_pct = int((step_index / len(STEPS)) * 100)

    return OnboardingStatusResponse(
        step=state.step,
        is_complete=state.completed_at is not None,
        question=STEP_QUESTIONS.get(state.step),
        answers=state.answers or {},
        progress_pct=progress_pct,
    )


@router.post("/step")
async def submit_onboarding_step(
    payload: OnboardingStepRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OnboardingState).where(OnboardingState.user_id == user_id)
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=404, detail="Onboarding not started")

    if state.completed_at:
        raise HTTPException(status_code=400, detail="Onboarding already complete")

    # Consent step: requires explicit acceptance
    if payload.step == "consent":
        if payload.answer is not True and payload.answer != "accepted":
            raise HTTPException(status_code=400, detail="Consent must be accepted to proceed")
        # Record consent timestamp on the User record
        user_result = await db.execute(select(User).where(User.id == user_id))
        user_obj = user_result.scalar_one_or_none()
        if user_obj:
            user_obj.data_consent_at = datetime.utcnow()

    # Save answer
    answers = dict(state.answers or {})
    answers[payload.step] = payload.answer
    state.answers = answers

    next_step = STEP_NEXT.get(payload.step, "complete")
    # Gym users skip the inventory step (they have all equipment)
    if payload.step == "equipment" and payload.answer == "gym":
        next_step = STEP_NEXT.get("inventory", "complete")
    state.step = next_step

    if next_step == "complete":
        state.completed_at = datetime.utcnow()
        # Save to UserProfile
        await _save_profile(user_id, answers, db)
        # Generate initial plan
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one()
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one()
        generator = WorkoutGenerator(db)
        plan = await generator.generate_plan(user.id, profile)

        return {
            "status": "complete",
            "message": "Онбординг завершён! Твой план готов 💪",
            "plan_id": str(plan.id),
            "next_step": None,
        }

    return {
        "status": "continue",
        "next_step": next_step,
        "question": STEP_QUESTIONS.get(next_step),
    }


async def _save_profile(user_id: str, answers: dict, db: AsyncSession):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    profile.display_name = answers.get("name")
    profile.goal = answers.get("goal")
    profile.gender = answers.get("gender")
    profile.age = answers.get("age")
    profile.height_cm = answers.get("height")
    profile.weight_kg = answers.get("weight")
    profile.fitness_level = answers.get("fitness_level")
    location = answers.get("equipment", "gym")
    inventory = answers.get("inventory", "none")
    if location == "gym":
        profile.equipment = "gym"
    elif inventory == "barbell":
        profile.equipment = "home_barbell"
    elif inventory == "dumbbells":
        profile.equipment = "home_dumbbells"
    elif inventory == "bands":
        profile.equipment = "bands"
    else:
        profile.equipment = "bodyweight"
    injuries = answers.get("injuries", [])
    profile.injuries = [i for i in injuries if i != "none"]
    profile.medical_notes = answers.get("medical_notes")
    profile.available_days = answers.get("available_days")
    profile.session_minutes = answers.get("session_minutes")
    profile.motivation_type = answers.get("motivation_type")
    profile.training_style = answers.get("training_style")

    await db.flush()
