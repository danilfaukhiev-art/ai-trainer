"""
Telegram Stars payment handler.
Handles /subscribe command, pre-checkout, and successful payment.
"""
import logging
import httpx

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.core.config import settings

logger = logging.getLogger(__name__)

BACKEND_URL = settings.telegram_webhook_url.replace("/webhook/telegram", "")

TIERS = {
    "basic": {
        "title": "Basic — 99 Stars/мес",
        "description": "7 тренировок/нед · 20 AI-сообщений/день · Фото прогресса",
        "stars": 99,
        "emoji": "⭐",
        "features": [
            "✅ 7 тренировок в неделю",
            "✅ 20 AI-сообщений в день",
            "✅ Фото прогресса",
            "❌ Питание Pro",
            "❌ Видео-анализ",
        ],
    },
    "pro": {
        "title": "Pro — 299 Stars/мес",
        "description": "Безлимит AI · Питание Pro · Все возможности тренировок",
        "stars": 299,
        "emoji": "🚀",
        "features": [
            "✅ 7 тренировок в неделю",
            "✅ Безлимитный AI-чат",
            "✅ Фото прогресса",
            "✅ Питание Pro",
            "❌ Видео-анализ",
        ],
    },
    "premium": {
        "title": "Premium — 599 Stars/мес",
        "description": "Всё включено: AI без лимитов, видео-анализ техники, PDF-экспорт",
        "stars": 599,
        "emoji": "💎",
        "features": [
            "✅ 7 тренировок в неделю",
            "✅ Безлимитный AI-чат",
            "✅ Фото прогресса",
            "✅ Питание Pro",
            "✅ Видео-анализ техники",
            "✅ PDF-экспорт отчётов",
        ],
    },
}


async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available subscription tiers."""
    keyboard = []
    text_lines = ["💳 *Выбери тариф:*\n"]

    for tier_key, tier in TIERS.items():
        features_text = "\n".join(tier["features"])
        text_lines.append(f"{tier['emoji']} *{tier['title']}*\n{features_text}\n")
        keyboard.append([
            InlineKeyboardButton(
                f"{tier['emoji']} Купить {tier['title']}",
                callback_data=f"buy:{tier_key}",
            )
        ])

    await update.message.reply_text(
        "\n".join(text_lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invoice when user taps a tier button."""
    query = update.callback_query
    await query.answer()

    tier_key = query.data.split(":")[1]
    tier = TIERS.get(tier_key)
    if not tier:
        return

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=tier["title"],
        description=tier["description"],
        payload=f"sub:{tier_key}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=tier["title"], amount=tier["stars"])],
        provider_token="",  # Empty string for Stars
    )


async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm payment before processing."""
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("sub:"):
        await query.answer(ok=False, error_message="Неизвестный платёж")
        return
    await query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate subscription after Stars payment."""
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # e.g. "sub:pro"

    if not payload.startswith("sub:"):
        return

    tier_key = payload.split(":")[1]
    tier = TIERS.get(tier_key)
    if not tier:
        return

    charge_id = payment.telegram_payment_charge_id
    user_tg_id = update.message.from_user.id

    # Activate via backend API — use bot token as internal auth
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/subscriptions/activate-by-telegram",
                json={
                    "telegram_id": user_tg_id,
                    "tier": tier_key,
                    "payment_provider": "telegram_stars",
                    "external_id": charge_id,
                    "bot_secret": settings.telegram_bot_token,
                },
            )
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to activate subscription for {user_tg_id}: {e}")
        await update.message.reply_text(
            "Оплата прошла, но возникла ошибка активации. Напиши в поддержку.",
        )
        return

    await update.message.reply_text(
        f"🎉 *{tier['emoji']} {tier['title'].split(' —')[0]} активирован!*\n\n"
        f"Добро пожаловать в новый уровень тренировок!\n"
        f"Все функции уже доступны в приложении.",
        parse_mode=ParseMode.MARKDOWN,
    )
