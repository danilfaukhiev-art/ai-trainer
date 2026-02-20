from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.models.user import User, OnboardingState
from app.models.subscription import Subscription
from app.core.auth import verify_telegram_init_data, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    onboarding_complete: bool


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(
    payload: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate Telegram initData and return JWT.
    Creates user if not exists.
    """
    try:
        tg_user = verify_telegram_init_data(payload.init_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="No user id in initData")

    # Find or create user
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    is_new = False

    if not user:
        user = User(
            telegram_id=telegram_id,
            telegram_username=tg_user.get("username"),
            language_code=tg_user.get("language_code", "ru"),
        )
        db.add(user)
        await db.flush()

        # Create onboarding state — starts with consent step
        onboarding = OnboardingState(user_id=user.id, step="consent")
        db.add(onboarding)

        # Start on free tier — upgrade via /subscribe
        pro_sub = Subscription(
            user_id=user.id,
            tier="free",
            status="active",
            payment_provider="manual",
        )
        db.add(pro_sub)
        is_new = True

    # Check onboarding
    ob_result = await db.execute(
        select(OnboardingState).where(OnboardingState.user_id == user.id)
    )
    onboarding_state = ob_result.scalar_one_or_none()
    onboarding_complete = (
        onboarding_state is not None and onboarding_state.completed_at is not None
    )

    token = create_access_token(str(user.id), telegram_id)

    return AuthResponse(
        access_token=token,
        is_new_user=is_new,
        onboarding_complete=onboarding_complete,
    )
