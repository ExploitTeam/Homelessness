import asyncio
import ssl
import warnings
import aiohttp
from exceptions_max import *

class Bot:
    api_url = "https://platform-api2.max.ru"
    def __init__(self, token):
        self.token = token
        self.session = None
        self.ssl_context = ssl.create_default_context(cafile="Russian_Trusted_CA.pem")

    def connect(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": self.token,
                     "Content-Type": "application/json",},
        )

    async def send_msg(self, chat_id : int, text : str):
        """Send a message to chat"""

        async with self.session.post(
            f'{self.api_url}/messages',
            params={'chat_id': chat_id},
            json={'text': text},
            ssl=self.ssl_context,
        ) as response:
            data = await response.json()
            if response.status != 200:
                raise ConnectionMaxError(f"Error while sending message. Code: {response.status}")
            return data

    async def __get_updates(self, timeout=10):
        """GET NEW EVENTS"""

        async with self.session.get(
                f"{self.api_url}/updates",
                params={"timeout": timeout},
                ssl=self.ssl_context) as response:
            data = await response.json()
            if response.status != 200:
                raise ConnectionMaxError(f"Error while getting updates. Code: {response.status}")
            return data

    async def pulling(self, handler):
        """Cycle for getting events (messages)"""
        print("Bot started.")
        while True:
            try:
                updates = await self.__get_updates()
                for upd in updates.get("updates", []):
                    await handler(upd)
            except Exception as e:
                warnings.warn(f"ERROR WHILE PULLING: {e}")
                await asyncio.sleep(2)

    async def close(self):
        if self.session:
            await self.session.close()