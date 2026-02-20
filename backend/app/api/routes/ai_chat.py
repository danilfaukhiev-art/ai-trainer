from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.base import get_db
from app.core.auth import get_current_user_id
from app.models.user import UserProfile
from app.models.ai import AIConversation
from app.models.progress import UserStreak
from app.services.ai.orchestrator import AIOrchestrator
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    remaining_messages: int  # -1 = unlimited


@router.post("/chat", response_model=ChatResponse)
async def chat_with_trainer(
    payload: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sub_service = SubscriptionService(db)

    # Check message quota
    can_send, remaining = await sub_service.can_send_ai_message(UUID(user_id))
    if not can_send:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "quota_exceeded",
                "message": "Лимит сообщений на сегодня исчерпан. Обнови подписку для безлимитного общения.",
            },
        )

    # Build user context
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = streak_result.scalar_one_or_none()

    user_context = {
        "display_name": profile.display_name if profile else None,
        "goal": profile.goal if profile else "не указана",
        "fitness_level": profile.fitness_level if profile else "не указан",
        "motivation_type": profile.motivation_type if profile else None,
        "training_style": profile.training_style if profile else None,
        "medical_notes": profile.medical_notes if profile else None,
        "last_workout": "нет данных",
        "streak": streak.current_streak if streak else 0,
    }

    orchestrator = AIOrchestrator(UUID(user_id), user_context)
    reply, tokens = await orchestrator.chat(
        user_message=payload.message,
        task="general",
    )

    # Save to DB
    for role, content in [("user", payload.message), ("assistant", reply)]:
        db.add(AIConversation(
            user_id=user_id,
            role=role,
            content=content,
            tokens_used=tokens if role == "assistant" else None,
            model="gpt-4o",
        ))

    # Increment counter
    await sub_service.increment_ai_message_count(UUID(user_id))
    _, new_remaining = await sub_service.can_send_ai_message(UUID(user_id))

    return ChatResponse(reply=reply, remaining_messages=new_remaining)


@router.get("/history")
async def get_chat_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == user_id)
        .order_by(desc(AIConversation.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(messages)
    ]
