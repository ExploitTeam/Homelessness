import threading
import sys
from database import db_manager
from maxbot.bot_manager import *
import api.http_server as http_server
import parser.parser
import os
import dotenv
import asyncio
from datetime import datetime, timedelta, timezone
from database.db_manager import get_all_bookings, delete_booking, get_homestay, insert_or_update_homestay
load_dotenv()

CLEAN_EVERY = timedelta(hours=int(os.getenv("CLEAN_EVERY", 1)))
UNAPPROVED_TTL = timedelta(minutes=int(os.getenv("UNAPPROVED_TTL", 1)))
APPROVED_TTL = timedelta(hours=int(os.getenv("APPROVED_TTL", 0)))


def _booking_age(booking):
    if not booking.date_time:
        return None
    created = datetime.fromisoformat(booking.date_time)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created


def _should_delete(booking) -> bool:
    age = _booking_age(booking)
    if age is None:
        return False
    if age >= APPROVED_TTL:
        return True
    if not booking.is_approved and age >= UNAPPROVED_TTL:
        return True
    return False

def _should_restore_bed(booking):
    age = _booking_age(booking)
    if not booking.is_approved and age >= UNAPPROVED_TTL:
        return True
    return False

def _restore_bed(booking):
    homestay = get_homestay(id=booking.homestay_id)
    if not homestay:
        return
    homestay.available_beds = (homestay.available_beds or 0) + 1
    insert_or_update_homestay(homestay)


async def cleanup_bookings_loop():
    await asyncio.sleep(5)
    while True:
        try:
            bookings = get_all_bookings() or []
            for booking in bookings:
                if not _should_delete(booking):
                    continue
                if _should_restore_bed(booking):
                    _restore_bed(booking)
                    try:
                        from maxbot.bot_manager import bot
                        await bot.send_msg(booking.user_id, f"❗️ Ваша бронь была автоматически удалена, "
                                                            f"так как менеджер ее не подтвердил.\n"
                                                            f"Информация о брони:\n"
                                                            f"{booking}")
                    except Exception as e:
                        print(f"Ошибка отправки уведомления: {e}")
                delete_booking(booking)
                print(f"Удалена бронь #{getattr(booking, 'id', '?')}")
            await asyncio.sleep(CLEAN_EVERY.total_seconds())
        except Exception as error:
            print("cleanup_bookings_loop:", error)
            await asyncio.sleep(5)



async def main():
    db_manager.initialize_database()
    try:
        bot.connect()
        bot.loop = asyncio.get_running_loop()
        server_thread = threading.Thread(target=http_server.start_server, daemon=True)
        server_thread.start()
        asyncio.create_task(cleanup_bookings_loop())
        await bot.pulling()
    finally:
        await bot.close()

asyncio.run(main())