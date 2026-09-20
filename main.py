import asyncio
from database import db_manager
from maxbot.bot_manager import *


async def main():
    db_manager.initialize_database()
    try:
        bot.connect()
        await bot.pulling()
    finally:
        await bot.close()

asyncio.run(main())