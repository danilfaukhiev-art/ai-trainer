"""
Fetch GIF URLs for exercises from ExerciseDB.dev (free, no API key needed).
API docs: https://v1.exercisedb.dev/docs

Usage:
    python scripts/fetch_exercise_gifs.py
"""
import asyncio
import os
import sys
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select, update
from app.db.base import AsyncSessionLocal
from app.models.workout import Exercise

EXERCISEDB_BASE = "https://exercisedb.dev/api/v1"

# Search term overrides: our Exercise.name -> API search term
NAME_OVERRIDES: dict[str, str] = {
    "Romanian Deadlift": "romanian deadlift",
    "Bent Over Row": "bent over row",
    "Lat Pulldown": "lat pulldown",
    "Seated Cable Row": "cable seated row",
    "Overhead Press": "overhead press",
    "Lateral Raise": "lateral raise",
    "Bicep Curl": "bicep curl",
    "Tricep Dip": "dips",
    "Tricep Pushdown": "cable pushdown",
    "Dead Bug": "dead bug",
    "Goblet Squat": "goblet squat",
    "Incline Bench Press": "incline bench press",
    "Dumbbell Fly": "dumbbell fly",
    "Calf Raise": "calf raise",
    "Leg Press": "leg press",
    "Pull-up": "pull up",
    "Push-up": "push up",
    "Bench Press": "bench press",
    "Squat": "barbell squat",
    "Lunge": "lunge",
    "Plank": "plank",
    "Crunch": "crunch",
}


async def search_exercise(client: httpx.AsyncClient, name: str) -> str | None:
    """Search exercisedb.dev by name, return gifUrl of best match."""
    search_term = NAME_OVERRIDES.get(name, name.lower())
    try:
        resp = await client.get(
            f"{EXERCISEDB_BASE}/exercises/search",
            params={"q": search_term, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        exercises = data.get("data", [])
        if exercises:
            return exercises[0].get("gifUrl")
    except Exception as e:
        print(f"  ⚠️  Error fetching '{name}': {e}")
    return None


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Exercise))
        exercises = result.scalars().all()

        print(f"🏋️  Found {len(exercises)} exercises. Fetching GIFs...\n")

        async with httpx.AsyncClient() as client:
            for ex in exercises:
                if ex.gif_url:
                    print(f"  ✅ {ex.name} — already has GIF, skipping")
                    continue

                gif_url = await search_exercise(client, ex.name)
                if gif_url:
                    await db.execute(
                        update(Exercise)
                        .where(Exercise.id == ex.id)
                        .values(gif_url=gif_url)
                    )
                    print(f"  ✅ {ex.name} → {gif_url}")
                else:
                    print(f"  ❌ {ex.name} — not found")

                await asyncio.sleep(1.5)

        await db.commit()
        print("\n✅ Done! GIF URLs saved to database.")


if __name__ == "__main__":
    asyncio.run(main())
