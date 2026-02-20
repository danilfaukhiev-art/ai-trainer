"""
Subscription management service.
Handles tier checks, upgrades, and access control.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionEvent
from app.db.redis import redis_client, RedisKeys

TIER_RANK = {"free": 0, "basic": 1, "pro": 2, "premium": 3}
TIER_FEATURES = {
    "free": {
        "workouts_per_week": 3,
        "ai_messages_per_day": 3,
        "nutrition_pro": False,
        "video_analysis": False,
        "progress_photos": False,
        "pdf_export": False,
    },
    "basic": {
        "workouts_per_week": 7,
        "ai_messages_per_day": 20,
        "nutrition_pro": False,
        "video_analysis": False,
        "progress_photos": True,
        "pdf_export": False,
    },
    "pro": {
        "workouts_per_week": 7,
        "ai_messages_per_day": -1,  # unlimited
        "nutrition_pro": True,
        "video_analysis": False,
        "progress_photos": True,
        "pdf_export": False,
    },
    "premium": {
        "workouts_per_week": 7,
        "ai_messages_per_day": -1,
        "nutrition_pro": True,
        "video_analysis": True,
        "progress_photos": True,
        "pdf_export": True,
    },
}


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_subscription(self, user_id: UUID) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                    (Subscription.expires_at.is_(None)) |
                    (Subscription.expires_at > datetime.utcnow()),
                )
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_tier(self, user_id: UUID) -> str:
        """Get user tier with Redis cache."""
        cache_key = RedisKeys.sub_tier(str(user_id))
        cached = await redis_client.get(cache_key)
        if cached:
            return cached

        sub = await self.get_active_subscription(user_id)
        tier = sub.tier if sub else "free"

        await redis_client.setex(cache_key, 3600, tier)  # cache 1h
        return tier

    async def has_feature(self, user_id: UUID, feature: str) -> bool:
        tier = await self.get_tier(user_id)
        return TIER_FEATURES.get(tier, {}).get(feature, False)

    async def check_tier(self, user_id: UUID, min_tier: str) -> bool:
        tier = await self.get_tier(user_id)
        return TIER_RANK.get(tier, 0) >= TIER_RANK.get(min_tier, 0)

    async def create_subscription(
        self,
        user_id: UUID,
        tier: str,
        expires_at: Optional[datetime] = None,
        payment_provider: str = "manual",
        external_id: Optional[str] = None,
    ) -> Subscription:
        # Deactivate old active subscriptions
        old_subs = await self.db.execute(
            select(Subscription).where(
                and_(Subscription.user_id == user_id, Subscription.status == "active")
            )
        )
        for old_sub in old_subs.scalars():
            old_sub.status = "cancelled"

        sub = Subscription(
            user_id=user_id,
            tier=tier,
            status="active",
            expires_at=expires_at,
            payment_provider=payment_provider,
            external_id=external_id,
        )
        self.db.add(sub)

        event = SubscriptionEvent(
            user_id=user_id,
            event_type="created",
            tier=tier,
            metadata_={"payment_provider": payment_provider},
        )
        self.db.add(event)
        await self.db.flush()

        # Invalidate cache
        await redis_client.delete(RedisKeys.sub_tier(str(user_id)))

        return sub

    async def can_send_ai_message(self, user_id: UUID) -> tuple[bool, int]:
        """Returns (can_send, remaining_today)"""
        tier = await self.get_tier(user_id)
        daily_limit = TIER_FEATURES[tier]["ai_messages_per_day"]

        if daily_limit == -1:
            return True, -1  # unlimited

        key = RedisKeys.ai_messages_count(str(user_id))
        count = await redis_client.get(key)
        count = int(count) if count else 0

        remaining = daily_limit - count
        return remaining > 0, remaining

    async def increment_ai_message_count(self, user_id: UUID):
        key = RedisKeys.ai_messages_count(str(user_id))
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400)  # TTL = 24h
        await pipe.execute()
