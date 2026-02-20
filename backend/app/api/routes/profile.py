from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.user import User, UserProfile
from app.services.subscription_service import SubscriptionService
from uuid import UUID

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    display_name: Optional[str]
    telegram_username: Optional[str]
    goal: Optional[str]
    gender: Optional[str]
    age: Optional[int]
    height_cm: Optional[int]
    weight_kg: Optional[float]
    fitness_level: Optional[str]
    equipment: Optional[str]
    injuries: Optional[list]
    medical_notes: Optional[str]
    available_days: Optional[int]
    session_minutes: Optional[int]
    subscription_tier: str


class ProfileUpdateRequest(BaseModel):
    weight_kg: Optional[float] = None
    available_days: Optional[int] = None
    session_minutes: Optional[int] = None
    goal: Optional[str] = None


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    sub_service = SubscriptionService(db)
    tier = await sub_service.get_tier(UUID(user_id))

    return ProfileResponse(
        display_name=profile.display_name if profile else None,
        telegram_username=user.telegram_username,
        goal=profile.goal if profile else None,
        gender=profile.gender if profile else None,
        age=profile.age if profile else None,
        height_cm=profile.height_cm if profile else None,
        weight_kg=profile.weight_kg if profile else None,
        fitness_level=profile.fitness_level if profile else None,
        equipment=profile.equipment if profile else None,
        injuries=profile.injuries if profile else [],
        medical_notes=profile.medical_notes if profile else None,
        available_days=profile.available_days if profile else None,
        session_minutes=profile.session_minutes if profile else None,
        subscription_tier=tier,
    )


@router.put("")
async def update_profile(
    payload: ProfileUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if payload.weight_kg is not None:
        profile.weight_kg = payload.weight_kg
    if payload.available_days is not None:
        profile.available_days = payload.available_days
    if payload.session_minutes is not None:
        profile.session_minutes = payload.session_minutes
    if payload.goal is not None:
        profile.goal = payload.goal

    await db.commit()
    return {"status": "updated"}


@router.delete("/account")
async def delete_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.deleted_at = datetime.utcnow()
    await db.commit()
    return {"status": "deleted"}
