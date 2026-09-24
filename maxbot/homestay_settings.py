import json
import sqlite3
from maxbot.bot_manager import bot, keyboard_to_start
from database.db_manager import *
from maxbot.functions import *
from maxbot.maxapi import Bot
from parser.parser import proceed_parsing
import parser.coordinates_finder as coordinates_finder
from database import db_manager, classes

USER_TYPE_USER = 0
USER_TYPE_MANAGER = 1
USER_TYPE_ADMIN = 2

ADMIN_ONLY_COMMANDS = {"add_homestay"}


def extract_user_id(update) -> int:
    if update.get("callback"):
        return update.get("callback", {}).get("user", {}).get("user_id", 0) or 0
    return update.get("message", {}).get("sender", {}).get("user_id", 0) or 0


def get_actor(user_id: int):
    if not user_id:
        return None
    return get_user(id=user_id)


def is_admin(actor) -> bool:
    return bool(actor) and actor.user_type == USER_TYPE_ADMIN


def is_manager(actor) -> bool:
    return bool(actor) and actor.user_type == USER_TYPE_MANAGER


def can_open_homestay_panel(actor) -> bool:
    return is_admin(actor) or is_manager(actor)


def can_manage_homestay(actor, homestay_id: int) -> bool:
    if is_admin(actor):
        return True
    if is_manager(actor) and actor.id_homestay is not None:
        try:
            return int(actor.id_homestay) == int(homestay_id)
        except (TypeError, ValueError):
            return False
    return False


async def deny_access(bot, user_id: int, text: str = "⛔ Недостаточно прав для этого действия."):
    if user_id:
        await bot.send_msg(user_id, text)


async def require_panel_access(update, bot):
    user_id = extract_user_id(update)
    actor = get_actor(user_id)
    if can_open_homestay_panel(actor):
        return actor
    await deny_access(bot, user_id, "⛔ Этот раздел доступен только сотрудникам.")
    return None


async def require_homestay_access(update, bot, homestay_id: int):
    user_id = extract_user_id(update)
    actor = get_actor(user_id)
    if can_manage_homestay(actor, homestay_id):
        return actor
    if can_open_homestay_panel(actor):
        await deny_access(bot, user_id, "⛔ Вы можете управлять только своим пунктом.")
    else:
        await deny_access(bot, user_id, "⛔ Этот раздел доступен только сотрудникам.")
    return None


async def require_admin(update, bot):
    user_id = extract_user_id(update)
    actor = get_actor(user_id)
    if is_admin(actor):
        return actor
    await deny_access(bot, user_id, "⛔ Это действие доступно только администратору.")
    return None


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
    await bot.send_msg(user_id, f"🔢 Укажите новое общее количество мест в формате ВСЕГО_МЕСТ/ЗАНЯТО:",
                       keyboard.keyboard)
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


async def do_add_homestay(user_id: int, homestay_id: int, bot, update):
    """Начало процесса создания нового пункта"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, "edit_homestay")

    await bot.send_msg(user_id,
                       "🏠 Начинаем добавление нового пункта.\n\n"
                       "Шаг 1: Введите полный географический адрес объекта (например: Санкт-Петербург, ул. Ленина, д. 5):",
                       keyboard.keyboard)

    bot.set_next_step(user_id, json.dumps({
        "command": "create_input_address"
    }))


async def do_change_type(user_id: int, homestay_id: int, bot, update):
    """Запрос нового типа пункта"""
    homestay = db_manager.get_homestay(id=homestay_id)
    if not homestay:
        return
    keyboard = InlineKeyboardMarkup()
    for i in classes.HomestayTypes:
        keyboard.add_button(i.label, button_types.callback, payload=json.dumps({
            "command": "change_homestay_type",
            "homestay_id": homestay_id,
            "type": i.value
        }))

    keyboard.add_button("❌ Отмена", button_types.callback, json.dumps(
        {
            "command": "edit_one_homestay",
            "homestay_id": homestay_id
        }
    ))

    mgs_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(mgs_id,
                       f"{homestay}\n\n"
                       f"Выберите новый тип кнопками ниже 👇",
                       keyboard.keyboard)


async def update_geo_info(user_id: int, homestay_id: int, bot, update):
    homestay = db_manager.get_homestay(id=homestay_id)
    longitute, latitude, res = coordinates_finder.get_coordinates(homestay.address)
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button(f"Хорошо", button_types.callback, json.dumps({
        "command": "edit_one_homestay",
        "homestay_id": homestay_id
    }))
    if not res:
        await bot.send_msg(user_id, f"Ошибка обновления координат. Возможно, указан неизвестный адрес.",
                     keyboard.keyboard)
        return

    await bot.send_msg(user_id, f"Координаты обновлены! Проверьте карту. ",
                 keyboard.keyboard)


HOMESTAY_ACTIONS = {
    "remove_homestay": do_remove_homestay,
    "change_address": do_change_address,
    "edit_places": do_edit_places,
    "close_homestay": do_close_homestay,
    "change_work_hours": do_change_work_hours,
    "change_description_homestay": do_change_description,
    "change_type_homestay": do_change_type,
    "add_homestay": do_add_homestay,
    "update_geo_info": update_geo_info
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
    if not await require_homestay_access(update, bot, homestay_id):
        bot.clear_next_step(sender_id)
        return

    if not text:
        await bot.send_msg(sender_id, "⚠️ Текст адреса не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    lat, lon = (0.0, 0.0)
    try:
        lat, lon, _ = coordinates_finder.get_coordinates(text)
    except Exception as e:
        print(f"Ошибка при первичном поиске координат: {e}")
    if homestay:
        homestay.latitude = lat
        homestay.longtitude = lon
        homestay.address = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)

    await edit_one_homestay(update, bot, True, homestay_id)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get("command") == "input_new_places")
async def input_new_places(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()
    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")
    if not await require_homestay_access(update, bot, homestay_id):
        bot.clear_next_step(sender_id)
        return

    try:
        total, free = text.split("/")
        total = int(total)
        free = int(free)
    except ValueError:
        await bot.send_msg(sender_id, "⚠️ Пожалуйста, введите корректное число для количества мест.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.all_beds = total
        homestay.available_beds = free
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)
    await edit_one_homestay(update, bot, True, homestay_id)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "input_new_work_hours")
async def input_new_work_hours(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")
    if not await require_homestay_access(update, bot, homestay_id):
        bot.clear_next_step(sender_id)
        return

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
    await edit_one_homestay(update, bot, True, homestay_id)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "input_new_description")
async def input_new_description(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")
    if not await require_homestay_access(update, bot, homestay_id):
        bot.clear_next_step(sender_id)
        return

    if not text:
        await bot.send_msg(sender_id, "⚠️ Описание не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.additional_info = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)
    await edit_one_homestay(update, bot, True, homestay_id)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get("command") == "input_new_type")
async def input_new_type(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    homestay_id = step_data.get("target_homestay")
    if not await require_homestay_access(update, bot, homestay_id):
        bot.clear_next_step(sender_id)
        return

    if not text:
        await bot.send_msg(sender_id, "⚠️ Тип пункта не может быть пустым.")
        return

    homestay = db_manager.get_homestay(id=homestay_id)
    if homestay:
        homestay.homestay_type = text
        db_manager.insert_or_update_homestay(homestay)
        bot.clear_next_step(sender_id)
    await edit_one_homestay(update, bot, True, homestay_id)

@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    msg.get("callback", {}).get("payload", {})).get("command") == "change_homestay_type")
async def change_homestay_type(update, bot):
    user = update.get('callback', {}).get('user', {})
    msg_id = update.get("callback", {}).get('body', {}).get('mid', "")
    task = safe_json_loads(update.get("callback", {}).get("payload", {}))
    homestay_id = task.get("homestay_id", -1)
    type = task.get("type", -1)
    if not await require_homestay_access(update, bot, homestay_id):
        return
    homestay = db_manager.get_homestay(id=homestay_id)
    homestay.homestay_type = type
    db_manager.insert_or_update_homestay(homestay)
    await edit_one_homestay(update, bot, False, homestay_id)



# =====================================================================
# Создание нового пункта
# =====================================================================


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "create_input_beds")
async def create_input_beds(update, bot):
    """Шаг 3: Получаем места, ищем координаты и сохраняем пункт в БД"""
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    if not await require_admin(update, bot):
        bot.clear_next_step(sender_id)
        return

    beds_text = update.get("message", {}).get("body", {}).get('text', "").strip()

    step_data = safe_json_loads(bot.get_next_step(sender_id))
    address_text = step_data.get("address")

    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, "edit_homestay")
    try:
        beds_count = int(beds_text)
    except ValueError:
        await bot.send_msg(sender_id, "⚠️ Пожалуйста, введите корректное число мест цифрами:",
                           keyboard.keyboard)
        return

    lat, lon = (0.0, 0.0)
    try:
        lat, lon, _ = coordinates_finder.get_coordinates(address_text)
    except Exception as e:
        print(f"Ошибка при первичном поиске координат: {e}")

    new_homestay = classes.Homestay(
        address=address_text,
        all_beds=beds_count,
        available_beds=beds_count,
        open_time="00:00",
        close_time="00:00",
        is_working=1,
        additional_info="Новый пункт, добавленный вручную.",
        homestay_type=0
    )

    new_homestay.latitude = lat
    new_homestay.longtitude = lon

    db_manager.insert_or_update_homestay(new_homestay)
    bot.clear_next_step(sender_id)
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button(f"Далее", button_types.callback, "edit_homestay")
    await bot.send_msg(sender_id,
                       f"✅ Пункт успешно создан!\n\n"
                       f"ID в системе: {new_homestay.id}\n"
                       f"Адрес: {address_text}\n"
                       f"Координаты: {lat}, {lon}", keyboard.keyboard)


@bot.message_handler(func=lambda msg, tp: safe_json_loads(
    bot.get_next_step(msg.get("message", {}).get("sender", {}).get("user_id", 0))).get(
    "command") == "create_input_address")
async def create_input_address(update, bot):
    """Шаг 2: Получаем адрес и запрашиваем количество мест"""
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    if not await require_admin(update, bot):
        bot.clear_next_step(sender_id)
        return

    address_text = update.get("message", {}).get("body", {}).get('text', "").strip()
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("❌ Отмена", button_types.callback, "edit_homestay")
    if not address_text:
        await bot.send_msg(sender_id, "⚠️ Адрес не может быть пустым. Введите адрес:", keyboard.keyboard)
        return

    await bot.send_msg(sender_id,
                       f"📍 Адрес записан: {address_text}\n\nШаг 2: Введите общее количество доступных спальных мест (цифрой):",
                       keyboard.keyboard)

    bot.set_next_step(sender_id, json.dumps({
        "command": "create_input_beds",
        "address": address_text
    }))

# =====================================================================
# НАЧАЛО БЛОКА: ОСНОВНЫЕ ИНТЕРФЕЙСНЫЕ МЕТОДЫ КНОПОК
# =====================================================================


@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "edit_homestay")
async def edit_user_button_pressed(update, bot, send_new = False):
    actor = await require_panel_access(update, bot)
    if not actor:
        return

    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', 0)
    all_homestays = show_all(get_in_dict=True)
    if is_manager(actor):
        all_homestays = [h for h in all_homestays if h.id == actor.id_homestay]

    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    if is_admin(actor):
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
    if is_manager(actor) and not all_homestays:
        text = "Вы не привязаны ни к одному пункту."
    elif is_manager(actor):
        text = "Ваш пункт 👇"
    else:
        text = "Добавьте новый пункт или отредактируйте существующий 👇"

    if send_new:
        await bot.send_msg(id, text, keyboard.keyboard)
    else:
        await bot.edit_msg(msg_id, text, keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp:
json.loads(msg.get("callback", {}).get("payload", "")).get("command", "") == "edit_one_homestay")
async def edit_one_homestay(update, bot, send_new = False, homestay_id = -1):
    if "callback" not in update:
        user = update.get('message', {}).get('sender', {})
    else:
        user = update.get('callback', {}).get('user', {})
        homestay_id = json.loads(update.get("callback", {}).get("payload", "")).get("homestay_id", -1)

    if not await require_homestay_access(update, bot, homestay_id):
        return

    keyboard = InlineKeyboardMarkup()
    id = user.get('user_id', 0)
    bot.clear_next_step(id)
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    homestay = get_homestay(homestay_id)
    usr = get_user(id_homestay=homestay_id)
    usr_info_homestay = ""
    if not usr:
        usr_info_homestay = "Нет менеджера"
    else:
        usr_info_homestay = usr
    keyboard.add_button("⬅️ На главную", button_types.callback, payload="load_start")
    keyboard.add_button("⬅️ К пунктам", button_types.callback, payload="edit_homestay")
    keyboard.add_button("❌ Удалить пункт", button_types.callback,payload=json.dumps(
        {"command": "remove_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("❌ Закрыть" if homestay.is_working else "✅ Открыть", button_types.callback, payload=json.dumps(
        {"command": "close_homestay", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Изменить адрес", button_types.callback, payload=json.dumps(
        {"command": "change_address", "homestay_id": homestay_id}
    ))
    keyboard.add_button("Редактировать места", button_types.callback, payload=json.dumps(
        {"command": "edit_places", "homestay_id": homestay_id}
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
    keyboard.add_button("Обновить координаты (положение на карте)", button_types.callback, payload=json.dumps(
        {"command": "update_geo_info", "homestay_id": homestay_id}
    ))
    if not send_new:
        await bot.edit_msg(msg_id, f"Информация о пункте:\n{homestay}\n\nМенеджер:\n{usr_info_homestay}", keyboard.keyboard)
    else:
        await bot.send_msg(id, f"Информация о пункте:\n{homestay}\n\nМенеджер:\n{usr_info_homestay}", keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp:
safe_json_loads(msg.get("callback", {}).get("payload", "")).get("command") in HOMESTAY_ACTIONS)
async def handle_homestay_management(update, bot):
    payload = safe_json_loads(update.get("callback", {}).get("payload", ""))
    command = payload.get("command")
    homestay_id = int(payload.get("homestay_id", 0))
    sender_id = update.get('callback', {}).get('user', {}).get('user_id', 0)

    if command in ADMIN_ONLY_COMMANDS:
        if not await require_admin(update, bot):
            return
    elif not await require_homestay_access(update, bot, homestay_id):
        return

    action_func = HOMESTAY_ACTIONS[command]
    await action_func(sender_id, homestay_id, bot, update)

@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "update_db")
async def update_db(update, bot):
    if not await require_admin(update, bot):
        return
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(msg_id, f"🔄 Обновление данных... Пожалуйста, ждите.")
    proceed_parsing()
    await edit_user_button_pressed(update, bot)
