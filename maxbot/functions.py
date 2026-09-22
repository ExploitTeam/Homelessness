import os
from database.classes import *
from maxbot.maxapi import Bot
from parser.modules import *
from maxbot.inline_keyboard import *
from database.db_manager import *
from dotenv import load_dotenv
import json

load_dotenv()
ADMINS = [int(i) for i in os.getenv("MAX_ADMINS_ID", "").split(",")]

start_text = ("Привет{} 👋\n"
              "Это бот, который поможет вам найти место, где можно согреться или переночевать.\n"
              "Нажмите кнопку «Отправить геопозицию»', чтобы посмотреть ближайшие к вам ночлежки.\n"
              "Вы можете открыть мини-пиложение и ознакомиться с пунктами на карте.\n\n"
              "Ваш ID: {}.")

def show_all(name=None, get_in_dict=False):
    all = get_all_homestays()
    if name:
        all = sort_places(all, name)
    if get_in_dict:
        return all
    res = ""
    for i in all:
        res += (f"🆔 {i.id}\n"
                f"🏠 Адрес: {i.address}\n{
                f'🙅‍♂️ Занято: {i.available_beds}\n👤 Всего мест: {i.all_beds}\n' if i.all_beds > 0 else ''}"
                f"{'🟢 Работает' if i.is_working else '🔴 Не работает'}\n"
                f"⏳ Время работы: {i.open_time} - {i.close_time}\n"
                f"ℹ Дополнительная информация: {i.additional_info}\n\n")
    if not res:
        res = ("Сейчас доступных точек нет(\n"
               "Зайдите немного позже, возможно, ситуация изменится.")
    return res

def generate_buttons_by_user_privilege(usr, msg_id, me, no_edit=False):
    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("Изменить номер", button_types.callback, payload=json.dumps({
        "command": "change_number",
        "user": usr.id,
        "msg_id": msg_id
    }))
    if no_edit:
        return keyboard

    if usr.user_type != 2 and usr.id != me and usr.id not in ADMINS:
        keyboard.add_button("Сделать админом", button_types.callback, payload=json.dumps({
            "command": "set_admin",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type != 1 and usr.id != me and usr.id not in ADMINS:
        keyboard.add_button("Сделать менеджером", button_types.callback, payload=json.dumps({
            "command": "set_manager",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type != 0 and usr.id != me and usr.id not in ADMINS:
        keyboard.add_button("Отнять привилегии", button_types.callback, payload=json.dumps({
            "command": "restrict_user",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type in [1, 2]:
        keyboard.add_button("Привязать к пункту", button_types.callback, payload=json.dumps({
            "command": "attach_to_point",
            "user": usr.id,
            "msg_id": msg_id
        }))
    return keyboard


async def do_on_start(bot, usr, msg_id = None):
    global start_text
    name = usr.get('first_name', None)
    id = usr.get('user_id', None)
    keyboard = InlineKeyboardMarkup()
    usr = get_user(id)
    if not usr:
        usr = User(id, name, 0, "", -1)
        insert_or_update_user(usr)

    if id in ADMINS or usr.user_type == 2:
        keyboard.add_button("Редактировать пользователя", button_types.callback, payload="edit_user")
        keyboard.add_button("Редактировать пункт помощи", button_types.callback, payload="edit_homestay")
    if name:
        name = f", {name}"
        text = start_text.format(name, id)
    else:
        text = start_text.format("", id)

    keyboard.add_button("Отправить геопозицию", button_types.request_geo_location, payload="send_geo")
    if msg_id:
        await bot.edit_msg(msg_id, text, keyboard.keyboard)
    else:
        msg_id = (await bot.send_msg(id, text, keyboard.keyboard)).get('message', {}).get('body', {}).get('mid')
        bot.set_next_step(id,
                          json.dumps({
                              "command" : "edit_homestay",
                              "msg_id" : msg_id
                          }))

    print(text)

def safe_json_loads(string_data):
    if not string_data:
        return {}
    try:
        return json.loads(string_data)
    except (ValueError, TypeError):
        return {}