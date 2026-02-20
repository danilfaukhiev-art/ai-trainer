from redis.asyncio import Redis, from_url
from app.core.config import settings

redis_client: Redis = from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> Redis:
    return redis_client


class RedisKeys:
    @staticmethod
    def user_state(telegram_id: int) -> str:
        return f"user:{telegram_id}:state"

    @staticmethod
    def onboarding(telegram_id: int) -> str:
        return f"user:{telegram_id}:onboarding"

    @staticmethod
    def today_workout(user_id: str) -> str:
        return f"user:{user_id}:today_workout"

    @staticmethod
    def ai_context(user_id: str) -> str:
        return f"user:{user_id}:ai_context"

    @staticmethod
    def sub_tier(user_id: str) -> str:
        return f"sub:{user_id}:tier"

    @staticmethod
    def ai_messages_count(user_id: str) -> str:
        from datetime import date
        return f"ai_msg:{user_id}:{date.today().isoformat()}"

    @staticmethod
    def video_job(job_id: str) -> str:
        return f"video_job:{job_id}"
