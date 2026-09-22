import json
import sqlite3
from maxbot.bot_manager import bot, keyboard_to_start
from database.db_manager import *
from maxbot.functions import *
from maxbot.maxapi import Bot
from parser.parser import proceed_parsing
import parser.coordinate_finder_v2 as coordinates_finder_v2
from database import db_manager, classes

# =====================================================================
# МЕТОДЫ ОДНОЙ КНОПКИ
# =====================================================================

async def do_remove_homestay(user_id: int, homestay_id: int, bot, update):
    """Удаление пункта размещения"""
    homestay = db_manager.get_homestay(id=homestay_id)
    res = db_manager.delete_homestay(homestay)
    if res:
        await bot.send_msg(user_id, f"❌ Пункт с адресом «{homestay.address}» успешно удален из базы данных.",
                           keyboard_to_start.keyboard)
    else:
        await bot.send_msg(user_id, f"❌ Ошибка удаления пункта {homestay.address}",
                           keyboard_to_start.keyboard)


async def do_change_address(user_id: int, homestay_id: int, bot, update):
    """Запрос нового адреса"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))
    await bot.send_msg(user_id, f"📝 Введите новый адрес для пункта (ID: {homestay_id}):", keyboard.keyboard)
    bot.set_next_step(user_id, json.dumps({
        "command": "input_new_address",
        "target_homestay": homestay_id
    }))


async def do_edit_places(user_id: int, homestay_id: int, bot, update):
    """Запрос количества мест"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))
    await bot.send_msg(user_id, f"🔢 Укажите новое общее количество мест для пункта (ID: {homestay_id}):", keyboard.keyboard)
    bot.set_next_step(user_id, json.dumps({
        "command": "input_new_places",
        "target_homestay": homestay_id
    }))


async def do_close_homestay(user_id: int, homestay_id: int, bot, update):
    """Перевод пункта в статус закрытого/открытого"""
    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.is_working = 1 if not homestay.is_working else 0
        db_manager.insert_or_update_homestay(homestay)
        update['callback']['payload'] = json.dumps({"homestay_id": homestay_id})
        await edit_one_homestay(update, bot)


async def update_location(user_id: int, homestay_id: int, bot, update):
    """Перевод пункта в статус закрытого/открытого"""
    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.longtitude, homestay.latitude = coordinates_finder_v2.get_coordinates(homestay.address)
        db_manager.insert_or_update_homestay(homestay)
        await bot.send_msg(user_id, f"Данные обновлены.")


async def do_change_work_hours(user_id: int, homestay_id: int, bot, update):
    """Запрос новых часов работы"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))
    await bot.send_msg(user_id, f"⏰ Введите новые часы работы в формате 'ЧЧ:ММ-ЧЧ:ММ' для пункта (ID: {homestay_id}):",
                       keyboard.keyboard)
    bot.set_next_step(user_id, json.dumps({
        "command": "input_new_work_hours",
        "target_homestay": homestay_id
    }))


async def do_change_description(user_id: int, homestay_id: int, bot, update):
    """Запрос новой дополнительной информации"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))
    await bot.send_msg(user_id, f"ℹ️ Введите новое описание / доп. информацию для пункта (ID: {homestay_id}):",
                       keyboard.keyboard)
    bot.set_next_step(user_id, json.dumps({
        "command": "input_new_description",
        "target_homestay": homestay_id
    }))


async def do_change_type(user_id: int, homestay_id: int, bot, update):
    """Запрос нового типа пункта"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))
    await bot.send_msg(user_id,
                       f"⛺️ Введите новый тип пункта (например: Хостел, Отель, Глэмпинг) для ID {homestay_id}:",
                       keyboard.keyboard)
    bot.set_next_step(user_id, json.dumps({
        "command": "input_new_type",
        "target_homestay": homestay_id
    }))


HOMESTAY_ACTIONS = {
    "remove_homestay": do_remove_homestay,
    "change_address": do_change_address,
    "edit_places": do_edit_places,
    "close_homestay": do_close_homestay,
    "change_work_hours": do_change_work_hours,
    "change_description_homestay": do_change_description,
    "change_type_homestay": do_change_type,
    "update_location": update_location
}


# =====================================================================
# ХЕНДЛЕРЫ ВВОДА
# =====================================================================

@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "input_new_address")
async def input_new_address(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")

    if not text:
        await bot.send_msg(sender_id, "⚠️ Текст адреса не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.address = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

        update['callback'] = {'payload': json.dumps({"homestay_id": homestay_id}), 'user': {'user_id': sender_id}}
        await edit_one_homestay(update, bot)
    await edit_one_homestay(update, bot, True)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get("command") == "input_new_places")
async def input_new_places(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")

    try:
        places_count = int(text)
    except ValueError:
        await bot.send_msg(sender_id, "⚠️ Пожалуйста, введите корректное число для количества мест.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.all_beds = places_count
        homestay.available_beds = places_count
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

        update['callback'] = {'payload': json.dumps({"homestay_id": homestay_id}), 'user': {'user_id': sender_id}}
        await edit_one_homestay(update, bot)
    await edit_one_homestay(update, bot, True)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "input_new_work_hours")
async def input_new_work_hours(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")

    if "-" not in text:
        await bot.send_msg(sender_id, "⚠️ Формат должен содержать дефис, например: 09:00-18:00")
        return

    try:
        open_time, close_time = text.split("-")
    except ValueError:
        await bot.send_msg(sender_id, "⚠️ Ошибка парсинга времени. Введите в формате 'ЧЧ:ММ-ЧЧ:ММ'")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.open_time = open_time.strip()
        homestay.close_time = close_time.strip()
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

        update['callback'] = {'payload': json.dumps({"homestay_id": homestay_id}), 'user': {'user_id': sender_id}}
        await edit_one_homestay(update, bot)
    await edit_one_homestay(update, bot, True)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "input_new_description")
async def input_new_description(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")

    if not text:
        await bot.send_msg(sender_id, "⚠️ Описание не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.additional_info = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

        update['callback'] = {'payload': json.dumps({"homestay_id": homestay_id}), 'user': {'user_id': sender_id}}
        await edit_one_homestay(update, bot)
    await edit_one_homestay(update, bot, True)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get("command") == "input_new_type")
async def input_new_type(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")

    if not text:
        await bot.send_msg(sender_id, "⚠️ Тип пункта не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.homestay_type = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

        update['callback'] = {'payload': json.dumps({"homestay_id": homestay_id}), 'user': {'user_id': sender_id}}
        await edit_one_homestay(update, bot)
    await edit_one_homestay(update, bot, True)


# =====================================================================
# НАЧАЛО БЛОКА: ОСНОВНЫЕ ИНТЕРФЕЙСНЫЕ МЕТОДЫ КНОПОК
# =====================================================================

@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "edit_homestay")
async def edit_user_button_pressed(update, bot):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    all_homestays = show_all(get_in_dict=True)
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    keyboard.add_button("🔄 Обновить базу", button_types.callback, payload="update_db")
    keyboard.add_button("🏠 Добавить новый пункт",
                        button_types.callback,
                        payload=json.dumps({
                            "command": "add_homestay",
                        }))
    for i in all_homestays:
        keyboard.add_button(f"📍 {i.address}",
                            button_types.callback,
                            payload=json.dumps({
                                "command": "edit_one_homestay",
                                "homestay_id": i.id
                            }))
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(msg_id, f"Добавьте новый пункт или отредактируйте существующий 👇", keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp:
json.loads(msg.get("callback", {}).get("payload", "")).get("command", "") == "edit_one_homestay")
async def edit_one_homestay(update, bot, send_new = False):
    keyboard = InlineKeyboardMarkup()
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    bot.clear_next_step(id)
    homestay_id = json.loads(update.get("callback", {}).get("payload", "")).get("homestay_id", -1)
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    homestay = get_homestay(homestay_id)
    usr = get_user(id_homestay=homestay_id)
    usr_info_homestay = ""
    if not usr:
        usr_info_homestay = "Нет менеджера"
    else:
        usr_info_homestay = usr
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    keyboard.add_button("❌ Удалить пункт", button_types.callback,payload=json.dumps(
        {"command": "remove_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Изменить адрес", button_types.callback, payload=json.dumps(
        {"command": "change_address", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Редактировать места", button_types.callback, payload=json.dumps(
        {"command": "edit_places", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Закрыть" if homestay.is_working else "Открыть", button_types.callback, payload=json.dumps(
        {"command": "close_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Изменить часы работы", button_types.callback, payload=json.dumps(
        {"command": "change_work_hours", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Изменить дополнительную информацию", button_types.callback, payload=json.dumps(
        {"command": "change_description_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Изменить тип пункта", button_types.callback, payload=json.dumps(
        {"command": "change_type_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Обновить координаты", button_types.callback, payload=json.dumps(
        {"command": "update_location", "homestay_id": homestay_id}
    ))
    if not send_new:
        await bot.edit_msg(msg_id, f"Информация о пункте:\n{homestay}\n\nМенеджер:\n{usr_info_homestay}", keyboard.keyboard)
    else:
        await bot.send_msg(id, f"Информация о пункте:\n{homestay}\n\nМенеджер:\n{usr_info_homestay}", keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") in HOMESTAY_ACTIONS
                     )
async def handle_homestay_management(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    command = payload.get("command")
    homestay_id = int(payload.get("homestay_id", 0))
    sender_id = update.get('callback', {}).get('user', {}).get('user_id', 0)

    if not homestay_id or not sender_id:
        return
    action_func = HOMESTAY_ACTIONS[command]
    await action_func(sender_id, homestay_id, bot, update)

@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "update_db")
async def update_db(update, bot):
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(msg_id, f"🔄 Обновление данных... Пожалуйста, ждите.")
    proceed_parsing()
    await edit_user_button_pressed(update, bot)


