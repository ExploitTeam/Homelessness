import asyncio
import ssl
import warnings
import aiohttp
from maxbot.exceptions_max import *

class Bot:
    api_url = "https://platform-api2.max.ru"
    def __init__(self, token):
        self.text_handlers = []
        self.command_handlers = {}
        self.token = token
        self.session = None
        self.ssl_context = ssl.create_default_context(cafile="maxbot/Russian_Trusted_CA.pem")
        self.next_step = {}

    def connect(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": self.token,
                     "Content-Type": "application/json",},
        )

    async def _send_single(self, chat_id: int, text: str, btns=None):
        body = {'text': text,
                'attachments': [{'type': 'inline_keyboard',
                                 'payload': {'buttons': btns}}] if btns else []}
        async with self.session.post(f'{self.api_url}/messages',
                                     params={'user_id':chat_id},json=body,
                                     ssl=self.ssl_context) as response:
            data=await response.json()
            if response.status != 200:
                raise ConnectionMaxError(f'Error while sending message. Code: {response.status}')
            return data

    async def send_msg(self, chat_id: int, text: str, btns=None):
        """Совместимо с API: его первое уведомление о новой заявке дублируется
        ОСТАЛЬНЫМ менеджерам пункта (без правок api/http_server.py).
        """
        extra=[]
        if btns and text.startswith('Новая заявка!'):
            import json
            from database.db_manager import get_booking, get_homestay_managers
            for row in btns:
                for button in row:
                    try:
                        payload=json.loads(button.get('payload') or '{}')
                    except (ValueError,TypeError):
                        continue
                    if payload.get('command') != 'approve_booking':
                        continue
                    booking=get_booking(id=payload.get('booking_id'))
                    if booking:
                        extra=[m.id for m in get_homestay_managers(booking.homestay_id)
                               if m.id != chat_id]
                    break
        result=None
        first_error=None
        try:
            result=await self._send_single(chat_id,text,btns)
        except Exception as error:
            first_error=error
        # Уведомление всем менеджерам, независимо от ошибки доставки первому.
        if extra:
            results=await asyncio.gather(*(self._send_single(uid,text,btns) for uid in extra),
                                         return_exceptions=True)
            for uid,status in zip(extra,results):
                if isinstance(status,Exception):
                    warnings.warn(f'Booking manager notification failed for {uid}: {status}')
        if first_error:
            raise first_error
        return result

    async def edit_msg(self, message_id : int, text : str, btns: list = []):
        """Send a message to chat"""

        body = {'text': text,
                  'attachments': [
                      {
                          "type": "inline_keyboard",
                          "payload": {
                              "buttons": btns
                          }
                      }
                  ] if btns else []}
        print(body)
        async with self.session.put(
            f'{self.api_url}/messages',
            params={'message_id': message_id},
            json=body,
            ssl=self.ssl_context,
        ) as response:
            data = await response.json()
            if response.status != 200:
                raise ConnectionMaxError(f"Error while sending message. Code: {response.status}")
            return data

    def message_handler(self, commands=None, func=None):
        def decorator(handler_func):
            if commands:
                for cmd in commands:
                    cmd_name = cmd.lstrip('/')
                    self.command_handlers[cmd_name] = handler_func
            elif func:
                self.text_handlers.append((func, handler_func))
            else:
                self.text_handlers.append((lambda msg, _: True, handler_func))
            return handler_func

        return decorator

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

    async def _route_update(self, update):
        tp = update.get("update_type")
        #print(tp)
        message = update.get("message", {})

        if tp == "message_created":
            text = message.get("body", {}).get("text", "").strip()
            if text and text.startswith('/'):
                command = text.split()[0][1:]
                if command in self.command_handlers:
                    await self.command_handlers[command](update, self)
                    return

        for filter_func, handler_func in self.text_handlers:
            try:
                if filter_func(update, tp):
                    await handler_func(update, self)
            except Exception as filter_err:
                print(f"Ошибка в фильтре: {filter_err}")
                continue
        print(tp, update)

    async def pulling(self):
        """Cycle for getting events (messages)"""
        print("Bot started.")
        while True:
            try:
                updates = await self.__get_updates()
                for upd in updates.get("updates", []):
                    await self._route_update(upd)
            except Exception as e:
                warnings.warn(f"ERROR WHILE PULLING: {e}")
                await asyncio.sleep(2)

    def set_next_step(self, id, step):
        self.next_step[id] = step

    def get_next_step(self, id):
        try:
            id = int(id)
        except ValueError:
            pass
        if id in self.next_step:
            return self.next_step[id]
        return ""

    def clear_next_step(self, id):
        try:
            id = int(id)
        except ValueError:
            pass

        if id in self.next_step:
            del self.next_step[id]

    async def close(self):
        if self.session:
            await self.session.close()

