import json
import os
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from starlette.staticfiles import StaticFiles
from maxbot.bot_manager import bot
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from fastapi.responses import FileResponse
from database.db_manager import *
from maxbot.functions import is_point_open

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
    answer = []
    for homestay in all_homestays:
        usr = get_user(id_homestay=homestay.id)
        print(f"Address {homestay.address}, ({homestay.longtitude, homestay.latitude})")
        res = homestay.to_json()
        if usr:
            res["manager_info"] = usr
        answer.append(res)

    print("REQUEST ANSWER: \n", {
        "user_id": user_id,
        "places" : answer,
    })
    return {
        "user_id": user_id,
        "places": answer
    }


class BookingRequest(BaseModel):
    id_homestay: int


BOOKING_COOLDOWN = timedelta(minutes=5) # тайаут на следующее бронирование

def _parse_last_booking(value: str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "-"}:
        return None

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None

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

    user = get_user(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now()
    last = _parse_last_booking(user.last_booking)

    if last is not None and now - last < BOOKING_COOLDOWN:
        wait_sec = int((BOOKING_COOLDOWN - (now - last)).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"Повторное бронирование можно сделать через {wait_sec} сек."
        )

    user.last_booking = now.isoformat(timespec="seconds")
    insert_or_update_user(user)

    homestay.available_beds -= 1
    insert_or_update_homestay(homestay)
    manager = get_user(id_homestay=homestay.id)
    manager_info = ""
    if manager:
        manager_info = (f"👤 Менеджер пункта: {manager.username}\n"
                        f"📱 Телефон менеджера: {manager.phone_number if manager.phone_number else '-'}")
        try:
            await send_bot_msg(manager.id, text=(f"Новая заявка!\n"
                                           f"Заявку оставил {user.username}\n"
                                           f"Контактный номер: {user.phone_number if user.phone_number else '-'}\n"))
        except Exception as e:
            print("ERROR:", e)

    try:
        await send_bot_msg(user.id, text=(f"❗️ Вы оставили заявку в пункт по адресу {homestay.address}.\n"
                                    f"{'🟢 СЕЙЧАС ПУНКТ ОТКРЫТ\n' if is_point_open(homestay.open_time, homestay.close_time) 
                                                               and homestay.is_working
                                    else '🔴  СЕЙЧАС ПУНКТ ЗАКРЫТ\n' if homestay.is_working else ''}"
                                    f"⏱️ Время работы пункта: {homestay.open_time} - {homestay.close_time}\n"
                                    f"{manager_info}\n\n"
                                    f"Приходите, мы Вас ждем! 😊"))
    except Exception as e:
        print("ERROR:", e)

    return {
        "status": "success",
        "message": f"User {user_id} booked homestay {booking.id_homestay}",
        "last_booking": user.last_booking,
        "available_beds": homestay.available_beds,
    }

import asyncio
from maxbot.bot_manager import bot


async def send_bot_msg(user_id: int, text: str, keyboard=None):
    loop = getattr(bot, "loop", None)
    if loop is None or not loop.is_running():
        raise RuntimeError("Event loop бота ещё не запущен")

    future = asyncio.run_coroutine_threadsafe(
        bot.send_msg(user_id, text, keyboard),
        loop,
    )
    return await asyncio.wrap_future(future)

DIST_DIR = Path(__file__).resolve().parents[1] / "Web" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        file_path = DIST_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")

def start_server():
    """Функция для программного запуска сервера из любой точки проекта"""
    uvicorn.run(
        "api.http_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )