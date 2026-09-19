import asyncio

from maxbot.maxapi import Bot
import os
from dotenv import load_dotenv
load_dotenv()

async def handler(update):
    print(f"New update for bot: {update}")
    if update.get("update_type") == "message_created":
        message = update["message"]
        chat_id = message["recipient"]["chat_id"]
        text = message["body"].get("text", "")
        print(f"Received message: {text} from {chat_id}")


TOKEN = os.getenv("MAX_TOKEN", "")

async def main():
    bot = Bot(TOKEN)
    try:
        bot.connect()
        await bot.pulling(handler)
    finally:
        await bot.close()

asyncio.run(main())