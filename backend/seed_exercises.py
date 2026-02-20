"""
Seed exercise library with base exercises.
Run: python scripts/seed_exercises.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.base import AsyncSessionLocal
from app.models.workout import Exercise

EXERCISES = [
    # Ноги
    {"name": "Squat", "name_ru": "Приседания со штангой", "muscle_groups": ["quads", "glutes", "hamstrings"], "equipment": ["barbell", "gym"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Goblet Squat", "name_ru": "Присед с гантелей", "muscle_groups": ["quads", "glutes"], "equipment": ["dumbbell", "home"], "difficulty": "beginner", "is_compound": True},
    {"name": "Romanian Deadlift", "name_ru": "Румынская тяга", "muscle_groups": ["hamstrings", "glutes", "back"], "equipment": ["barbell", "dumbbell"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Lunge", "name_ru": "Выпады", "muscle_groups": ["quads", "glutes"], "equipment": ["bodyweight", "dumbbell"], "difficulty": "beginner", "is_compound": False},
    {"name": "Leg Press", "name_ru": "Жим ногами", "muscle_groups": ["quads", "glutes"], "equipment": ["machine", "gym"], "difficulty": "beginner", "is_compound": False},
    {"name": "Calf Raise", "name_ru": "Подъём на носки", "muscle_groups": ["calves"], "equipment": ["bodyweight", "gym"], "difficulty": "beginner", "is_compound": False},
    # Грудь
    {"name": "Bench Press", "name_ru": "Жим лёжа", "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": ["barbell", "gym"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Push-up", "name_ru": "Отжимания", "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": ["bodyweight"], "difficulty": "beginner", "is_compound": True},
    {"name": "Dumbbell Fly", "name_ru": "Разводка гантелей", "muscle_groups": ["chest"], "equipment": ["dumbbell"], "difficulty": "beginner", "is_compound": False},
    {"name": "Incline Bench Press", "name_ru": "Жим под углом", "muscle_groups": ["upper_chest", "triceps"], "equipment": ["barbell", "dumbbell", "gym"], "difficulty": "intermediate", "is_compound": True},
    # Спина
    {"name": "Pull-up", "name_ru": "Подтягивания", "muscle_groups": ["lats", "biceps"], "equipment": ["bodyweight", "bar"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Bent Over Row", "name_ru": "Тяга штанги в наклоне", "muscle_groups": ["back", "biceps"], "equipment": ["barbell"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Lat Pulldown", "name_ru": "Тяга верхнего блока", "muscle_groups": ["lats", "biceps"], "equipment": ["cable", "gym"], "difficulty": "beginner", "is_compound": True},
    {"name": "Seated Cable Row", "name_ru": "Тяга нижнего блока", "muscle_groups": ["back", "biceps"], "equipment": ["cable", "gym"], "difficulty": "beginner", "is_compound": True},
    # Плечи
    {"name": "Overhead Press", "name_ru": "Жим над головой", "muscle_groups": ["shoulders", "triceps"], "equipment": ["barbell", "dumbbell"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Lateral Raise", "name_ru": "Боковые подъёмы", "muscle_groups": ["shoulders"], "equipment": ["dumbbell"], "difficulty": "beginner", "is_compound": False},
    # Бицепс/трицепс
    {"name": "Bicep Curl", "name_ru": "Сгибание на бицепс", "muscle_groups": ["biceps"], "equipment": ["dumbbell", "barbell"], "difficulty": "beginner", "is_compound": False},
    {"name": "Tricep Dip", "name_ru": "Отжимания на брусьях", "muscle_groups": ["triceps", "chest"], "equipment": ["bodyweight", "parallel_bars"], "difficulty": "intermediate", "is_compound": True},
    {"name": "Tricep Pushdown", "name_ru": "Разгибание на блоке", "muscle_groups": ["triceps"], "equipment": ["cable", "gym"], "difficulty": "beginner", "is_compound": False},
    # Кор
    {"name": "Plank", "name_ru": "Планка", "muscle_groups": ["core"], "equipment": ["bodyweight"], "difficulty": "beginner", "is_compound": False},
    {"name": "Crunch", "name_ru": "Скручивания", "muscle_groups": ["core"], "equipment": ["bodyweight"], "difficulty": "beginner", "is_compound": False},
    {"name": "Dead Bug", "name_ru": "Мёртвый жук", "muscle_groups": ["core"], "equipment": ["bodyweight"], "difficulty": "beginner", "is_compound": False},
]


async def seed():
    async with AsyncSessionLocal() as db:
        for ex_data in EXERCISES:
            ex = Exercise(**ex_data)
            db.add(ex)
        await db.commit()
        print(f"✅ Seeded {len(EXERCISES)} exercises")


if __name__ == "__main__":
    asyncio.run(seed())
