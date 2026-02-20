"""
Telegram Bot Application.
Handles commands, onboarding flow, daily notifications, payments.
"""
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, PreCheckoutQueryHandler,
    filters, ContextTypes
)

from app.core.config import settings
from bot.handlers import onboarding, daily, commands, payments

# Global app instance
_app: Application = None


def create_bot_app() -> Application:
    global _app
    _app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Commands
    _app.add_handler(CommandHandler("start", commands.start))
    _app.add_handler(CommandHandler("workout", commands.workout))
    _app.add_handler(CommandHandler("progress", commands.progress))
    _app.add_handler(CommandHandler("settings", commands.settings_cmd))
    _app.add_handler(CommandHandler("chat", commands.chat_cmd))
    _app.add_handler(CommandHandler("help", commands.help_cmd))
    _app.add_handler(CommandHandler("subscribe", payments.subscribe_cmd))

    # Onboarding callbacks
    _app.add_handler(CallbackQueryHandler(onboarding.handle_callback, pattern="^ob:"))

    # Payment callbacks (tier selection)
    _app.add_handler(CallbackQueryHandler(payments.handle_buy_callback, pattern="^buy:"))

    # Telegram Stars payment flow
    _app.add_handler(PreCheckoutQueryHandler(payments.pre_checkout))
    _app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, payments.successful_payment)
    )

    # General messages → AI coach
    _app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, commands.handle_message)
    )

    return _app


async def process_update(update_data: dict):
    """Process incoming Telegram update."""
    global _app
    if _app is None:
        _app = create_bot_app()
        await _app.initialize()

    update = Update.de_json(update_data, _app.bot)
    await _app.process_update(update)
