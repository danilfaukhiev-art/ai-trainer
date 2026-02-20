"""
Subscription management routes.
Handles tier info and activation from Telegram Stars payments.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.core.config import settings
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionEvent
from app.services.subscription_service import TIER_FEATURES, TIER_RANK

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Prices in Telegram Stars
TIER_PRICES = {
    "basic": {"stars": 99, "days": 30},
    "pro": {"stars": 299, "days": 30},
    "premium": {"stars": 599, "days": 30},
}


class ActivateRequest(BaseModel):
    tier: str
    payment_provider: str = "telegram_stars"
    external_id: Optional[str] = None  # Telegram payment charge_id


class BotActivateRequest(BaseModel):
    telegram_id: int
    tier: str
    payment_provider: str = "telegram_stars"
    external_id: Optional[str] = None
    bot_secret: str  # must match settings.telegram_bot_token


@router.get("/info")
async def get_subscription_info(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return current subscription + available tiers with features."""
    result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
        ).order_by(Subscription.created_at.desc())
    )
    sub = result.scalar_one_or_none()
    current_tier = sub.tier if sub else "free"
    expires_at = sub.expires_at.isoformat() if sub and sub.expires_at else None

    tiers = []
    for tier_name, price in TIER_PRICES.items():
        features = TIER_FEATURES.get(tier_name, {})
        tiers.append({
            "tier": tier_name,
            "stars": price["stars"],
            "days": price["days"],
            "is_current": current_tier == tier_name,
            "is_upgrade": TIER_RANK.get(tier_name, 0) > TIER_RANK.get(current_tier, 0),
            "features": features,
        })

    return {
        "current_tier": current_tier,
        "expires_at": expires_at,
        "tiers": tiers,
        "features": TIER_FEATURES.get(current_tier, TIER_FEATURES["free"]),
    }


@router.post("/activate")
async def activate_subscription(
    payload: ActivateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a subscription tier.
    Called by the bot after a successful Telegram Stars payment.
    """
    if payload.tier not in TIER_PRICES and payload.tier not in ("free",):
        raise HTTPException(status_code=400, detail=f"Unknown tier: {payload.tier}")

    # Deactivate current subscriptions
    existing = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
        )
    )
    for s in existing.scalars():
        s.status = "cancelled"

    days = TIER_PRICES.get(payload.tier, {}).get("days", 30)
    new_sub = Subscription(
        user_id=UUID(user_id),
        tier=payload.tier,
        status="active",
        payment_provider=payload.payment_provider,
        external_id=payload.external_id,
        expires_at=datetime.utcnow() + timedelta(days=days),
    )
    db.add(new_sub)

    event = SubscriptionEvent(
        user_id=UUID(user_id),
        event_type="created",
        tier=payload.tier,
        metadata_={"provider": payload.payment_provider, "external_id": payload.external_id},
    )
    db.add(event)
    await db.flush()

    return {
        "status": "activated",
        "tier": payload.tier,
        "expires_at": new_sub.expires_at.isoformat(),
    }


@router.post("/activate-by-telegram")
async def activate_by_telegram(
    payload: BotActivateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint — called by the bot after successful Stars payment.
    Authenticates via bot_secret instead of JWT.
    """
    if payload.bot_secret != settings.telegram_bot_token:
        raise HTTPException(status_code=403, detail="Invalid bot secret")

    if payload.tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {payload.tier}")

    # Find user by telegram_id
    user_result = await db.execute(
        select(User).where(User.telegram_id == payload.telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id

    # Deactivate existing subscriptions
    existing = await db.execute(
        select(Subscription).where(
            and_(Subscription.user_id == user_id, Subscription.status == "active")
        )
    )
    for s in existing.scalars():
        s.status = "cancelled"

    days = TIER_PRICES[payload.tier]["days"]
    new_sub = Subscription(
        user_id=user_id,
        tier=payload.tier,
        status="active",
        payment_provider=payload.payment_provider,
        external_id=payload.external_id,
        expires_at=datetime.utcnow() + timedelta(days=days),
    )
    db.add(new_sub)

    event = SubscriptionEvent(
        user_id=user_id,
        event_type="created",
        tier=payload.tier,
        metadata_={"provider": payload.payment_provider, "telegram_charge_id": payload.external_id},
    )
    db.add(event)
    await db.flush()

    return {"status": "activated", "tier": payload.tier}
