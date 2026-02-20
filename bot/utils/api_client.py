"""
Internal API client for Bot → Backend communication.
Bot calls the FastAPI backend internally (same process or HTTP).
"""
import httpx
from app.core.config import settings
from app.core.auth import create_access_token

BASE_URL = f"http://localhost:{settings.app_port}/api"


async def _get_bot_token(user_id: str, telegram_id: int) -> str:
    """Generate an internal JWT for bot-originated requests."""
    return create_access_token(user_id=str(user_id), telegram_id=telegram_id)


async def internal_api_chat(user_id, telegram_id: int, message: str) -> str:
    """Send chat message through internal API and return AI reply."""
    token = await _get_bot_token(str(user_id), telegram_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/ai/chat",
                json={"message": message},
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return response.json()["reply"]
            elif response.status_code == 402:
                detail = response.json().get("detail", {})
                return detail.get(
                    "message",
                    "Лимит сообщений исчерпан. Обнови подписку для безлимитного общения."
                )
            else:
                return "Что-то пошло не так. Попробуй позже."
        except Exception as e:
            return "Не удалось связаться с тренером. Попробуй позже."
