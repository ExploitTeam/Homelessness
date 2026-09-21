from maxbot.bot_manager import bot, keyboard_to_start
import json
from database.db_manager import *
from maxbot.functions import *
from parser.parser import proceed_parsing

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
                                "command": "edit_homestay",
                                "homestay_id": i.id
                            }))
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(msg_id, f"Добавьте новый пункт или отредактируйте существующий 👇", keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp:
msg.get("callback", {}).get("payload", "") == "update_db")
async def update_db(update, bot):
    msg_id = update.get('message', {}).get('body', {}).get('mid', "")
    await bot.edit_msg(msg_id, f"🔄 Обновление данных... Пожалуйста, ждите.")
    proceed_parsing()
    await edit_user_button_pressed(update, bot)
