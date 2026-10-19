import json
import os
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from maxbot.bot_manager import bot
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from fastapi.responses import FileResponse
from database.db_manager import *
from database.classes import HomestayTypes
from maxbot.inline_keyboard import InlineKeyboardMarkup, button_types

app = FastAPI(title="HOMELESSNESS API")
app.add_middleware(
    CORSMiddleware,
    # Разрешаем запросы с любых сайтов (включая editor.swagger.io)
    allow_origins=["*"],
    # Обязательно разрешаем передавать куки и заголовки авторизации
    allow_credentials=True,
    # Разрешаем все методы (GET, POST, OPTIONS, PUT, DELETE)
    allow_methods=["*"],
    # Обязательно разрешаем любые заголовки (включая Authorization и Accept)
    allow_headers=["*"],
)
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
    """Публичные данные пунктов + только собственная активная бронь пользователя.

    Ключи прежнего API сохранены. Новые поля: fund, managers, category_label.
    Служебные идентификаторы и роли менеджеров наружу не передаются.
    """
    funds = {fund["id"]: fund for fund in get_funds()}
    current_user = get_user(id=user_id)
    own_bookings = {
        booking.homestay_id: booking.to_json()
        for booking in get_user_bookings(current_user)
    } if current_user else {}

    places = []
    for point in get_all_homestays():
        result = point.to_json()
        fund = funds.get(point.fund_id)
        managers = [
            {
                "name": manager.username or "Сотрудник пункта",
                "phone": manager.phone_number or None,
            }
            for manager in get_homestay_managers(point.id)
        ]
        try:
            category_label = HomestayTypes(point.homestay_type).label
        except (ValueError, TypeError):
            category_label = "Пункт помощи"

        result.update({
            "fund": {
                "name": fund["name"],
                "description": fund["description"] or "",
            } if fund else None,
            "category_label": category_label,
            "managers": managers,
            # Для клиентов прежнего формата (без внутренних ID и ролей).
            "manager_info": {
                "username": managers[0]["name"],
                "phone_number": managers[0]["phone"] or "",
            } if managers else {},
            "booking": own_bookings.get(point.id, {}),
        })
        places.append(result)

    return {"user_id": user_id, "places": places}


class BookingRequest(BaseModel):
    id_homestay: int


BOOKING_COOLDOWN = timedelta(seconds=5) # тайаут на следующее бронирование

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
    all_books = get_user_bookings(user)
    if any(i.homestay_id == homestay.id for i in all_books):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking already created")

    user.last_booking = now.isoformat(timespec="seconds")
    insert_or_update_user(user)
    new_booking = Booking(user_id=user_id, homestay_id=homestay.id, date_time=now.isoformat(timespec="seconds"))
    if not insert_or_update_booking(new_booking):
        raise HTTPException(status_code=500, detail="Booking could not be created")
    homestay.available_beds -= 1
    insert_or_update_homestay(homestay)
    managers = get_homestay_managers(homestay.id)
    if managers:
        keyboard = InlineKeyboardMarkup()
        horizontal_keyboard = InlineKeyboardMarkup()
        horizontal_keyboard.add_button("✅ Подтвердить", button_types.callback, json.dumps({
            "command": "approve_booking", "booking_id": new_booking.id,
        }))
        horizontal_keyboard.add_button("❌ Отклонить", button_types.callback, json.dumps({
            "command": "delete_booking", "booking_id": new_booking.id,
        }))
        keyboard.add_buttons_one_line(horizontal_keyboard.keyboard)
        message = (
            "Новая заявка! Подтвердите её или она автоматически завершится.\n"
            f"Пользователь: {user.username or 'Не указано'}\n"
            f"Телефон: {user.phone_number or 'Номер телефона не указан'}\n\n"
            f"{new_booking}"
        )
        # Bot.send_msg уже рассылает новые заявки остальным менеджерам
        # выбранного пункта; второй цикл создал бы дубли уведомлений.
        try:
            await send_bot_msg(managers[0].id, text=message, keyboard=keyboard.keyboard)
        except Exception as exc:
            print(f"Не удалось отправить уведомления менеджерам: {exc}")

    try:
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button("🔄 Обновить", button_types.callback, json.dumps({
            "command": "update_booking_info",
            "booking_id": new_booking.id,
        }))
        keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
        await send_bot_msg(user.id, text=(f"📝 Заявка на бронирование отправлена\n"
                                    f"{new_booking}\n\n"
                                    "Ожидайте подтверждения менеджера."), keyboard=keyboard.keyboard)
    except Exception as e:
        print("ERROR:", e)

    return {
        "status": "success",
        "message": "Заявка на бронирование создана",
        "last_booking": user.last_booking,
        "available_beds": homestay.available_beds,
        "booking_id": new_booking.id,
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
    # Vite кладёт хэши в /assets; автономная ESM-сборка содержит /src и /vendor.
    if (DIST_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # Не позволяем относительным путям выйти за пределы каталога сборки.
        file_path = (DIST_DIR / full_path).resolve()
        if full_path and file_path.is_relative_to(DIST_DIR.resolve()) and file_path.is_file():
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