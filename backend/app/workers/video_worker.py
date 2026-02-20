"""
Async video analysis worker.
Listens to Redis queue, processes videos, saves results.
"""
import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime

import av
import redis.asyncio as aioredis

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.ai import VideoAnalysis
from app.services.ai.orchestrator import AIOrchestrator
from app.services.storage import StorageService
from sqlalchemy import select

logger = logging.getLogger(__name__)

QUEUE_KEY = "video_analysis_queue"
MAX_FRAMES = 6
FRAME_INTERVAL_SEC = 0.5


async def extract_frames(video_bytes: bytes) -> list[bytes]:
    """Extract key frames from video using PyAV."""
    frames = []
    try:
        with av.open(video_bytes) as container:
            stream = container.streams.video[0]
            fps = float(stream.average_rate)
            interval_frames = max(1, int(fps * FRAME_INTERVAL_SEC))

            for i, frame in enumerate(container.decode(video=0)):
                if i % interval_frames == 0:
                    img = frame.to_image().convert("RGB")
                    # Resize for API efficiency
                    img.thumbnail((640, 640))
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=75)
                    frames.append(buf.getvalue())

                    if len(frames) >= MAX_FRAMES:
                        break
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")

    return frames


async def process_video_job(job_id: str, db_session, storage: StorageService):
    """Process a single video analysis job."""
    # Load job from DB
    result = await db_session.execute(
        select(VideoAnalysis).where(VideoAnalysis.id == job_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        logger.warning(f"Video job {job_id} not found in DB")
        return

    analysis.status = "processing"
    await db_session.commit()

    try:
        # Download video
        video_bytes = await storage.download_to_bytes(analysis.storage_key)

        # Extract frames
        frames = await asyncio.get_event_loop().run_in_executor(
            None, lambda: asyncio.run(extract_frames(video_bytes))
        )

        if not frames:
            raise ValueError("No frames extracted from video")

        # Encode to base64
        frames_b64 = [base64.b64encode(f).decode() for f in frames]

        # Analyze via Vision API
        orchestrator = AIOrchestrator(
            user_id=analysis.user_id,
            user_context={},
        )
        result_data = await orchestrator.analyze_video_frames(
            frames_b64=frames_b64,
            exercise_name=analysis.exercise_name or "упражнение",
        )

        # Save results
        analysis.errors_found = result_data.get("errors", [])
        analysis.corrections = result_data.get("corrections", [])
        analysis.checklist = result_data.get("checklist", [])
        analysis.overall_score = result_data.get("overall_score")
        analysis.summary = result_data.get("summary")
        analysis.status = "done"
        analysis.processed_at = datetime.utcnow()

        # Delete video after analysis (privacy)
        try:
            await storage.delete(analysis.storage_key)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Video analysis failed for job {job_id}: {e}")
        analysis.status = "failed"
        analysis.summary = "Не удалось проанализировать видео. Попробуй ещё раз."

    await db_session.commit()

    # Notify user via bot (fire-and-forget)
    await notify_user_video_done(analysis)


async def notify_user_video_done(analysis: VideoAnalysis):
    """Send Telegram notification when video analysis is complete."""
    from telegram import Bot
    try:
        bot = Bot(token=settings.telegram_bot_token)
        # Get telegram_id from user
        async with AsyncSessionLocal() as db:
            from app.models.user import User
            user_result = await db.execute(
                select(User).where(User.id == analysis.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                if analysis.status == "done":
                    msg = (
                        f"✅ *Анализ техники готов!*\n"
                        f"Упражнение: {analysis.exercise_name}\n"
                        f"Оценка: {analysis.overall_score}/10\n\n"
                        f"Открой приложение, чтобы увидеть детальный разбор."
                    )
                else:
                    msg = "❌ Не удалось проанализировать видео. Попробуй загрузить снова."

                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=msg,
                    parse_mode="Markdown",
                )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")


async def run_worker():
    """Main worker loop — listens to Redis queue."""
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    storage = StorageService()

    logger.info("Video worker started, listening to queue...")

    while True:
        try:
            # Blocking pop with 5s timeout
            job = await redis.brpop(QUEUE_KEY, timeout=5)
            if not job:
                continue

            _, job_id = job
            logger.info(f"Processing video job: {job_id}")

            async with AsyncSessionLocal() as db:
                await process_video_job(job_id, db, storage)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
