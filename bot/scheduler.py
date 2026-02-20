"""
Notification scheduler.
Uses APScheduler to run daily notification tasks.
"""
import asyncio
import logging
from datetime import time

logger = logging.getLogger(__name__)


async def setup_scheduler(app):
    """Setup job queue for daily notifications."""
    from bot.handlers.daily import (
        send_daily_reminders,
        send_evening_reminders,
        send_reengagement,
        send_streak_update,
        send_weekly_summary,
    )

    job_queue = app.job_queue

    # Morning workout reminder — 07:00 UTC+3 (04:00 UTC)
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(send_daily_reminders()),
        time=time(hour=4, minute=0),
        name="morning_reminder",
    )

    # Evening gentle nudge — 20:00 UTC+3 (17:00 UTC)
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(send_evening_reminders()),
        time=time(hour=17, minute=0),
        name="evening_reminder",
    )

    # Streak update — 21:00 UTC+3 (18:00 UTC)
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(send_streak_update()),
        time=time(hour=18, minute=0),
        name="streak_update",
    )

    # Weekly summary — Sunday 10:00 UTC+3 (07:00 UTC)
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(send_weekly_summary()),
        time=time(hour=7, minute=0),
        days=(6,),  # Sunday
        name="weekly_summary",
    )

    # Re-engagement — daily at 12:00 UTC+3 (09:00 UTC)
    job_queue.run_daily(
        lambda ctx: asyncio.ensure_future(send_reengagement()),
        time=time(hour=9, minute=0),
        name="reengagement",
    )

    logger.info("Notification scheduler initialized with 5 daily jobs")
