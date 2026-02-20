from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.progress import ProgressEntry, ProgressPhoto, UserStreak

router = APIRouter(prefix="/progress", tags=["progress"])


class ProgressEntryCreate(BaseModel):
    recorded_date: date
    weight_kg: Optional[float] = None
    body_fat_pct: Optional[float] = None
    chest_cm: Optional[int] = None
    waist_cm: Optional[int] = None
    hips_cm: Optional[int] = None
    bicep_cm: Optional[int] = None
    forearm_cm: Optional[int] = None
    thigh_cm: Optional[int] = None
    calf_cm: Optional[int] = None
    notes: Optional[str] = None


@router.get("")
async def get_progress(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
):
    result = await db.execute(
        select(ProgressEntry)
        .where(ProgressEntry.user_id == user_id)
        .order_by(desc(ProgressEntry.recorded_date))
        .limit(limit)
    )
    entries = result.scalars().all()

    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = streak_result.scalar_one_or_none()

    return {
        "entries": [_format_entry(e) for e in entries],
        "streak": {
            "current": streak.current_streak if streak else 0,
            "max": streak.max_streak if streak else 0,
            "last_activity": streak.last_activity.isoformat() if streak and streak.last_activity else None,
        },
    }


@router.post("")
async def add_progress_entry(
    payload: ProgressEntryCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    entry = ProgressEntry(
        user_id=user_id,
        **payload.model_dump(),
    )
    db.add(entry)
    await db.flush()
    return _format_entry(entry)


@router.post("/photos")
async def upload_progress_photo(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    photo_type: str = Form("front"),
    taken_date: Optional[str] = Form(None),
):
    from app.services.storage import StorageService

    storage = StorageService()
    storage_key = await storage.upload_progress_photo(
        user_id=user_id,
        file=file,
        photo_type=photo_type,
    )

    photo = ProgressPhoto(
        user_id=user_id,
        storage_key=storage_key,
        taken_date=date.fromisoformat(taken_date) if taken_date else date.today(),
        type=photo_type,
    )
    db.add(photo)
    await db.flush()

    return {
        "id": str(photo.id),
        "url": await storage.get_presigned_url(storage_key),
        "type": photo_type,
    }


def _format_entry(entry: ProgressEntry) -> dict:
    return {
        "id": str(entry.id),
        "recorded_date": entry.recorded_date.isoformat(),
        "weight_kg": float(entry.weight_kg) if entry.weight_kg else None,
        "body_fat_pct": float(entry.body_fat_pct) if entry.body_fat_pct else None,
        "chest_cm": entry.chest_cm,
        "waist_cm": entry.waist_cm,
        "hips_cm": entry.hips_cm,
        "bicep_cm": entry.bicep_cm,
        "forearm_cm": entry.forearm_cm,
        "thigh_cm": entry.thigh_cm,
        "calf_cm": entry.calf_cm,
        "notes": entry.notes,
    }
