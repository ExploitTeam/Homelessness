import asyncio
from database import db_manager
from maxbot import inline_keyboard
from maxbot.inline_keyboard import *
from maxbot.maxapi import Bot
import os
from dotenv import load_dotenv
from database.db_manager import *
from parser.modules import *
load_dotenv()

TOKEN = os.getenv("MAX_TOKEN", "")
ADMINS = [int(i) for i in os.getenv("MAX_ADMINS_ID", "").split(",")]
bot = Bot(TOKEN)
start_text = ("Привет{} 👋\n"
              "Это бот, который поможет вам найти место, где можно согреться или переночевать.\n"
              "Нажмите кнопку 'Отправить геопозицию', чтобы посмотреть ближайшие к вам ночлежки.\n\n"
              "Ваш ID: {}.")

keyboard_to_start = InlineKeyboardMarkup()
keyboard_to_start.add_button("На главную", button_types.callback, payload="load_start")

async def do_on_start(usr):
    global start_text
    name = usr.get('first_name', None)
    id = usr.get('user_id', None)
    keyboard = InlineKeyboardMarkup()
    usr = get_user(id)
    if not usr:
        usr = User(id, name, 0, "", -1)
        insert_or_update_user(usr)

    if id in ADMINS or usr.user_type == 2:
        keyboard.add_button("Добавить менеджера", button_types.callback, payload="set_manager")
        keyboard.add_button("Добавить администратора", button_types.callback, payload="set_admin")
        keyboard.add_button("Сделать обычным пользователем", button_types.callback, payload="restrict_user")
    if name:
        name = f", {name}"
        text = start_text.format(name, id)
    else:
        text = start_text.format("", id)

    keyboard.add_button("Отправить геопозицию", button_types.request_geo_location, payload="send_geo")
    keyboard.add_button("Открыть мини приложение", button_types.callback, payload="open_mini_app")
    await bot.send_msg(id, text, keyboard.keyboard)
    print(text)

@bot.message_handler(commands=['start'])
async def only_start(update):
    user = update.get('message', {}).get('sender', {})
    await do_on_start(user)

@bot.message_handler(func=lambda msg, tp: tp == "bot_started")
async def on_start(update):
    await do_on_start(update.get('user', {}))

@bot.message_handler(func=lambda msg, tp:
                     msg.get("callback", {}).get("payload", "") == "load_start")
async def to_start(update):
    bot.clear_next_step(update.get("callback", {}).get("user", {}).get("user_id", 0))
    await do_on_start(update.get("callback", {}).get("user", {}))

"""Set user as manager"""

@bot.message_handler(func=lambda msg, tp:
                    msg.get("callback", {}).get("payload", "") == "set_manager" or
                    msg.get("callback", {}).get("payload", "") == "set_admin")
async def set_manager_or_admin(update):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    bot.set_next_step(id, update.get('callback', {}).get("payload", ""))
    await bot.send_msg(id, f"Пожалуйста, отправьте в чат id менеджера. ID отображается при запуске бота.",
                       keyboard_to_start.keyboard)

@bot.message_handler(func=lambda msg, tp:
                    bot.get_next_step(
                        msg.get("message", {}).get("sender", {}).get("user_id", 0))
                        .startswith("set_homestay_for_manager_"))
async def set_manager(update):
    user = update.get('message', {}).get('sender', {})
    id = user.get('user_id', {})
    id_homestay =  update.get('message', {}).get('body', {}).get('text', 0)
    id_manager = bot.get_next_step(id).replace("set_homestay_for_manager_", "")
    try:
        id_homestay = int(id_homestay)
    except ValueError:
        await bot.send_msg(id, f"Неверный ввод. ", keyboard_to_start.keyboard)
        return
    homestay = get_homestay(id_homestay)
    if not homestay:
        await bot.send_msg(id, f"Не удалось найти это место.", keyboard_to_start.keyboard)
        bot.clear_next_step(id)
        return
    usr = get_user(id_manager)
    usr.id_homestay = id_homestay
    insert_or_update_user(usr)
    await bot.send_msg(id, f"Настройки изменены!\n\n{usr}", keyboard_to_start.keyboard)

@bot.message_handler(func=lambda msg, tp:
                    bot.get_next_step(
                        msg.get("message", {}).get("sender", {}).get("user_id", 0)) == "set_manager" or
                    bot.get_next_step(
                        msg.get("message", {}).get("sender", {}).get("user_id", 0)) == "set_admin"
                     )
async def set_manager_or_admin(update):
    user = update.get('message', {}).get('sender', {})
    id = user.get('user_id', {})
    s = ""
    id_manager =  update.get('message', {}).get('body', {}).get('text', 0)
    try:
        id_manager = int(id_manager)
    except ValueError:
        await bot.send_msg(id, "Неверный ввод.", keyboard_to_start.keyboard)
        return
    usr = get_user(id)
    if not usr:
        await bot.send_msg(id, "Такой пользователь не найден.", keyboard_to_start.keyboard)
        bot.clear_next_step(id)
        return
    usr.user_type = 1 if bot.get_next_step(id) == "set_manager" else 2
    insert_or_update_user(usr)
    if usr.user_type == 2:
        await bot.send_msg(id, f"Настройки изменены!\n\n{usr}", keyboard_to_start.keyboard)
        bot.clear_next_step(id)
        return

    await bot.send_msg(id, f"К какому пункту привязать пользователя?\n"
                           f"Список всех доступных пунктов:\n{show_all()}", keyboard_to_start.keyboard)
    bot.set_next_step(id, f"set_homestay_for_manager_{id_manager}")


"""restriction user"""

@bot.message_handler(func=lambda msg, tp:
                    msg.get("callback", {}).get("payload", "") == "restrict_user")
async def set_manager_or_admin(update):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    bot.set_next_step(id, update.get('callback', {}).get("payload", ""))
    await bot.send_msg(id, f"Пожалуйста, отправьте в чат id пользователя. ID отображается при запуске бота.")

@bot.message_handler(func=lambda msg, tp:
                    bot.get_next_step(
                        msg.get("message", {}).get("sender", {}).get("user_id", 0)) == "restrict_user")
async def set_manager_or_admin(update):
    user = update.get('message', {}).get('sender', {})
    id = user.get('user_id', {})
    id_manager =  update.get('message', {}).get('body', {}).get('text', 0)
    try:
        id_manager = int(id_manager)
    except ValueError:
        await bot.send_msg(id, "Неверный ввод.", keyboard_to_start.keyboard)
        return
    usr = get_user(id)
    if not usr:
        await bot.send_msg(id, "Такой пользователь не найден.", keyboard_to_start.keyboard)
        bot.clear_next_step(id)
        return
    usr.user_type = 0
    insert_or_update_user(usr)
    await bot.send_msg(id, f"Настройки изменены!\n\n{usr}", keyboard_to_start.keyboard)
    bot.clear_next_step(id)

"""On sending location"""

@bot.message_handler(func=lambda msg, tp:
                    (len(msg.get('message', {}).get('body', {}).get('attachments', [])) > 0 and
                     msg.get('message', {}).get('body', {}).get('attachments', [])[0]['type'] == 'location'))
async def on_sending_geo(update):
    user =  update.get('message', {}).get('sender', {})
    name = user.get('first_name', "")
    id = user.get('user_id', 0)

    if id:
        res = show_all(name)
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button("Смотреть на карте", button_types.callback, payload="open_mini_app")
        keyboard.add_button("На главную", button_types.callback, payload="load_start")
        await bot.send_msg(id, f"Доступные точки (от самой близкой до дальней):\n{res}", keyboard.keyboard)

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
