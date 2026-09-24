import asyncio
import threading

from database import db_manager
from maxbot.bot_manager import *
import api.http_server as http_server
import parser.parser

async def main():
    db_manager.initialize_database()
    try:
        bot.connect()
        bot.loop = asyncio.get_running_loop()
        server_thread = threading.Thread(target=http_server.start_server, daemon=True)
        server_thread.start()
        await bot.pulling()
    finally:
        await bot.close()

asyncio.run(main())