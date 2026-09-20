import os

from database.classes import *
from parser.modules import *
from maxbot.inline_keyboard import *
from database.db_manager import *
from dotenv import load_dotenv
import json
load_dotenv()
ADMINS = [int(i) for i in os.getenv("MAX_ADMINS_ID", "").split(",")]
def show_all(name=None):
    # all = get_all_homestays() --- ОПИСАТЬ В db_manager.py!!!!!
    all = [ # ПРИМЕР НА ВРЕМЯ ОТСУТСТВИЯ РЕАЛЬНОЙ ИНФЫ. УБРАТЬ!
        Homestay(1, "Улица Пушкина 1", 20, 5, "9:00", "20:00",
                 1, "Пункт для ночлежки"),
        Homestay(2, "Улица Ленина 5", -1, -1, "9:00", "20:00",
                 1, "Пункт бесплатной еды")
    ]
    if name:
        all = sort_places(all, name)
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

def generate_buttons_by_user_privilege(usr, msg_id):
    keyboard = InlineKeyboardMarkup()
    if usr.user_type != 2:
        keyboard.add_button("Сделать админом", button_types.callback, payload=json.dumps({
            "command": "set_admin",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type != 1:
        keyboard.add_button("Сделать менеджером", button_types.callback, payload=json.dumps({
            "command": "set_manager",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type != 0:
        keyboard.add_button("Отнять привилегии", button_types.callback, payload=json.dumps({
            "command": "restrict_user",
            "user": usr.id,
            "msg_id": msg_id
        }))
    if usr.user_type == 1:
        keyboard.add_button("Привязать к пункту", button_types.callback, payload=json.dumps({
            "command": "attach_to_point",
            "user": usr.id,
            "msg_id": msg_id
        }))
    return keyboard


async def do_on_start(bot, usr):
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
    keyboard.add_button("Открыть мини приложение", button_types.callback, payload="open_mini_app")
    await bot.send_msg(id, text, keyboard.keyboard)
    print(text)