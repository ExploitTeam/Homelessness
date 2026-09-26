import json

from maxbot.bot_manager import bot, keyboard_to_start, HOMESTAYS_PER_PAGE
from maxbot.inline_keyboard import InlineKeyboardMarkup, button_types
from maxbot.functions import safe_json_loads, show_all
from database.db_manager import *
from database import db_manager


MY_BOOKINGS_STEP = "my_bookings"
MANAGE_BOOKINGS_STEP = "manage_homestay_bookings"


def _page_count(total: int) -> int:
    if total <= 0:
        return 1
    return (total + HOMESTAYS_PER_PAGE - 1) // HOMESTAYS_PER_PAGE


def _clamp_page(page: int, total: int) -> int:
    last = _page_count(total)
    if page < 1:
        return 1
    if page > last:
        return last
    return page


def _paginate(items: list, page: int) -> tuple[list, int, int]:
    total = len(items)
    page = _clamp_page(page, total)
    start = (page - 1) * HOMESTAYS_PER_PAGE
    return items[start:start + HOMESTAYS_PER_PAGE], page, _page_count(total)


def _callback_mid(update) -> str:
    return (
        update.get("message", {}).get("body", {}).get("mid")
        or update.get("callback", {}).get("body", {}).get("mid")
        or ""
    )


def _callback_user_id(update) -> int:
    return (
        update.get("callback", {}).get("user", {}).get("user_id")
        or update.get("message", {}).get("sender", {}).get("user_id")
        or 0
    )


def _add_pager(keyboard: InlineKeyboardMarkup, page: int, pages: int, total: int, command: str, extra: dict | None = None):
    if total <= HOMESTAYS_PER_PAGE:
        return
    extra = extra or {}
    pager = InlineKeyboardMarkup()
    pager.add_button("⬅️", button_types.callback, payload=json.dumps({
        "command": command, "dir": -1, **extra
    }))
    pager.add_button(f"{page}/{pages}", button_types.callback, payload=json.dumps({
        "command": command, "dir": 0, **extra
    }))
    pager.add_button("➡️", button_types.callback, payload=json.dumps({
        "command": command, "dir": 1, **extra
    }))
    keyboard.add_buttons_one_line(pager.keyboard)


def _list_user_bookings(user) -> list:
    if not user:
        return []
    return get_user_bookings(user) or []


def _as_booking(item):
    if item is None:
        return None
    if hasattr(item, "homestay_id") and hasattr(item, "user_id"):
        return item
    if isinstance(item, int):
        try:
            return get_booking(id=item)
        except TypeError:
            return get_booking(item)
    return None


def _list_homestay_bookings(homestay_id: int) -> list:
    raw = []
    if hasattr(db_manager, "get_homestay_bookings"):
        try:
            raw = db_manager.get_homestay_bookings(homestay_id) or []
        except TypeError:
            raw = db_manager.get_homestay_bookings(homestay_id=homestay_id) or []
    elif hasattr(db_manager, "get_all_bookings"):
        raw = db_manager.get_all_bookings() or []
    else:
        return []

    bookings = []
    for item in raw:
        booking = _as_booking(item)
        if booking and booking.homestay_id == homestay_id:
            bookings.append(booking)
    return bookings


def _managed_homestays(actor) -> list:
    all_homestays = show_all(get_in_dict=True)
    if actor.user_type == 2:
        return all_homestays
    if actor.user_type == 1 and actor.id_homestay:
        return [h for h in all_homestays if h.id == actor.id_homestay]
    return []


def _format_bookings(bookings: list) -> str:
    if not bookings:
        return "Бронирований нет."
    return "\n\n".join(str(b) for b in bookings)


def _restore_bed(booking) -> None:
    homestay = get_homestay(id=booking.homestay_id)
    if not homestay:
        return
    homestay.available_beds = (homestay.available_beds or 0) + 1
    insert_or_update_homestay(homestay)


async def _safe_send(bot, user_id, text, keyboard=None):
    if not user_id:
        return
    try:
        await bot.send_msg(user_id, text, keyboard or keyboard_to_start.keyboard)
    except Exception as error:
        print("BOOKING NOTIFY ERROR:", error)


# =====================================================================
# Мои бронирования
# =====================================================================

def _build_my_bookings_view(user, page: int):
    items = _list_user_bookings(user)
    page_items, page, pages = _paginate(items, page)
    header = "📋 Мои бронирования"
    if len(items) > HOMESTAYS_PER_PAGE:
        header += f"\nСтраница {page}/{pages}"
    text = f"{header}\n\n{_format_bookings(page_items)}"

    keyboard = InlineKeyboardMarkup()
    _add_pager(keyboard, page, pages, len(items), "my_bookings_page")
    for booking in page_items:
        keyboard.add_button(
            f"❌ Удалить бронь #{booking.id}",
            button_types.callback,
            payload=json.dumps({
                "command": "delete_my_booking",
                "booking_id": booking.id,
                "page": page,
            }),
        )
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    return text, keyboard, page


@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "my_bookings")
async def open_my_bookings(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    user = get_user(id=user_id)
    text, keyboard, page = _build_my_bookings_view(user, 1)
    bot.set_next_step(user_id, json.dumps({"command": MY_BOOKINGS_STEP, "page": page}))
    await bot.edit_msg(mid, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "my_bookings_page")
async def my_bookings_page(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    step = safe_json_loads(bot.get_next_step(user_id))
    page = int(step.get("page") or 1) + int(payload.get("dir") or 0)
    user = get_user(id=user_id)
    text, keyboard, page = _build_my_bookings_view(user, page)
    bot.set_next_step(user_id, json.dumps({"command": MY_BOOKINGS_STEP, "page": page}))
    await bot.edit_msg(mid, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "delete_my_booking")
async def delete_my_booking(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    booking = get_booking(id=payload.get("booking_id", -1))
    page = int(payload.get("page") or 1)

    if booking and booking.user_id == user_id:
        manager = get_user(id_homestay=booking.homestay_id)
        _restore_bed(booking)
        delete_booking(booking)
        if manager:
            await _safe_send(
                bot,
                manager.id,
                f"❌ Пользователь отменил бронирование #{booking.id}\n\n{booking}",
            )

    user = get_user(id=user_id)
    text, keyboard, page = _build_my_bookings_view(user, page)
    bot.set_next_step(user_id, json.dumps({"command": MY_BOOKINGS_STEP, "page": page}))
    await bot.edit_msg(mid, text, keyboard.keyboard)


# =====================================================================
# Управление бронированиями (менеджер / админ)
# =====================================================================

def _can_manage_bookings(actor) -> bool:
    return bool(actor) and actor.user_type in (1, 2)


def _can_manage_homestay(actor, homestay_id: int) -> bool:
    if not _can_manage_bookings(actor):
        return False
    if actor.user_type == 2:
        return True
    return actor.id_homestay is not None and int(actor.id_homestay) == int(homestay_id)


@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "manage_bookings")
async def open_manage_bookings(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    actor = get_user(id=user_id)
    if not _can_manage_bookings(actor):
        await bot.edit_msg(mid, "⛔ Раздел доступен только сотрудникам.", keyboard_to_start.keyboard)
        return

    homestays = _managed_homestays(actor)
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    for homestay in homestays:
        keyboard.add_button(
            f"📍 {homestay.address}",
            button_types.callback,
            payload=json.dumps({
                "command": "manage_homestay_bookings",
                "homestay_id": homestay.id,
                "page": 1,
            }),
        )
    text = "Выберите пункт, бронированиями которого хотите управлять 👇"
    if not homestays:
        text = "Нет доступных пунктов для управления бронированиями."
    await bot.edit_msg(mid, text, keyboard.keyboard)


def _build_manage_homestay_view(homestay_id: int, page: int):
    homestay = get_homestay(id=homestay_id)
    items = _list_homestay_bookings(homestay_id)
    page_items, page, pages = _paginate(items, page)
    title = homestay.address if homestay else f"пункт #{homestay_id}"
    header = f"📋 Бронирования пункта\n📍 {title}"
    if len(items) > HOMESTAYS_PER_PAGE:
        header += f"\nСтраница {page}/{pages}"
    text = f"{header}\n\n{_format_bookings(page_items)}"

    keyboard = InlineKeyboardMarkup()
    _add_pager(
        keyboard, page, pages, len(items),
        "manage_homestay_bookings_page",
        {"homestay_id": homestay_id},
    )
    for booking in page_items:
        row = InlineKeyboardMarkup()
        row.add_button(
            f"❌ Удалить #{booking.id}",
            button_types.callback,
            payload=json.dumps({
                "command": "staff_delete_booking",
                "booking_id": booking.id,
                "homestay_id": homestay_id,
                "page": page,
            }),
        )
        if not booking.is_approved:
            row.add_button(
                f"✅ Подтвердить #{booking.id}",
                button_types.callback,
                payload=json.dumps({
                    "command": "staff_approve_booking",
                    "booking_id": booking.id,
                    "homestay_id": homestay_id,
                    "page": page,
                }),
            )
        keyboard.add_buttons_one_line(row.keyboard)
    keyboard.add_button("⬅️ К пунктам", button_types.callback, payload="manage_bookings")
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    return text, keyboard, page


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "manage_homestay_bookings")
async def open_homestay_bookings(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    homestay_id = int(payload.get("homestay_id") or 0)
    actor = get_user(id=user_id)
    if not _can_manage_homestay(actor, homestay_id):
        await bot.edit_msg(mid, "⛔ Недостаточно прав.", keyboard_to_start.keyboard)
        return

    text, keyboard, page = _build_manage_homestay_view(homestay_id, int(payload.get("page") or 1))
    bot.set_next_step(user_id, json.dumps({
        "command": MANAGE_BOOKINGS_STEP,
        "homestay_id": homestay_id,
        "page": page,
    }))
    await bot.edit_msg(mid, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "manage_homestay_bookings_page")
async def manage_homestay_bookings_page(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    homestay_id = int(payload.get("homestay_id") or 0)
    actor = get_user(id=user_id)
    if not _can_manage_homestay(actor, homestay_id):
        await bot.edit_msg(mid, "⛔ Недостаточно прав.", keyboard_to_start.keyboard)
        return

    step = safe_json_loads(bot.get_next_step(user_id))
    page = int(step.get("page") or 1) + int(payload.get("dir") or 0)
    text, keyboard, page = _build_manage_homestay_view(homestay_id, page)
    bot.set_next_step(user_id, json.dumps({
        "command": MANAGE_BOOKINGS_STEP,
        "homestay_id": homestay_id,
        "page": page,
    }))
    await bot.edit_msg(mid, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "staff_approve_booking")
async def staff_approve_booking(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    homestay_id = int(payload.get("homestay_id") or 0)
    actor = get_user(id=user_id)
    if not _can_manage_homestay(actor, homestay_id):
        await bot.edit_msg(mid, "⛔ Недостаточно прав.", keyboard_to_start.keyboard)
        return

    booking = get_booking(id=payload.get("booking_id", -1))
    if booking:
        booking.is_approved = 1
        insert_or_update_booking(booking)
        await _safe_send(
            bot,
            booking.user_id,
            f"❗️ Ваше бронирование подтверждено менеджером!\n"
            f"🔵 Обратите внимание, что бронь действует ближайшие сутки.\n\n"
            f"{booking}",
        )

    page = int(payload.get("page") or 1)
    text, keyboard, page = _build_manage_homestay_view(homestay_id, page)
    await bot.edit_msg(mid, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "staff_delete_booking")
async def staff_delete_booking(update, bot):
    user_id = _callback_user_id(update)
    mid = _callback_mid(update)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    homestay_id = int(payload.get("homestay_id") or 0)
    actor = get_user(id=user_id)
    if not _can_manage_homestay(actor, homestay_id):
        await bot.edit_msg(mid, "⛔ Недостаточно прав.", keyboard_to_start.keyboard)
        return

    booking = get_booking(id=payload.get("booking_id", -1))
    if booking:
        manager_info = ""
        usr_manager = get_user(id_homestay=booking.homestay_id)
        if usr_manager:
            manager_info = (
                f"😎 Менеджер: {usr_manager.username or '-'}\n"
                f"📱 Телефон менеджера: {usr_manager.phone_number or '-'}\n"
            )
        _restore_bed(booking)
        delete_booking(booking)
        await _safe_send(
            bot,
            booking.user_id,
            f"❌ Ваше бронирование удалено менеджером!\n{manager_info}",
        )

    page = int(payload.get("page") or 1)
    text, keyboard, page = _build_manage_homestay_view(homestay_id, page)
    await bot.edit_msg(mid, text, keyboard.keyboard)


# Совместимость с кнопками из /api/book
@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "update_booking_info")
async def update_booking_info(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    mid = _callback_mid(update)
    booking = get_booking(id=payload.get("booking_id", -1))
    if not booking:
        await bot.edit_msg(
            mid,
            "Такого бронирования не существует. "
            "Все бронирования автоматически удаляются через сутки, "
            "не подтвержденные - через 1 час.",
            keyboard_to_start.keyboard,
        )
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("🔄 Обновить", button_types.callback, json.dumps({
        "command": "update_booking_info",
        "booking_id": booking.id,
    }))
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(
        mid,
        f"❗️ Вы забронировали место в пункте ❗️\n{booking}\nПриходите, мы Вас ждем! 😊",
        keyboard.keyboard,
    )


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "approve_booking")
async def approve_booking_from_card(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    payload["homestay_id"] = payload.get("homestay_id")
    booking = get_booking(id=payload.get("booking_id", -1))
    if booking and payload.get("homestay_id") is None:
        payload["homestay_id"] = booking.homestay_id
        payload["page"] = 1
        update.setdefault("callback", {})["payload"] = json.dumps(payload)
    await staff_approve_booking(update, bot)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "delete_booking")
async def delete_booking_from_card(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    booking = get_booking(id=payload.get("booking_id", -1))
    if booking and payload.get("homestay_id") is None:
        payload["homestay_id"] = booking.homestay_id
        payload["page"] = 1
        update.setdefault("callback", {})["payload"] = json.dumps(payload)
    await staff_delete_booking(update, bot)
