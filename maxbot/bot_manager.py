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


def _build_geo_results_text(homestays: list, selected_types: list) -> str:
    header = "Доступные точки (от самой близкой до дальней):"
    labels = _selected_type_labels(selected_types)
    if labels:
        header += "\nФильтр: " + ", ".join(labels)

    if not homestays:
        body = "Пунктов выбранных типов не найдено."
    else:
        body = "\n\n".join(str(h) for h in homestays)
    return f"{header}\n{body}"


def _geo_filter_keyboard(selected_types: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
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
    keyboard.add_button("Смотреть на карте", button_types.callback, payload="open_mini_app")
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    return keyboard


def _save_geo_results_state(user_id: int, homestay_ids: list, selected_types: list,
                            longitude: float, latitude: float) -> None:
    bot.set_next_step(user_id, json.dumps({
        "command": GEO_RESULTS_STEP,
        "ids": homestay_ids,
        "types": selected_types,
        "longitude": longitude,
        "latitude": latitude,
    }))


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
        _save_geo_results_state(
            user_id=id,
            homestay_ids=[h.id for h in res],
            selected_types=[],
            longitude=longitude,
            latitude=latitude,
        )
        text = _build_geo_results_text(res, [])
        keyboard = _geo_filter_keyboard([])
        await bot.send_msg(id, text, keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") == "toggle_geo_type")
async def toggle_geo_type_filter(update, bot):
    user_id = update.get("callback", {}).get("user", {}).get("user_id", 0)
    msg_id = (
        update.get("message", {}).get("body", {}).get("mid")
        or update.get("callback", {}).get("body", {}).get("mid")
    )
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

    ordered = _homestays_by_saved_order(step.get("ids") or [])
    filtered = _filter_homestays_by_types(ordered, selected_types)

    _save_geo_results_state(
        user_id=user_id,
        homestay_ids=step.get("ids") or [h.id for h in ordered],
        selected_types=selected_types,
        longitude=step.get("longitude"),
        latitude=step.get("latitude"),
    )

    text = _build_geo_results_text(filtered, selected_types)
    keyboard = _geo_filter_keyboard(selected_types)
    if msg_id:
        await bot.edit_msg(msg_id, text, keyboard.keyboard)
    else:
        await bot.send_msg(user_id, text, keyboard.keyboard)
