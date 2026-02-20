"""
Telegram Mini App authentication.
Validates initData from Telegram WebApp and issues JWT.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, unquote
from typing import Optional

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Validate Telegram WebApp initData signature.
    Returns parsed user data if valid, raises ValueError if not.
    """
    vals = dict(parse_qsl(unquote(init_data), strict_parsing=True))
    received_hash = vals.pop("hash", None)

    if not received_hash:
        raise ValueError("No hash in initData")

    # Build data-check-string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(vals.items())
    )

    # HMAC-SHA256 with secret key derived from bot token
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode(),
        hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid initData signature")

    # Parse user JSON
    user_data = json.loads(vals.get("user", "{}"))
    return user_data


def create_access_token(user_id: str, telegram_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "tg_id": telegram_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return user_id


async def get_current_telegram_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    payload = decode_token(credentials.credentials)
    tg_id = payload.get("tg_id")
    if not tg_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return tg_id
