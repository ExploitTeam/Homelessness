import asyncio
from inline_keyboard import *
from maxbot.maxapi import Bot
import os
from dotenv import load_dotenv
from database.db_manager import *
from parser.modules import *
load_dotenv()
TOKEN = os.getenv("MAX_TOKEN", "")
bot = Bot(TOKEN)
start_text = ("Привет{} 👋\n"
              "Это бот, который поможет вам найти место, где можно согреться или переночевать.\n"
              "Нажмите кнопку 'Отправить геопозицию', чтобы посмотреть ближайшие к вам ночлежки.")

@bot.message_handler(commands=['start'])
async def only_start(update):
    user = update.get('message', {}).get('sender', {})
    name = user.get('first_name', {})
    id = user.get('user_id', {})
    if name:
        name = f", {name}"
        text = start_text.format(name)
    else:
        text = start_text
    print(text)

    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("Отправить геопозицию", button_types.request_geo_location, payload="send_geo")
    keyboard.add_button("Открыть мини приложение", button_types.callback, payload="open_mini_app")
    await bot.send_msg(id, text, keyboard.keyboard)

@bot.message_handler(func=lambda msg, tp: tp == "bot_started")
async def on_start(update):
    name = update.get('user', {}).get('first_name', None)
    id = update.get('user', {}).get('user_id', None)
    if name:
        name = f", {name}"
        text = start_text.format(name)
    else:
        text = start_text

    keyboard = InlineKeyboardMarkup()
    keyboard.add_button("Отправить геопозицию", button_types.request_geo_location, payload="send_geo")
    keyboard.add_button("Открыть мини приложение", button_types.callback, payload="open_mini_app")
    await bot.send_msg(id, text, keyboard.keyboard)
    print(text)

@bot.message_handler(func=lambda msg, tp: tp == "bot_stopped")
async def on_stop(update):
    print("BOT DELETED! INFO: ", update)

@bot.message_handler(func=lambda msg, tp:
(len(msg.get('message', {}).get('body', {}).get('attachments', [])) > 0 and
                     msg.get('message', {}).get('body', {}).get('attachments', [])[0]['type'] == 'location'))
async def on_sending_geo(update):
    user =  update.get('message', {}).get('sender', {})
    name = user.get('first_name', "")
    id = user.get('user_id', 0)
    if id:
        all = get_all_homestays()
        sort = sort_places(all, name)
        res = ""
        for i in sort:
            res += (f"🏠 Адрес: {i.address}\n🙅‍♂️ Занято: {i.current}\n👤 Всего мест: {i.max_people}\n"
                    f"{'🟢 Работает' if i.is_open else '🔴 Не работает'}\n"
                    f"⏳ Время работы: {i.time_work}\n\n")
        if not res:
            res = ("Сейчас доступных точек нет(\n"
                   "Зайдите немного позже, возможно, ситуация изменится.")
        keyboard = InlineKeyboardMarkup()
        keyboard.add_button("Смотреть на карте", button_types.callback, payload="open_mini_app")
        await bot.send_msg(id, f"Доступные точки (от самой близкой до дальней):\n{res}", keyboard.keyboard)

async def main():

    try:
        bot.connect()
        await bot.pulling()
    finally:
        await bot.close()

asyncio.run(main())