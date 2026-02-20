"""
Fetches exercise GIF URLs and step-by-step instructions from free ExerciseDB API.
Caches results in-memory to avoid redundant requests.
"""
import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# In-memory cache: english_name → {"gif_url": str, "instructions": list[str]}
_cache: dict[str, dict] = {}

EXERCISEDB_SEARCH_URL = "https://exercisedb-api.vercel.app/api/v1/exercises/search"


async def fetch_exercise_data(name_en: str) -> dict:
    """
    Fetch GIF URL + instructions for an exercise from ExerciseDB free API.
    Returns {"gif_url": str|None, "instructions": list[str]}.
    """
    if not name_en:
        return {"gif_url": None, "instructions": []}

    key = name_en.lower().strip()
    if key in _cache:
        return _cache[key]

    result = {"gif_url": None, "instructions": []}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                EXERCISEDB_SEARCH_URL,
                params={"q": key, "limit": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                exercises = data.get("data", [])
                if exercises:
                    ex = exercises[0]
                    result["gif_url"] = ex.get("gifUrl") or ex.get("gif_url")
                    instructions = ex.get("instructions", [])
                    # Clean up "Step:N " prefix if present
                    cleaned = []
                    for step in instructions:
                        if isinstance(step, str):
                            text = step
                            if text.startswith("Step:"):
                                parts = text.split(" ", 1)
                                text = parts[1] if len(parts) > 1 else text
                            cleaned.append(text)
                    result["instructions"] = cleaned
    except Exception as exc:
        logger.debug("ExerciseDB fetch failed for %r: %s", name_en, exc)

    _cache[key] = result
    return result


async def fetch_gif_url(name_en: str) -> Optional[str]:
    """Backward-compat: fetch just the GIF URL."""
    data = await fetch_exercise_data(name_en)
    return data["gif_url"]


async def fetch_exercise_data_bulk(names_en: list[str]) -> dict[str, dict]:
    """Fetch data for multiple exercises concurrently."""
    tasks = [fetch_exercise_data(n) for n in names_en]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        name: (r if not isinstance(r, Exception) else {"gif_url": None, "instructions": []})
        for name, r in zip(names_en, results)
    }


async def fetch_gif_urls_bulk(names_en: list[str]) -> dict[str, Optional[str]]:
    """Backward-compat: fetch just GIF URLs in bulk."""
    data = await fetch_exercise_data_bulk(names_en)
    return {name: d["gif_url"] for name, d in data.items()}
