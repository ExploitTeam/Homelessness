import json

from maxbot.functions import *
from maxbot.inline_keyboard import *
from maxbot.maxapi import Bot
import os
from dotenv import load_dotenv
from database.db_manager import *


load_dotenv()

TOKEN = os.getenv("MAX_TOKEN", "")
ADMINS = [int(i) for i in os.getenv("MAX_ADMINS_ID", "").split(",")]
bot = Bot(TOKEN)

keyboard_to_start = InlineKeyboardMarkup()
keyboard_to_start.add_button("На главную", button_types.callback, payload="load_start")

from maxbot.user_settings import *
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
    await do_on_start(bot, update.get("callback", {}).get("user", {}))



"""On sending location"""


@bot.message_handler(func=lambda msg, tp:
(len(msg.get('message', {}).get('body', {}).get('attachments', [])) > 0 and
 msg.get('message', {}).get('body', {}).get('attachments', [])[0]['type'] == 'location'))
async def on_sending_geo(update, bot):
    user = update.get('message', {}).get('sender', {})
    name = user.get('first_name', "")
    id = user.get('user_id', 0)

    if id:
        res = show_all(name)
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button("Смотреть на карте", button_types.callback, payload="open_mini_app")
        keyboard.add_button("На главную", button_types.callback, payload="load_start")
        await bot.send_msg(id, f"Доступные точки (от самой близкой до дальней):\n{res}", keyboard.keyboard)
