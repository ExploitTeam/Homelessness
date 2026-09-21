from maxbot.bot_manager import bot, keyboard_to_start
import json
from database.db_manager import *
from maxbot.functions import *
"""user settings"""



@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "edit_user")
async def edit_user_button_pressed(update, bot):
    user = update.get('callback', {}).get('user', {})
    id = user.get('user_id', {})
    bot.set_next_step(id, "set_user_for_edit")
    await bot.send_msg(id, f"Введите ID пользователя для редактирования. ID видно в этом боте в главном меню.")


@bot.message_handler(func=lambda msg, tp:
bot.get_next_step(
    msg.get("message", {}).get("sender", {}).get("user_id", 0)) == "set_user_for_edit")
async def set_user_for_edit(update, bot):
    user = update.get('message', {}).get('sender', {})
    text = update.get('message', {}).get('body', {}).get('text', "")
    id = user.get('user_id', {})
    try:
        text = int(text)
    except ValueError:
        await bot.send_msg(id, f"Ошибка ввода")
        return

    usr = get_user(text)
    if not usr:
        await bot.send_msg(id, "Не удалось найти такого пользователя. Попробуйте еще раз.")
        return

    res = await bot.send_msg(id, f"Информация о пользователе:\n{usr}")
    keyboard = InlineKeyboardMarkup()
    if usr.id == id:
        keyboard = generate_buttons_by_user_privilege(usr, res.get('message', {}).get('body', {}).get('mid'), no_edit=True)
    keyboard.add_button("На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(res.get('message', {}).get('body', {}).get('mid'),
                       f"Информация о пользователе:\n{usr}",
                       keyboard.keyboard)


"""Set user as [manager, admin, user]"""


@bot.message_handler(func=lambda msg, tp:
json.loads(msg.get("callback", {}).get("payload", "")
           )["command"] in ["set_admin", "set_manager", "restrict_user"])
async def set_manager(update, bot):
    current_task = update.get("callback", {}).get("payload", "")
    if not current_task:
        return
    current_task = json.loads(current_task)
    usr_id = int(current_task.get("user", 0))
    msg_id = current_task.get("msg_id", "")
    usr = get_user(usr_id)
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
json.loads(msg.get("callback", {}).get("payload", "")
           )["command"] == "attach_to_point")
async def attach_to_point(update, bot):
    sender_id = update.get('callback', {}).get('user', {}).get('user_id', 0)
    current_task = update.get("callback", {}).get("payload", "")
    if not current_task:
        return
    current_task = json.loads(current_task)
    id_usr = int(current_task.get("user", 0))
    await bot.send_msg(sender_id, f"К какому пункту привязать пользователя?\n"
                                  f"Список всех доступных пунктов:\n{show_all()}", keyboard_to_start.keyboard)
    bot.set_next_step(sender_id, json.dumps({
        "command": "input_point_to_attach",
        "target_user": id_usr
    }))


@bot.message_handler(func=lambda msg, tp:
json.loads(
    bot.get_next_step(
        msg.get("message", {}).get("sender", {}).get("user_id", 0)
    )
)["command"] == "input_point_to_attach")
async def input_point_to_attach(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    target_user = json.loads(
        bot.get_next_step(
            update.get("message", {}).get("sender", {}).get("user_id", 0)
        )
    )["target_user"]
    text = update.get("message", {}).get("body", {}).get('text', "")
    if not text:
        return
    try:
        text = int(text)
    except ValueError:
        await bot.send_msg(sender_id, f"Ошибка ввода. ")
        return
    homestay = get_homestay(id=text)
    if not homestay:
        await bot.send_msg(sender_id, f"Не удалось найти пункт с индексом {text}")
        return
    usr = get_user(id=target_user)
    usr.id_homestay = text
    insert_or_update_user(usr)
    res = await bot.send_msg(sender_id, f".")
    keyboard = generate_buttons_by_user_privilege(usr, res.get('message', {}).get('body', {}).get('mid'))
    keyboard.add_button("На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(res.get('message', {}).get('body', {}).get('mid'),
                       f"Даныые пользователя успешно обновлены!\n{usr}",
                       keyboard.keyboard)
    bot.clear_next_step(sender_id)


"""Set phone number"""


@bot.message_handler(func=lambda msg, tp:
json.loads(msg.get("callback", {}).get("payload", "")
           )["command"] == "change_number")
async def edit_number(update, bot):
    sender_id = update.get('callback', {}).get('user', {}).get('user_id', 0)
    current_task = update.get("callback", {}).get("payload", "")
    current_task = json.loads(current_task)
    id_usr = int(current_task.get("user", 0))
    await bot.send_msg(sender_id, f"Укажите номер телефона ниже:\n")
    bot.set_next_step(sender_id, json.dumps({
        "command": "input_new_number",
        "target_user": id_usr
    }))


@bot.message_handler(func=lambda msg, tp:
json.loads(
    bot.get_next_step(
        msg.get("message", {}).get("sender", {}).get("user_id", 0)
    )
)["command"] == "input_new_number")
async def input_new_number(update, bot):
    sender_id = update.get('message', {}).get('sender', {}).get('user_id', 0)
    target_user = json.loads(
        bot.get_next_step(
            update.get("message", {}).get("sender", {}).get("user_id", 0)
        )
    )["target_user"]
    text = update.get("message", {}).get("body", {}).get('text', "")
    if not text:
        return
    usr = get_user(id=target_user)
    usr.phone_number = text
    insert_or_update_user(usr)
    res = await bot.send_msg(sender_id, f".")
    keyboard = generate_buttons_by_user_privilege(usr, res.get('message', {}).get('body', {}).get('mid'))
    keyboard.add_button("На главную", button_types.callback, payload="load_start")
    await bot.edit_msg(res.get('message', {}).get('body', {}).get('mid'),
                       f"Даныые пользователя успешно обновлены!\n{usr}",
                       keyboard.keyboard)
    bot.clear_next_step(sender_id)
