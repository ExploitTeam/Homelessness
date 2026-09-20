from maxbot.module import *
from maxbot.inline_keyboard import *
from maxbot.maxapi import Bot
import os
from dotenv import load_dotenv
from database.db_manager import *
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

@bot.message_handler(commands=['start'])
async def only_start(update):
    user = update.get('message', {}).get('sender', {})
    await do_on_start(bot, user)

@bot.message_handler(func=lambda msg, tp: tp == "bot_started")
async def on_start(update):
    await do_on_start(bot, update.get('user', {}))

@bot.message_handler(func=lambda msg, tp:
                     msg.get("callback", {}).get("payload", "") == "load_start")
async def to_start(update):
    bot.clear_next_step(update.get("callback", {}).get("user", {}).get("user_id", 0))
    await do_on_start(bot, update.get("callback", {}).get("user", {}))

"""user settings"""

@bot.message_handler(func=lambda msg, tp:
                    msg.get("callback", {}).get("payload", "") == "edit_user")
async def edit_user_button_pressed(update):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    bot.set_next_step(id, "set_user_for_edit")
    await bot.send_msg(id, f"Введите ID пользователя для редактирования. ID видно в этом боте в главном меню.")

@bot.message_handler(func=lambda msg, tp:
                    bot.get_next_step(
                        msg.get("message", {}).get("sender", {}).get("user_id", 0)) == "set_user_for_edit")
async def set_user_for_edit(update):
    user = update.get('message', {}).get('sender', {})
    text = update.get('message', {}).get('body', {}).get('text', "")
    id = user.get('user_id', {})
    try:
        text = int(text)
    except ValueError:
        await bot.send_msg(id, f"Ошибка ввода", keyboard_to_start.keyboard)
        return

    usr = get_user(text)
    if not usr:
        await bot.send_msg(id, "Не удалось найти такого пользователя. Попробуйте еще раз.",
                           keyboard_to_start.keyboard)
        return

    res = await bot.send_msg(id, f"Информация о пользователе:\n{usr}")
    keyboard = generate_buttons_by_user_privilege(usr, res.get('message', {}).get('body', {}).get('mid'))
    keyboard.add_button("На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(res.get('message', {}).get('body', {}).get('mid'),
                       f"Информация о пользователе:\n{usr}",
                       keyboard.keyboard)

"""Set user as [manager, admin, user]"""

@bot.message_handler(func=lambda msg, tp:
                    json.loads(msg.get("callback", {}).get("payload", "")
                     )["command"] in ["set_admin", "set_manager", "restrict_user"])
async def set_manager(update):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    current_task = update.get("callback", {}).get("payload", "")
    if not current_task:
        return
    current_task = json.loads(current_task)
    usr_id = int(current_task.get("user", 0))
    msg_id = current_task.get("msg_id", "")
    usr = get_user(usr_id)
    keyboard = InlineKeyboardMarkup()
    if current_task["command"] == "set_admin":
        usr.user_type = 2
        insert_or_update_user(usr)
    if current_task["command"] == "set_manager":
        usr.user_type = 1
        insert_or_update_user(usr)
    if current_task["command"] == "restrict_user":
        usr.user_type = 0
        insert_or_update_user(usr)
    keyboard = generate_buttons_by_user_privilege(usr, msg_id)
    keyboard.add_button("На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(msg_id, f"Информация о пользователе:\n{usr}", keyboard.keyboard)

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
