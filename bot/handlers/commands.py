"""Core bot command handlers."""
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.core.config import settings
from bot.utils.db_helpers import get_or_create_user, get_user_profile, get_today_workout
from bot.keyboards.main_kb import main_keyboard, open_app_button

MINIAPP_URL = settings.telegram_webhook_url.replace("/webhook/telegram", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — onboarding or main menu."""
    tg_user = update.effective_user
    user, is_new = await get_or_create_user(tg_user)

    if is_new:
        await update.message.reply_text(
            f"👋 Привет, {tg_user.first_name}!\n\n"
            "Я *Константин* — твой AI-тренер.\n"
            "Помогу составить план тренировок, следить за прогрессом "
            "и не потерять мотивацию 💪\n\n"
            "Давай начнём с короткой настройки — займёт 2 минуты.\n\n"
            "⚠️ _Приложение предоставляет общие рекомендации и не является "
            "медицинской консультацией. Перед началом тренировок проконсультируйтесь с врачом._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🚀 Начать настройку",
                    web_app=WebAppInfo(url=f"{MINIAPP_URL}/onboarding")
                )],
            ]),
        )
    else:
        profile = await get_user_profile(user.id)
        if not profile:
            await update.message.reply_text(
                "Завершим настройку профиля?",
                reply_markup=open_app_button("/onboarding"),
            )
            return

        await update.message.reply_text(
            f"С возвращением, {tg_user.first_name}! 💪\n\n"
            "Просто напиши мне что угодно — я твой AI-тренер 🤖",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard(MINIAPP_URL),
        )


async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's workout."""
    tg_user = update.effective_user
    user, _ = await get_or_create_user(tg_user)
    today_workout = await get_today_workout(user.id)

    if not today_workout:
        await update.message.reply_text(
            "🛋️ Сегодня день отдыха! Восстановление — тоже часть тренировки.",
            reply_markup=open_app_button("/"),
        )
        return

    exercises = today_workout.get("exercises", [])
    ex_text = "\n".join(
        f"• {ex['name']} — {ex['sets']}×{ex['reps']} "
        f"({'отдых ' + str(ex['rest_sec']) + 'с' if ex.get('rest_sec') else ''})"
        for ex in exercises[:5]
    )
    if len(exercises) > 5:
        ex_text += f"\n  _...и ещё {len(exercises) - 5} упражнений_"

    await update.message.reply_text(
        f"💪 *Тренировка на сегодня*\n\n{ex_text}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📱 Открыть полную тренировку",
                web_app=WebAppInfo(url=f"{MINIAPP_URL}/workout/{today_workout['id']}")
            )],
        ]),
    )


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Отслеживай свой прогресс в приложении:",
        reply_markup=open_app_button("/progress"),
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ Настройки профиля:",
        reply_markup=open_app_button("/settings"),
    )


async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show /chat hint."""
    await update.message.reply_text(
        "💬 *Чат с тренером Константином*\n\n"
        "Просто напиши мне любой вопрос прямо в этом чате!\n\n"
        "Например:\n"
        "• _Как правильно делать приседания?_\n"
        "• _Что съесть после тренировки?_\n"
        "• _Болят колени — что делать?_\n\n"
        "Или открой полный чат в приложении 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=open_app_button("/chat"),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Что я умею:*\n\n"
        "/workout — тренировка на сегодня\n"
        "/progress — твой прогресс\n"
        "/chat — чат с тренером\n"
        "/settings — настройки\n\n"
        "💬 Или просто напиши мне любой вопрос — отвечу как тренер!",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free text — route to AI coach."""
    tg_user = update.effective_user
    user, _ = await get_or_create_user(tg_user)
    user_message = update.message.text

    # Show typing...
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    # Call AI via internal API
    from bot.utils.api_client import internal_api_chat
    reply = await internal_api_chat(user.id, user.telegram_id, user_message)

    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📱 Открыть приложение",
                web_app=WebAppInfo(url=f"{MINIAPP_URL}/")
            )],
        ]),
    )
