"""Профили и роли; все проверки выполняются повторно на сервере при каждом клике."""
import json
from maxbot.bot_manager import bot, keyboard_to_start
from maxbot.inline_keyboard import InlineKeyboardMarkup, button_types
from maxbot.functions import safe_json_loads
from database import db_manager as db
from database import access
from maxbot.formatting import escape as md_escape


def _actor(update):
    data = update.get('callback', {}).get('user') or update.get('message', {}).get('sender', {})
    return db.get_user(id=data.get('user_id', 0))


def _mid(update):
    return (update.get('message', {}).get('body', {}).get('mid') or
            update.get('callback', {}).get('body', {}).get('mid'))


def can_edit_phone(actor,target):
    if not actor or not target:return False
    if actor.id==target.id or access.is_global(actor):return True
    return (actor.user_type==access.FUND_ADMIN and target.user_type==access.MANAGER
            and access.can_manage_account(actor,target))


def profile_text(actor,target):
    """ID и детали чужого аккаунта доступны только сотруднику с правами."""
    fund=db.get_fund(target.fund_id) if target.fund_id else None
    role={access.USER:'Пользователь',access.MANAGER:'Менеджер пункта',
          access.BOT_ADMIN:'Администратор бота',access.FUND_ADMIN:'Администратор фонда'}.get(target.user_type,'—')
    may_edit=access.can_manage_account(actor,target)
    own=bool(actor and actor.id==target.id)
    parts=[f'**Имя:** {md_escape(target.username or "Не указано")}',f'**Роль:** {role}']
    if fund:
        parts.append(f'**Фонд:** {md_escape(fund["name"])}')
    if own or may_edit or access.is_global(actor):
        if may_edit or access.is_global(actor):
            parts.insert(0,f'**MAX ID:** {target.id}')
        if can_edit_phone(actor,target):
            parts.append(f'**Телефон:** {md_escape(target.phone_number or "Номер телефона не указан")}')
    return '\n'.join(parts)

def profile_keyboard(actor, target):
    kb = InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню', button_types.callback, 'load_start')
    if can_edit_phone(actor,target):
        kb.add_button('📱 Изменить номер', button_types.callback,
                      json.dumps({'command': 'change_number', 'user': target.id}))
    if access.can_manage_account(actor,target):
        if access.is_global(actor):
            kb.add_button('🏛️ Назначить администратором фонда', button_types.callback,
                          json.dumps({'command':'select_admin_fund','user':target.id}))
            kb.add_button('👑 Сделать администратором бота', button_types.callback,
                          json.dumps({'command': 'set_admin', 'user': target.id}))
        if target.user_type != access.MANAGER:
            kb.add_button('👷 Назначить менеджером', button_types.callback,
                          json.dumps({'command': 'set_manager', 'user': target.id}))
        if target.user_type != access.USER:
            kb.add_button('🚫 Снять права администратора' if target.user_type == access.FUND_ADMIN
                          else '↩️ Сделать пользователем', button_types.callback,
                          json.dumps({'command': 'restrict_user', 'user': target.id}))
        if target.user_type == access.MANAGER:
            kb.add_button('📍 Управление привязками', button_types.callback,
                          json.dumps({'command': 'attach_to_point','user':target.id}))
    return kb


@bot.message_handler(func=lambda m,t: m.get('callback',{}).get('payload') == 'edit_user')
async def user_panel(update, bot):
    actor = _actor(update)
    if not actor:
        return
    if actor.user_type in (access.FUND_ADMIN, access.BOT_ADMIN) or access.is_global(actor):
        bot.set_next_step(actor.id, json.dumps({'command':'find_user'}))
        await bot.edit_msg(_mid(update), '👥 Укажите MAX ID пользователя, которого хотите найти.',
                           keyboard_to_start.keyboard)
    else:
        await bot.edit_msg(_mid(update), f'**👤 Настройки профиля**\n\n{profile_text(actor,actor)}',
                           profile_keyboard(actor,actor).keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command') == 'find_user')
async def find_user(update, bot):
    actor = _actor(update)
    if not actor or (not access.is_global(actor) and actor.user_type != access.FUND_ADMIN):
        return
    try:
        target_id = int(update['message']['body']['text'].strip())
    except (ValueError,KeyError):
        await bot.send_msg(actor.id, 'Введите числовой MAX ID.')
        return
    target = db.get_user(id=target_id)
    if not target:
        await bot.send_msg(actor.id, 'Пользователь ещё не запустил бота или не найден.')
        return
    if not (access.can_manage_account(actor,target) or actor.id == target.id or access.is_global(actor)):
        await bot.send_msg(actor.id, '⛔ Пользователь другого фонда.')
        return
    bot.clear_next_step(actor.id)
    info=profile_text(actor,target)
    await bot.send_msg(actor.id, f'**👤 Информация о пользователе**\n\n{info}',
                       profile_keyboard(actor,target).keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     in ('set_admin','set_manager','restrict_user'))
async def change_role(update, bot):
    actor = _actor(update)
    data = safe_json_loads(update['callback'].get('payload'))
    target = db.get_user(id=data.get('user'))
    if not access.can_manage_account(actor,target):
        await bot.send_msg(actor.id if actor else 0,'⛔ Недостаточно прав для смены роли.')
        return
    role = {'set_admin':access.BOT_ADMIN,'set_manager':access.MANAGER,
            'restrict_user':access.USER}[data['command']]
    if role == access.BOT_ADMIN and not access.is_global(actor):
        await bot.send_msg(actor.id,'⛔ Только администратор бота может назначать глобальных администраторов.')
        return
    if not db.set_account_role(target.id,role):
        await bot.send_msg(actor.id,'Не удалось сменить роль.')
        return
    target = db.get_user(id=target.id)
    await bot.edit_msg(_mid(update),f'✅ Роль обновлена.\n\n{profile_text(actor,target)}',
                       profile_keyboard(actor,target).keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'select_admin_fund')
async def select_admin_fund(update,bot):
    actor=_actor(update)
    target=db.get_user(id=safe_json_loads(update['callback']['payload']).get('user'))
    if not access.is_global(actor) or not access.can_manage_account(actor,target):
        await bot.send_msg(actor.id if actor else 0,'⛔ Только администратор бота назначает администраторов фондов.')
        return
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    for fund in db.get_funds():
        kb.add_button('🏛️ '+fund['name'][:38],button_types.callback,
                      json.dumps({'command':'assign_fund_admin','user':target.id,'fund':fund['id']}))
    await bot.edit_msg(_mid(update),'**Назначение администратора фонда**\n\nВыберите фонд. '
                       'Пользователь сможет управлять только его пунктами.',kb.keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'assign_fund_admin')
async def assign_fund_admin(update,bot):
    actor=_actor(update)
    data=safe_json_loads(update['callback']['payload'])
    target=db.get_user(id=data.get('user'))
    fund=db.get_fund(data.get('fund'))
    if not fund or not access.is_global(actor) or not access.can_manage_account(actor,target):
        await bot.send_msg(actor.id if actor else 0,'⛔ Доступ запрещён или фонд не найден.')
        return
    if not db.set_account_role(target.id,access.FUND_ADMIN,fund['id']):
        await bot.send_msg(actor.id,'Не удалось изменить роль.')
        return
    updated=db.get_user(id=target.id)
    await bot.edit_msg(_mid(update),'✅ Назначен администратор фонда.\n\n'+profile_text(actor,updated),
                       profile_keyboard(actor,updated).keyboard,markdown=True)

@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'attach_to_point')
async def point_link_menu(update,bot):
    actor = _actor(update)
    target = db.get_user(id=safe_json_loads(update['callback']['payload']).get('user'))
    if not access.can_manage_account(actor,target) or target.user_type != access.MANAGER:
        await bot.send_msg(actor.id if actor else 0,'⛔ Недостаточно прав.')
        return
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    points=[p for p in db.get_all_homestays() if access.can_manage_fund(actor,p.fund_id)]
    for point in points:
        linked=db.manager_has_point(target.id,point.id)
        kb.add_button(('✅ ' if linked else '➕ ') + point.address[:40],
                      button_types.callback,json.dumps({'command':'toggle_manager_link',
                                                         'user':target.id,'point':point.id}))
    await bot.edit_msg(_mid(update),f'**Пункты менеджера {md_escape(target.username or "Без имени")}**\n\n'
                        '➕ — добавить в пункт\n✅ — убрать из пункта.\n\n'
                        'Нажмите на нужный пункт.',kb.keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'toggle_manager_link')
async def toggle_manager_link(update,bot):
    actor=_actor(update)
    payload=safe_json_loads(update['callback']['payload'])
    target=db.get_user(id=payload.get('user'))
    point=db.get_homestay(id=payload.get('point'))
    if not (access.can_manage_account(actor,target) and access.can_assign_manager(actor,target,point)):
        await bot.send_msg(actor.id if actor else 0,'⛔ Нет доступа к этому фонду или пользователю.')
        return
    if db.manager_has_point(target.id,point.id):
        db.unassign_manager(point.id,target.id)
    else:
        db.assign_manager(point.id,target.id)
    await point_link_menu(update_with_payload(update,{'command':'attach_to_point','user':target.id}),bot)


def update_with_payload(update,data):
    # Новый словарь — не изменяем исходный callback обработчика.
    return {**update,'callback':{**update['callback'],'payload':json.dumps(data)}}


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'change_number')
async def change_number(update,bot):
    actor=_actor(update)
    target=db.get_user(id=safe_json_loads(update['callback']['payload']).get('user'))
    if not can_edit_phone(actor,target):
        await bot.send_msg(actor.id if actor else 0,'⛔ Недостаточно прав.')
        return
    bot.set_next_step(actor.id,json.dumps({'command':'input_new_number','user':target.id}))
    await bot.edit_msg(_mid(update),'📱 Введите новый номер телефона:',keyboard_to_start.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command') == 'input_new_number')
async def save_number(update,bot):
    actor=_actor(update)
    data=safe_json_loads(bot.get_next_step(actor.id))
    target=db.get_user(id=data.get('user'))
    if not can_edit_phone(actor,target):
        bot.clear_next_step(actor.id)
        return
    phone=update.get('message',{}).get('body',{}).get('text','').strip()
    if not phone or len(phone)>30:
        await bot.send_msg(actor.id,'Укажите номер до 30 символов.')
        return
    target.phone_number=phone
    db.insert_or_update_user(target)
    bot.clear_next_step(actor.id)
    await bot.send_msg(actor.id,f'✅ Номер сохранён.\n\n{profile_text(actor,target)}',
                       profile_keyboard(actor,target).keyboard,markdown=True)
