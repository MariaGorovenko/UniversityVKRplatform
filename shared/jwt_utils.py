from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET не задан в переменных окружения")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Создаёт JWT-токен с данными пользователя (user_id, role и т.д.)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Проверяет токен и возвращает payload или None при ошибке
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_user_id_from_token(token: str) -> Optional[str]:
    payload = verify_token(token)
    if payload:
        return payload.get("sub")  # user_id обычно в поле sub
    return None

def get_role_from_token(token: str) -> Optional[str]:
    payload = verify_token(token)
    if payload:
        return payload.get("role")
    return None