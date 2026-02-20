import base64
import json
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from openai import AsyncOpenAI

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.core.config import settings
from app.models.nutrition import MealEntry, WaterLog

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


class MealCreate(BaseModel):
    meal_date: date
    meal_type: str  # breakfast | lunch | dinner | snack
    name: str
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    fats_g: Optional[float] = None
    carbs_g: Optional[float] = None
    portion_g: Optional[int] = None
    notes: Optional[str] = None


class WaterCreate(BaseModel):
    log_date: date
    amount_ml: int


@router.get("")
async def get_daily_nutrition(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    target_date: Optional[str] = None,
):
    d = date.fromisoformat(target_date) if target_date else date.today()

    # Get meals
    result = await db.execute(
        select(MealEntry)
        .where(and_(MealEntry.user_id == user_id, MealEntry.meal_date == d))
        .order_by(MealEntry.created_at)
    )
    meals = result.scalars().all()

    # Get water
    water_result = await db.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0))
        .where(and_(WaterLog.user_id == user_id, WaterLog.log_date == d))
    )
    water_ml = water_result.scalar()

    # Group meals by type
    grouped: dict = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
    totals = {"calories": 0, "protein_g": 0, "fats_g": 0, "carbs_g": 0}

    for meal in meals:
        entry = {
            "id": str(meal.id),
            "name": meal.name,
            "calories": meal.calories,
            "protein_g": float(meal.protein_g) if meal.protein_g else None,
            "fats_g": float(meal.fats_g) if meal.fats_g else None,
            "carbs_g": float(meal.carbs_g) if meal.carbs_g else None,
            "portion_g": meal.portion_g,
            "notes": meal.notes,
        }
        if meal.meal_type in grouped:
            grouped[meal.meal_type].append(entry)
        if meal.calories:
            totals["calories"] += meal.calories
        if meal.protein_g:
            totals["protein_g"] += float(meal.protein_g)
        if meal.fats_g:
            totals["fats_g"] += float(meal.fats_g)
        if meal.carbs_g:
            totals["carbs_g"] += float(meal.carbs_g)

    return {
        "date": d.isoformat(),
        "meals": grouped,
        "totals": {
            "calories": totals["calories"],
            "protein_g": round(totals["protein_g"], 1),
            "fats_g": round(totals["fats_g"], 1),
            "carbs_g": round(totals["carbs_g"], 1),
        },
        "water_ml": water_ml,
    }


@router.post("/meal")
async def add_meal(
    payload: MealCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meal = MealEntry(
        user_id=user_id,
        **payload.model_dump(),
    )
    db.add(meal)
    await db.flush()
    return {
        "id": str(meal.id),
        "name": meal.name,
        "meal_type": meal.meal_type,
        "calories": meal.calories,
    }


@router.delete("/meal/{meal_id}")
async def delete_meal(
    meal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MealEntry).where(
            and_(MealEntry.id == meal_id, MealEntry.user_id == user_id)
        )
    )
    meal = result.scalar_one_or_none()
    if meal:
        await db.delete(meal)
    return {"status": "deleted"}


@router.post("/analyze-photo")
async def analyze_food_photo(
    user_id: str = Depends(get_current_user_id),
    file: UploadFile = File(...),
):
    """Analyze food photo with GPT-4o Vision and return estimated macros."""
    image_bytes = await file.read()
    b64 = base64.b64encode(image_bytes).decode()
    mime = file.content_type or "image/jpeg"

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        'Определи блюдо на фото и оцени его пищевую ценность. '
                        'Верни ТОЛЬКО JSON без пояснений: '
                        '{"name": "Название блюда на русском", "calories": 350, '
                        '"protein_g": 25, "fats_g": 10, "carbs_g": 40, "portion_g": 300, '
                        '"description": "Краткое описание"} '
                        'Числа — целые. Если не можешь определить значение — укажи null.'
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"},
                },
            ],
        }],
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    return json.loads(response.choices[0].message.content)


@router.get("/search")
async def search_food(
    q: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Search common Russian foods with approximate macros per 100g.
    Returns top matches — no external API needed.
    """
    query = q.strip().lower()
    results = [item for item in _FOOD_DB if query in item["name"].lower()][:10]
    return {"results": results}


# ── Inline food database (per 100g) ──────────────────────────────────────────
_FOOD_DB = [
    {"name": "Гречка варёная", "calories": 92, "protein_g": 3.4, "fats_g": 0.6, "carbs_g": 20},
    {"name": "Гречка сухая", "calories": 308, "protein_g": 12.6, "fats_g": 3.3, "carbs_g": 57},
    {"name": "Рис белый варёный", "calories": 116, "protein_g": 2.7, "fats_g": 0.3, "carbs_g": 25},
    {"name": "Рис бурый варёный", "calories": 111, "protein_g": 2.6, "fats_g": 0.9, "carbs_g": 23},
    {"name": "Овсянка варёная", "calories": 68, "protein_g": 2.4, "fats_g": 1.4, "carbs_g": 12},
    {"name": "Овсянка сухая", "calories": 342, "protein_g": 12, "fats_g": 6, "carbs_g": 60},
    {"name": "Макароны варёные", "calories": 112, "protein_g": 3.8, "fats_g": 0.5, "carbs_g": 23},
    {"name": "Картофель варёный", "calories": 77, "protein_g": 2, "fats_g": 0.1, "carbs_g": 16},
    {"name": "Картофель запечённый", "calories": 93, "protein_g": 2.5, "fats_g": 0.1, "carbs_g": 21},
    {"name": "Куриная грудка варёная", "calories": 137, "protein_g": 26, "fats_g": 3, "carbs_g": 0},
    {"name": "Куриная грудка жареная", "calories": 165, "protein_g": 25, "fats_g": 7, "carbs_g": 0},
    {"name": "Куриное бедро варёное", "calories": 185, "protein_g": 22, "fats_g": 11, "carbs_g": 0},
    {"name": "Куриное яйцо", "calories": 155, "protein_g": 13, "fats_g": 11, "carbs_g": 1},
    {"name": "Яичный белок", "calories": 52, "protein_g": 11, "fats_g": 0.2, "carbs_g": 0.7},
    {"name": "Говядина варёная", "calories": 218, "protein_g": 25, "fats_g": 13, "carbs_g": 0},
    {"name": "Говядина жареная", "calories": 267, "protein_g": 27, "fats_g": 17, "carbs_g": 0},
    {"name": "Свинина варёная", "calories": 259, "protein_g": 22, "fats_g": 18, "carbs_g": 0},
    {"name": "Лосось запечённый", "calories": 206, "protein_g": 27, "fats_g": 11, "carbs_g": 0},
    {"name": "Тунец консервированный", "calories": 96, "protein_g": 22, "fats_g": 1, "carbs_g": 0},
    {"name": "Творог 0%", "calories": 71, "protein_g": 16, "fats_g": 0.1, "carbs_g": 1.8},
    {"name": "Творог 5%", "calories": 121, "protein_g": 17, "fats_g": 5, "carbs_g": 1.8},
    {"name": "Творог 9%", "calories": 159, "protein_g": 16, "fats_g": 9, "carbs_g": 2},
    {"name": "Молоко 2.5%", "calories": 52, "protein_g": 2.8, "fats_g": 2.5, "carbs_g": 4.7},
    {"name": "Кефир 1%", "calories": 40, "protein_g": 3, "fats_g": 1, "carbs_g": 4},
    {"name": "Греческий йогурт 0%", "calories": 59, "protein_g": 10, "fats_g": 0.4, "carbs_g": 3.6},
    {"name": "Сыр российский", "calories": 364, "protein_g": 24, "fats_g": 30, "carbs_g": 0},
    {"name": "Протеин сывороточный", "calories": 380, "protein_g": 75, "fats_g": 5, "carbs_g": 10},
    {"name": "Банан", "calories": 89, "protein_g": 1.1, "fats_g": 0.3, "carbs_g": 23},
    {"name": "Яблоко", "calories": 52, "protein_g": 0.3, "fats_g": 0.2, "carbs_g": 14},
    {"name": "Апельсин", "calories": 47, "protein_g": 0.9, "fats_g": 0.1, "carbs_g": 12},
    {"name": "Виноград", "calories": 67, "protein_g": 0.6, "fats_g": 0.4, "carbs_g": 17},
    {"name": "Клубника", "calories": 32, "protein_g": 0.7, "fats_g": 0.3, "carbs_g": 8},
    {"name": "Авокадо", "calories": 160, "protein_g": 2, "fats_g": 15, "carbs_g": 9},
    {"name": "Огурец", "calories": 15, "protein_g": 0.7, "fats_g": 0.1, "carbs_g": 3},
    {"name": "Помидор", "calories": 18, "protein_g": 0.9, "fats_g": 0.2, "carbs_g": 3.9},
    {"name": "Брокколи варёная", "calories": 35, "protein_g": 2.4, "fats_g": 0.3, "carbs_g": 7},
    {"name": "Шпинат", "calories": 23, "protein_g": 2.9, "fats_g": 0.4, "carbs_g": 3.6},
    {"name": "Миндаль", "calories": 579, "protein_g": 21, "fats_g": 50, "carbs_g": 22},
    {"name": "Грецкий орех", "calories": 654, "protein_g": 15, "fats_g": 65, "carbs_g": 14},
    {"name": "Арахисовое масло", "calories": 588, "protein_g": 25, "fats_g": 50, "carbs_g": 20},
    {"name": "Оливковое масло", "calories": 884, "protein_g": 0, "fats_g": 100, "carbs_g": 0},
    {"name": "Хлеб ржаной", "calories": 259, "protein_g": 6.6, "fats_g": 1.2, "carbs_g": 54},
    {"name": "Хлеб белый", "calories": 265, "protein_g": 9, "fats_g": 3, "carbs_g": 49},
    {"name": "Борщ", "calories": 50, "protein_g": 2.5, "fats_g": 1.5, "carbs_g": 7},
    {"name": "Пельмени варёные", "calories": 245, "protein_g": 12, "fats_g": 12, "carbs_g": 23},
    {"name": "Омлет из 2 яиц", "calories": 154, "protein_g": 11, "fats_g": 12, "carbs_g": 1},
    {"name": "Гречка с курицей", "calories": 112, "protein_g": 14, "fats_g": 2, "carbs_g": 11},
    {"name": "Рис с овощами", "calories": 110, "protein_g": 3, "fats_g": 2, "carbs_g": 22},
    {"name": "Салат с тунцом", "calories": 95, "protein_g": 14, "fats_g": 3, "carbs_g": 4},
]


@router.post("/water")
async def add_water(
    payload: WaterCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    log = WaterLog(
        user_id=user_id,
        log_date=payload.log_date,
        amount_ml=payload.amount_ml,
    )
    db.add(log)
    await db.flush()

    # Return total for the day
    total_result = await db.execute(
        select(func.coalesce(func.sum(WaterLog.amount_ml), 0))
        .where(and_(WaterLog.user_id == user_id, WaterLog.log_date == payload.log_date))
    )
    total = total_result.scalar()

    return {"water_ml": total}
