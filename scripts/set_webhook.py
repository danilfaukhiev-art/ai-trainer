"""
Set Telegram bot webhook URL.
Run once after deployment: python scripts/set_webhook.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from telegram import Bot
from app.core.config import settings


async def set_webhook():
    bot = Bot(token=settings.telegram_bot_token)

    webhook_url = f"{settings.telegram_webhook_url}"
    print(f"Setting webhook to: {webhook_url}")

    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
    )

    info = await bot.get_webhook_info()
    print(f"✅ Webhook set: {info.url}")
    print(f"   Pending updates: {info.pending_update_count}")
    if info.last_error_message:
        print(f"   Last error: {info.last_error_message}")


if __name__ == "__main__":
    asyncio.run(set_webhook())
