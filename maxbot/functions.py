import os
from database.classes import *
from maxbot.maxapi import Bot
from maxbot.inline_keyboard import *
from database.db_manager import *
from database import access
from dotenv import load_dotenv
import json

load_dotenv()
ADMINS = access.global_admin_ids()

start_text = ("Привет{} 👋\n"
              "Здесь можно найти бесплатную еду, ночлег, душ, одежду и другую помощь.\n\n"
              "Отправьте геопозицию, чтобы посмотреть ближайшие пункты. "
              "Категории можно выбрать в списке. "
              "Также доступно мини-приложение с картой пунктов.\n\n"
              "Ваш MAX ID: {}.")


def show_all(name=None, get_in_dict=False):
    points = get_all_homestays()
    if get_in_dict:
        return points
    if not points:
        return "Пока нет доступных пунктов помощи."
    return "\n\n".join(
        f"🆔 {p.id}\n📍 {p.address}\n"
        f"🏠 Мест: {p.available_beds}/{p.all_beds}\n"
        f"{'🟢 Работает' if p.is_working else '🔴 Не работает'}"
        for p in points
    )


def generate_buttons_by_user_privilege(usr, msg_id, me, no_edit=False):
    # Совместимость с прежними вызовами.
    from maxbot.user_settings import profile_keyboard
    return profile_keyboard(get_user(id=me),usr)


async def do_on_start(bot, usr, msg_id=None):
    user_id=usr.get('user_id')
    if not user_id:
        return
    name=usr.get('first_name') or ''
    account=get_user(id=user_id)
    if not account:
        account=User(id=user_id,username=name,user_type=0)
        insert_or_update_user(account)
    elif name and name!=account.username:
        account.username=name
        insert_or_update_user(account)
    kb=InlineKeyboardMarkup()
    kb.add_button('📍 Отправить геопозицию',button_types.request_geo_location,payload='send_geo')
    kb.add_button('📋 Мои бронирования',button_types.callback,payload='my_bookings')
    kb.add_button('🕘 История моих броней',button_types.callback,payload='my_booking_history')
    kb.add_button('👤 Мой профиль' if account.user_type==0 else '👥 Пользователи / профиль',
                  button_types.callback,payload='edit_user')
    if access.is_global(account) or account.user_type==access.FUND_ADMIN:
        kb.add_button('🏛️ Фонды',button_types.callback,payload='funds_panel')
    if access.is_global(account) or account.user_type in (access.MANAGER,access.FUND_ADMIN):
        kb.add_button('🏠 Управление пунктами',button_types.callback,payload='edit_homestay')
        kb.add_button('✅ Управление бронированиями',button_types.callback,payload='manage_bookings')
    text=start_text.format(f', {name}' if name else '',user_id)
    if msg_id:
        await bot.edit_msg(msg_id,text,kb.keyboard)
    else:
        await bot.send_msg(user_id,text,kb.keyboard)



def safe_json_loads(string_data):
    if not string_data:
        return {}
    try:
        return json.loads(string_data)
    except (ValueError, TypeError):
        return {}

#=================================
# Работа со временем
#=================================


from datetime import datetime, time


def parse_hhmm(value: str) -> time:
    return datetime.strptime(value.strip(), "%H:%M").time()


def is_point_open(open_str: str, close_str: str, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    current = now.time()

    opens_at = parse_hhmm(open_str)
    closes_at = parse_hhmm(close_str)

    if opens_at <= closes_at:
        return opens_at <= current < closes_at

    return current >= opens_at or current < closes_at
