from maxbot.functions import *
from maxbot.inline_keyboard import *
from maxbot.maxapi import Bot
import json
import os
from dotenv import load_dotenv
from database.db_manager import *
from database.classes import HomestayTypes


load_dotenv()

TOKEN = os.getenv("MAX_TOKEN", "")
ADMINS = [int(i) for i in os.getenv("MAX_ADMINS_ID", "").split(",")]
bot = Bot(TOKEN)

HOMESTAYS_PER_PAGE = 5

keyboard_to_start = InlineKeyboardMarkup()
keyboard_to_start.add_button("На главную", button_types.callback, payload="load_start")

from maxbot.user_settings import *
from maxbot.homestay_settings import *


GEO_RESULTS_STEP = "geo_results"


def _selected_type_labels(selected_types: list) -> list[str]:
    selected = set(selected_types or [])
    return [t.label for t in HomestayTypes if t.value in selected]


def _filter_homestays_by_types(homestays: list, selected_types: list) -> list:
    if not selected_types:
        return homestays
    selected = set(selected_types)
    return [h for h in homestays if h.homestay_type in selected]


def _homestays_by_saved_order(saved_ids: list) -> list:
    all_homestays = {h.id: h for h in get_all_homestays()}
    return [all_homestays[hid] for hid in saved_ids if hid in all_homestays]


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


def _paginate(homestays: list, page: int) -> tuple[list, int, int]:
    total = len(homestays)
    page = _clamp_page(page, total)
    start = (page - 1) * HOMESTAYS_PER_PAGE
    return homestays[start:start + HOMESTAYS_PER_PAGE], page, _page_count(total)


def _build_geo_results_text(homestays: list, selected_types: list, page: int, pages: int, total: int) -> str:
    header = "Доступные точки (от самой близкой до дальней):"
    labels = _selected_type_labels(selected_types)
    if labels:
        header += "\nФильтр: " + ", ".join(labels)
    if total > HOMESTAYS_PER_PAGE:
        header += f"\nСтраница {page}/{pages}"

    if not homestays:
        body = "Пунктов выбранных типов не найдено."
    else:
        body = "\n\n".join(str(h) for h in homestays)
    return f"{header}\n{body}"


def _geo_filter_keyboard(selected_types: list, page: int = 1, pages: int = 1, total: int = 0) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    if total > HOMESTAYS_PER_PAGE:
        pager = InlineKeyboardMarkup()
        pager.add_button(
            "⬅️",
            button_types.callback,
            payload=json.dumps({"command": "geo_page", "dir": -1}),
        )
        pager.add_button(
            f"{page}/{pages}",
            button_types.callback,
            payload=json.dumps({"command": "geo_page", "dir": 0}),
        )
        pager.add_button(
            "➡️",
            button_types.callback,
            payload=json.dumps({"command": "geo_page", "dir": 1}),
        )
        keyboard.add_buttons_one_line(pager.keyboard)

    selected = set(selected_types or [])
    for t in HomestayTypes:
        mark = "✅ " if t.value in selected else ""
        keyboard.add_button(
            f"{mark}{t.label}",
            button_types.callback,
            payload=json.dumps({
                "command": "toggle_geo_type",
                "type": t.value,
            })
        )
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    return keyboard


def _save_geo_results_state(user_id: int, homestay_ids: list, selected_types: list,
                            longitude: float, latitude: float, page: int = 1) -> None:
    bot.set_next_step(user_id, json.dumps({
        "command": GEO_RESULTS_STEP,
        "ids": homestay_ids,
        "types": selected_types,
        "page": page,
        "longitude": longitude,
        "latitude": latitude,
    }))


def _render_geo_results(homestay_ids: list, selected_types: list, page: int) -> tuple[str, InlineKeyboardMarkup, int]:
    ordered = _homestays_by_saved_order(homestay_ids)
    filtered = _filter_homestays_by_types(ordered, selected_types)
    page_items, page, pages = _paginate(filtered, page)
    text = _build_geo_results_text(page_items, selected_types, page, pages, len(filtered))
    keyboard = _geo_filter_keyboard(selected_types, page, pages, len(filtered))
    return text, keyboard, page


@bot.message_handler(commands=['start'])
async def only_start(update, bot):
    user = update.get('message', {}).get('sender', {})
    await do_on_start(bot, user)


@bot.message_handler(func=lambda msg, tp: tp == "bot_started")
async def on_start(update, bot):
    await do_on_start(bot, update.get('user', {}))


@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "load_start")
async def to_start(update, bot):
    bot.clear_next_step(update.get("callback", {}).get("user", {}).get("user_id", 0))
    msg_id = update.get("message", {}).get("body", {}).get("mid")
    await do_on_start(bot, update.get("callback", {}).get("user", {}), msg_id=msg_id)



"""On sending location"""


@bot.message_handler(func=lambda msg, tp:
(len(msg.get('message', {}).get('body', {}).get('attachments', [])) > 0 and
 msg.get('message', {}).get('body', {}).get('attachments', [])[0]['type'] == 'location'))
async def on_sending_geo(update, bot):
    user = update.get('message', {}).get('sender', {})
    name = user.get('first_name', "")
    id = user.get('user_id', 0)
    attachments = update.get('message', {}).get('body', {}).get('attachments', [{}])[0]
    longitude, latitude = attachments["longitude"], attachments["latitude"]
    if id:
        res = sort_homestays_by_distance(longitude, latitude)
        homestay_ids = [h.id for h in res]
        text, keyboard, page = _render_geo_results(homestay_ids, [], 1)
        _save_geo_results_state(
            user_id=id,
            homestay_ids=homestay_ids,
            selected_types=[],
            longitude=longitude,
            latitude=latitude,
            page=page,
        )
        await bot.send_msg(id, text, keyboard.keyboard)


async def _update_geo_message(update, bot, selected_types: list, page: int, step: dict):
    user_id = update.get("callback", {}).get("user", {}).get("user_id", 0)
    msg_id = (
        update.get("message", {}).get("body", {}).get("mid")
        or update.get("callback", {}).get("body", {}).get("mid")
    )
    homestay_ids = step.get("ids") or []
    text, keyboard, page = _render_geo_results(homestay_ids, selected_types, page)
    _save_geo_results_state(
        user_id=user_id,
        homestay_ids=homestay_ids,
        selected_types=selected_types,
        longitude=step.get("longitude"),
        latitude=step.get("latitude"),
        page=page,
    )
    if msg_id:
        await bot.edit_msg(msg_id, text, keyboard.keyboard)
    else:
        await bot.send_msg(user_id, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "toggle_geo_type")
async def toggle_geo_type_filter(update, bot):
    user_id = update.get("callback", {}).get("user", {}).get("user_id", 0)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    toggled_type = payload.get("type")

    step = safe_json_loads(bot.get_next_step(user_id))
    if not user_id or step.get("command") != GEO_RESULTS_STEP:
        await bot.send_msg(user_id, "Сначала отправьте геопозицию, чтобы получить список пунктов.")
        return

    selected_types = list(step.get("types") or [])
    if toggled_type in selected_types:
        selected_types.remove(toggled_type)
    elif toggled_type is not None:
        selected_types.append(toggled_type)

    await _update_geo_message(update, bot, selected_types, 1, step)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "geo_page")
async def change_geo_page(update, bot):
    user_id = update.get("callback", {}).get("user", {}).get("user_id", 0)
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    direction = int(payload.get("dir", 0))

    step = safe_json_loads(bot.get_next_step(user_id))
    if not user_id or step.get("command") != GEO_RESULTS_STEP:
        await bot.send_msg(user_id, "Сначала отправьте геопозицию, чтобы получить список пунктов.")
        return

    selected_types = list(step.get("types") or [])
    page = int(step.get("page") or 1) + direction
    await _update_geo_message(update, bot, selected_types, page, step)

@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "update_booking_info")
async def update_booking_info(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    mid = update.get("message", {}).get("body", {}).get("mid", "")
    booking = get_booking(payload.get("booking_id", -1))
    if not booking:
        await bot.edit_msg(mid, f"Такого бронирования не существует. "
                          f"Все бронирования автоматически удаляются через сутки, "
                          f"не подтвержденные - через 1 час.", btns=keyboard_to_start.keyboard)
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("🔄 Обновить", button_types.callback, json.dumps({
        "command": "update_booking_info",
        "booking_id": booking.id,
    }))
    await bot.edit_msg(mid,
                 text=(f"❗️ Вы забронировани место в пункте ❗️\n"
                       f"{booking}\n"
                       f"Приходите, мы Вас ждем! 😊"),
                 btns=keyboard.keyboard
                 )

@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "approve_booking")
async def update_booking_info(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    mid = update.get("message", {}).get("body", {}).get("mid", "")
    booking = get_booking(payload.get("booking_id", -1))
    if not booking:
        await bot.edit_msg(mid, f"Такого бронирования не существует. "
                          f"Все бронирования автоматически удаляются через сутки, "
                          f"не подтвержденные - через 1 час.", keyboard_to_start.keyboard)
        return
    user = get_user(id=booking.user_id)
    booking.is_approved = 1
    insert_or_update_booking(booking)
    await bot.edit_msg(mid,
                 text=(f"❗️ Бронирование подтверждено ❗️\n"
                       f"Заявку оставил {user.username}\n"
                       f"Контактный номер: {user.phone_number if user.phone_number else '-'}\n"
                       f"Управлять всеми бронями вы можете по кнопке Бронирования в главном меню\n\n"
                       f"{booking}"),
                 btns=keyboard_to_start.keyboard
                 )
    await bot.send_msg(booking.user_id, text=(f"❗️ Ваше бронирование подтверждено менеджером!\n"
                                  f"🔵 Обратите внимание, что бронь действует ближайшие сутки. \n\n"
                                  f"{booking}"), btns=keyboard_to_start.keyboard)

@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "delete_booking")
async def update_booking_info(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    mid = update.get("message", {}).get("body", {}).get("mid", "")
    booking = get_booking(payload.get("booking_id", -1))
    if not booking:
        await bot.edit_msg(mid, text=(f"Такого бронирования не существует. "
                          f"Все бронирования автоматически удаляются через сутки, "
                          f"не подтвержденные - через 1 час."), btns=keyboard_to_start.keyboard)
        return
    delete_booking(booking)
    await bot.edit_msg(mid,
                 text=(f"❌ Бронирование отменено ❌️\n"
                       f"Управлять всеми бронями вы можете по кнопке Броинварония в главном меню\n\n"
                       f"{booking}"),
                 btns=keyboard_to_start.keyboard
                 )
    manager = ""
    usr_manager = get_user(id_homestay=booking.homestay_id)
    if usr_manager:
        name = usr_manager.username
        phone = usr_manager.phone_number
        manager = (f"😎 Менеджер: {name if name else '-'}\n"
                   f"📱 Телефон менеджера: {phone if phone else '-'}\n")
    await bot.send_msg(booking.user_id, text = (f"❌️ Ваше бронирование удалено менеджером!\n"
                                    f"{manager}"),
                       btns=keyboard_to_start.keyboard)