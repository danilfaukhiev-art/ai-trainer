"""
Daily notification scheduler.
Sends workout reminders, streak updates, re-engagement messages.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.constants import ParseMode

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.user import User, UserProfile
from app.models.workout import Workout
from app.models.progress import UserStreak
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)

MINIAPP_URL = settings.telegram_webhook_url.replace("/webhook/telegram", "")


async def send_daily_reminders():
    """
    Main scheduler function — call this at 07:00 daily.
    Sends workout reminders to users with pending workouts today.
    """
    bot = Bot(token=settings.telegram_bot_token)
    today = date.today()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, Workout)
            .join(Workout, Workout.user_id == User.id)
            .where(
                and_(
                    Workout.scheduled_date == today,
                    Workout.status == "pending",
                    User.deleted_at.is_(None),
                )
            )
        )
        rows = result.all()

        for user, workout in rows:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "🌅 *Доброе утро!*\n\n"
                        "Твоя тренировка на сегодня готова.\n"
                        "Небольшой шаг каждый день — большой результат! 💪"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "💪 Начать тренировку",
                            web_app=WebAppInfo(
                                url=f"{MINIAPP_URL}/workout/{workout.id}"
                            )
                        )],
                    ]),
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Failed to notify user {user.telegram_id}: {e}")


async def send_evening_reminders():
    """
    Send at 20:00 to users who have pending workout but didn't complete.
    """
    bot = Bot(token=settings.telegram_bot_token)
    today = date.today()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, Workout)
            .join(Workout, Workout.user_id == User.id)
            .where(
                and_(
                    Workout.scheduled_date == today,
                    Workout.status == "pending",
                    User.deleted_at.is_(None),
                )
            )
        )
        rows = result.all()

        for user, workout in rows:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "🌙 Ещё не поздно!\n\n"
                        "У тебя есть тренировка на сегодня.\n"
                        "Даже 20 минут — это уже победа 🏆"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "⚡ Быстрая тренировка",
                            web_app=WebAppInfo(
                                url=f"{MINIAPP_URL}/workout/{workout.id}"
                            )
                        )],
                    ]),
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Evening reminder failed for {user.telegram_id}: {e}")


async def send_streak_update():
    """
    Send at 21:00 — streak milestone celebrations.
    """
    bot = Bot(token=settings.telegram_bot_token)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, UserStreak)
            .join(UserStreak, UserStreak.user_id == User.id)
            .where(
                and_(
                    UserStreak.last_activity == date.today(),
                    UserStreak.current_streak.in_([3, 7, 14, 21, 30, 50, 100]),
                    User.deleted_at.is_(None),
                )
            )
        )
        rows = result.all()

        milestones = {
            3: ("🔥 3 дня подряд!", "Отличное начало! Привычка формируется."),
            7: ("⭐ Неделя тренировок!", "Целая неделя без пропусков — ты молодец!"),
            14: ("💪 2 недели!", "Серьёзный результат. Привычка укрепляется!"),
            21: ("🏆 21 день!", "Научно доказано — привычка сформирована!"),
            30: ("🎯 Месяц!", "Невероятно! Целый месяц без пропусков!"),
            50: ("💎 50 дней!", "Ты в элите! Мало кто доходит до 50 дней."),
            100: ("👑 100 ДНЕЙ!", "Легенда! Сотня дней тренировок подряд!"),
        }

        for user, streak in rows:
            milestone = milestones.get(streak.current_streak)
            if not milestone:
                continue
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"{milestone[0]}\n\n{milestone[1]}\n\n🔥 Стрик: {streak.current_streak} дней",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "📊 Мой прогресс",
                            web_app=WebAppInfo(url=f"{MINIAPP_URL}/progress")
                        )],
                    ]),
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Streak update failed for {user.telegram_id}: {e}")


async def send_weekly_summary():
    """
    Send every Sunday — weekly training summary.
    """
    bot = Bot(token=settings.telegram_bot_token)
    week_ago = date.today() - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                User,
                func.count(Workout.id).label("total"),
                func.count(Workout.id).filter(Workout.status == "completed").label("completed"),
            )
            .join(Workout, Workout.user_id == User.id)
            .where(
                and_(
                    Workout.scheduled_date >= week_ago,
                    User.deleted_at.is_(None),
                )
            )
            .group_by(User.id)
        )
        rows = result.all()

        for user, total, completed in rows:
            pct = round((completed / total) * 100) if total > 0 else 0
            emoji = "🏆" if pct >= 80 else "💪" if pct >= 50 else "📈"

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"{emoji} *Итоги недели*\n\n"
                        f"Тренировок: {completed}/{total}\n"
                        f"Выполнение: {pct}%\n\n"
                        f"{'Отличная неделя! Так держать!' if pct >= 80 else 'Каждая тренировка — шаг вперёд!'}"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "📊 Полная статистика",
                            web_app=WebAppInfo(url=f"{MINIAPP_URL}/progress")
                        )],
                    ]),
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Weekly summary failed for {user.telegram_id}: {e}")


async def send_reengagement():
    """
    Send personalized re-engagement to users inactive for 3+ days.
    Uses the user's display name and streak history for a personal touch.
    """
    bot = Bot(token=settings.telegram_bot_token)
    three_days_ago = date.today() - timedelta(days=3)
    seven_days_ago = date.today() - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User, UserStreak, UserProfile)
            .join(UserStreak, UserStreak.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(
                and_(
                    UserStreak.last_activity <= three_days_ago,
                    User.deleted_at.is_(None),
                )
            )
        )
        rows = result.all()

        for user, streak, profile in rows:
            days_away = (date.today() - streak.last_activity).days
            name = profile.display_name if profile and profile.display_name else None
            greeting = f"{name}," if name else "Привет!"

            # Different messages based on how long they've been away
            if days_away <= 4:
                text = (
                    f"💭 {greeting}\n\n"
                    f"Уже {days_away} дня без тренировки. Твой стрик был {streak.current_streak} дн 🔥\n\n"
                    f"Даже 20 минут сегодня — и ты снова в ритме."
                )
            elif days_away <= 7:
                text = (
                    f"🌟 {greeting}\n\n"
                    f"Ты пропустил {days_away} дней. Это нормально.\n"
                    f"Я скорректировал план под твой возврат — начнём с лёгкого.\n\n"
                    f"Без давления. Просто первый шаг."
                )
            else:
                goal_map = {
                    "fat_loss": "похудеть", "muscle_gain": "набрать мышцы",
                    "health": "улучшить здоровье", "endurance": "выносливость",
                }
                goal = goal_map.get(profile.goal or "", "прийти в форму") if profile else "прийти в форму"
                text = (
                    f"👋 {greeting}\n\n"
                    f"Ты не заходил {days_away} дней. Твоя цель — {goal}.\n"
                    f"Я всё ещё здесь и план готов.\n\n"
                    f"Возвращайся когда захочешь — начнём заново."
                )

            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🔄 Вернуться к тренировкам",
                            web_app=WebAppInfo(url=f"{MINIAPP_URL}/")
                        )],
                    ]),
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Re-engagement failed for {user.telegram_id}: {e}")
