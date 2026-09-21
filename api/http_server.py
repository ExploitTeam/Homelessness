import json
import os
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from database.db_manager import *

app = FastAPI(title="HOMELESSNESS API")

BOT_TOKEN = os.getenv("MAX_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

security = HTTPBearer()

def verify_max_init_data(init_data_str: str) -> dict:
    """
    Проверяет hash из initData мессенджера МАКС.
    Возвращает словарь с данными пользователя, если всё ок.
    """
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_str, keep_blank_values=True))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid initData format")

    if "hash" not in parsed_data:
        raise HTTPException(status_code=400, detail="Missing hash in initData")

    received_hash = parsed_data.pop("hash")
    data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed_data.items())])

    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Authentication failed: Hash mismatch")

    return parsed_data

def create_access_token(user_id: int) -> str:
    """Создает JWT токен сессии для Mini App"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> int:
    """Депенденси для защиты эндпоинтов. Извлекает user_id из заголовка Bearer"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid session token")
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate session")

class AuthRequest(BaseModel):
    initData: str


@app.post("/api/auth")
async def auth_mini_app(payload: AuthRequest):
    """
    Точка входа. Сюда фронтенд отправляет initData при запуске приложения.
    """
    user_data = verify_max_init_data(payload.initData)
    try:
        user_json = json.loads(user_data.get("user", "{}"))
        user_id = int(user_json.get("id"))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse user_id from initData")
    token = create_access_token(user_id)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/places")
async def info(user_id: int = Depends(get_current_user_id)):
    """
    Защищенный эндпоинт. Доступен только с валидным JWT-токеном.
    Заголовки запроса от фронта: Authorization: Bearer <token>
    """
    all_homestays = get_all_homestays()
    return {
        "user_id": user_id,
        "places": all_homestays
    }


class BookingRequest(BaseModel):
    id_homestay: int


@app.post("/api/book")
async def book(booking: BookingRequest, user_id: int = Depends(get_current_user_id)):
    """
    Защищенное бронирование места
    """
    homestay = get_homestay(booking.id_homestay)
    if not homestay:
        raise HTTPException(status_code=404, detail="Homestay not found")

    if homestay.available_beds <= 0:
        raise HTTPException(status_code=400, detail="No available beds left")

    return {"status": "success", "message": f"User {user_id} booked homestay {booking.id_homestay}"}

def start_server():
    """Функция для программного запуска сервера из любой точки проекта"""
    uvicorn.run(
        "api.http_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
