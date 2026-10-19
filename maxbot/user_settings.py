"""Профили и роли; все проверки выполняются повторно на сервере при каждом клике."""
import json
from maxbot.bot_manager import bot, keyboard_to_start
from maxbot.inline_keyboard import InlineKeyboardMarkup, button_types
from maxbot.functions import safe_json_loads
from database import db_manager as db
from database import access


def _actor(update):
    data = update.get('callback', {}).get('user') or update.get('message', {}).get('sender', {})
    return db.get_user(id=data.get('user_id', 0))


def _mid(update):
    return (update.get('message', {}).get('body', {}).get('mid') or
            update.get('callback', {}).get('body', {}).get('mid'))


def profile_keyboard(actor, target):
    kb = InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню', button_types.callback, 'load_start')
    if actor and (actor.id == target.id or access.is_global(actor)):
        kb.add_button('📱 Изменить номер', button_types.callback,
                      json.dumps({'command': 'change_number', 'user': target.id}))
    if access.can_manage_account(actor,target):
        if access.is_global(actor):
            kb.add_button('👑 Сделать администратором бота', button_types.callback,
                          json.dumps({'command': 'set_admin', 'user': target.id}))
        if target.user_type != access.MANAGER:
            kb.add_button('👷 Назначить менеджером', button_types.callback,
                          json.dumps({'command': 'set_manager', 'user': target.id}))
        if target.user_type != access.USER:
            kb.add_button('🚫 Снять роль', button_types.callback,
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
        await bot.edit_msg(_mid(update), f'👤 Ваш профиль:\n{actor}', profile_keyboard(actor, actor).keyboard)


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
    info=str(target)
    if not access.is_global(actor) and actor.id != target.id and target.user_type==access.USER:
        # Достаточно ID и имени для назначения; телефон постороннего пользователя скрыт.
        info=f'ID: {target.id}\nИмя: {target.username or "-"}\nРоль: Пользователь'
    await bot.send_msg(actor.id, f'👤 Информация о пользователе:\n{info}',
                       profile_keyboard(actor,target).keyboard)


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
    db.set_account_role(target.id,role)
    target = db.get_user(id=target.id)
    await bot.edit_msg(_mid(update),f'✅ Роль обновлена.\n{target}',profile_keyboard(actor,target).keyboard)


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
        kb.add_button(('✅ Убрать из ' if linked else '➕ Добавить в ') + point.address,
                      button_types.callback,json.dumps({'command':'toggle_manager_link',
                                                         'user':target.id,'point':point.id}))
    await bot.edit_msg(_mid(update),f'Пункты менеджера {target.username or target.id}:\n'
                        'Нажмите пункт, чтобы добавить или убрать привязку.',kb.keyboard)


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
    if not actor or not target or not (actor.id==target.id or access.is_global(actor)):
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
    if not actor or not target or not (actor.id==target.id or access.is_global(actor)):
        bot.clear_next_step(actor.id)
        return
    phone=update.get('message',{}).get('body',{}).get('text','').strip()
    if not phone or len(phone)>30:
        await bot.send_msg(actor.id,'Укажите номер до 30 символов.')
        return
    target.phone_number=phone
    db.insert_or_update_user(target)
    bot.clear_next_step(actor.id)
    await bot.send_msg(actor.id,f'✅ Номер сохранён.\n{target}',profile_keyboard(actor,target).keyboard)
