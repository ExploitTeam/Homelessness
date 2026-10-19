"""Управление фондами из чата MAX, без изменений REST API."""
import json
from maxbot.bot_manager import bot, keyboard_to_start
from maxbot.inline_keyboard import InlineKeyboardMarkup,button_types
from maxbot.functions import safe_json_loads
from database import db_manager as db
from database import access
from maxbot.formatting import escape as md_escape


def sender_id(update):
    return (update.get('callback',{}).get('user') or update.get('message',{}).get('sender',{})).get('user_id',0)


def mid(update):
    return update.get('message',{}).get('body',{}).get('mid') or update.get('callback',{}).get('body',{}).get('mid')


def payload(command,**kwargs):
    return json.dumps({'command':command,**kwargs})


@bot.message_handler(func=lambda m,t: m.get('callback',{}).get('payload') == 'funds_panel')
async def fund_panel(update,bot):
    actor=db.get_user(id=sender_id(update))
    if not actor or (not access.is_global(actor) and actor.user_type != access.FUND_ADMIN):
        return
    funds=db.get_funds() if access.is_global(actor) else [db.get_fund(actor.fund_id)]
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    if access.is_global(actor):
        kb.add_button('➕ Создать фонд',button_types.callback,payload('fund_create'))
    for fund in filter(None,funds):
        kb.add_button('🏛️ '+fund['name'],button_types.callback,payload('fund_show',fund=fund['id']))
    await bot.edit_msg(mid(update),'**🏛️ Управление фондами**\nВыберите фонд для просмотра и настройки.',kb.keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'fund_create')
async def fund_create(update,bot):
    actor=db.get_user(id=sender_id(update))
    if not access.is_global(actor):
        return
    bot.set_next_step(actor.id,payload('fund_new_name'))
    await bot.edit_msg(mid(update),'Название нового фонда (1–120 символов):',keyboard_to_start.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command') == 'fund_new_name')
async def fund_new_name(update,bot):
    actor=db.get_user(id=sender_id(update))
    if not access.is_global(actor):return
    name=update.get('message',{}).get('body',{}).get('text','').strip()
    if not name or len(name)>120:
        await bot.send_msg(actor.id,'Введите название от 1 до 120 символов.')
        return
    bot.set_next_step(actor.id,payload('fund_new_description',name=name))
    await bot.send_msg(actor.id,'Добавьте описание фонда (или отправьте «-», чтобы пропустить):')


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command') == 'fund_new_description')
async def fund_new_description(update,bot):
    actor=db.get_user(id=sender_id(update))
    if not access.is_global(actor):return
    name=safe_json_loads(bot.get_next_step(actor.id)).get('name')
    desc=update.get('message',{}).get('body',{}).get('text','').strip()
    if len(desc)>1500:
        await bot.send_msg(actor.id,'Описание слишком длинное (максимум 1500 символов). Попробуйте ещё раз.')
        return
    fund_id=db.create_fund(name,'' if desc=='-' else desc)
    if fund_id:
        bot.clear_next_step(actor.id)
        await bot.send_msg(actor.id,f'✅ Фонд «{name}» создан. ID: {fund_id}.',
                           [[{'text':'Открыть фонд','type':'callback','payload':payload('fund_show',fund=fund_id)}]])
    else:
        await bot.send_msg(actor.id,'Не удалось создать фонд: название занято или описание слишком длинное.')


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'fund_show')
async def show_fund(update,bot):
    actor=db.get_user(id=sender_id(update))
    f_id=int(safe_json_loads(update['callback']['payload']).get('fund') or 0)
    if not access.can_manage_fund(actor,f_id):
        await bot.send_msg(sender_id(update),'⛔ Доступ к фонду запрещён.')
        return
    f=db.get_fund(f_id)
    if not f:
        await bot.send_msg(sender_id(update),'Фонд уже удалён.')
        return
    admins=[u for u in get_fund_admins(f_id)]
    points=[h for h in db.get_all_homestays() if h.fund_id==f_id]
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Фонды',button_types.callback,'funds_panel')
    kb.add_button('🏠 Управление пунктами',button_types.callback,payload('point_fund',fund=f_id))
    kb.add_button('✏️ Название',button_types.callback,payload('fund_edit',fund=f_id,field='name'))
    kb.add_button('📝 Описание',button_types.callback,payload('fund_edit',fund=f_id,field='description'))
    kb.add_button('🗑️ Удалить фонд',button_types.callback,payload('fund_delete_prompt',fund=f_id))
    if access.is_global(actor):
        kb.add_button('👤 Назначить администратора фонда',button_types.callback,
                      payload('fund_assign_admin',fund=f_id))
        kb.add_button('📍 Перенести пункт в фонд',button_types.callback,
                      payload('fund_move_point',fund=f_id))
    admin_names=', '.join(md_escape(a.username or 'Администратор') for a in admins) or 'Не назначены'
    if access.is_global(actor):
        for a in admins:
            if access.is_global(a):
                continue
            kb.add_button('🚫 Снять права: '+(a.username or str(a.id))[:27],
                          button_types.callback,payload('fund_admin_revoke',fund=f_id,user=a.id))
    text=(f"**🏛️ {md_escape(f['name'])}**\n\n"
          f"{md_escape(f['description'] or 'Без описания')}\n\n"
          f"**Администраторы:** {admin_names}\n"
          f"**Пунктов помощи:** {len(points)}")
    await bot.edit_msg(mid(update),text,kb.keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'fund_delete_prompt')
async def fund_delete_prompt(update,bot):
    actor=db.get_user(id=sender_id(update))
    fid=int(safe_json_loads(update['callback']['payload']).get('fund') or 0)
    fund=db.get_fund(fid)
    if not fund or not access.can_manage_fund(actor,fid):
        await bot.send_msg(sender_id(update),'⛔ У вас нет доступа к этому фонду.')
        return
    points=[h for h in db.get_all_homestays() if h.fund_id==fid]
    active=sum(len(db.get_homestay_bookings(p)) for p in points)
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Отмена',button_types.callback,payload('fund_show',fund=fid))
    kb.add_button('🗑️ Да, удалить безвозвратно',button_types.callback,
                  payload('fund_delete_confirm',fund=fid))
    text=(f'**⚠️ Удаление фонда «{md_escape(fund["name"])}»**\n\n'
          f'Будут удалены {len(points)} пункт(ов) и закрыты {active} активных броней. '
          'Все менеджеры потеряют привязки к этим пунктам, администраторы фонда — свои права.\n\n'
          '**История бронирований сохранится.** Действие нельзя отменить.')
    await bot.edit_msg(mid(update),text,kb.keyboard,markdown=True)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'fund_delete_confirm')
async def fund_delete_confirm(update,bot):
    actor=db.get_user(id=sender_id(update))
    fid=int(safe_json_loads(update['callback']['payload']).get('fund') or 0)
    if not access.can_manage_fund(actor,fid):
        await bot.send_msg(sender_id(update),'⛔ Доступ запрещён.')
        return
    result=db.delete_fund(fid,actor.id)
    if result is None:
        await bot.send_msg(actor.id,'Фонд уже удалён или права изменились.')
        return
    for booking_id,user_id in result['bookings']:
        try:
            await bot.send_msg(user_id,
                f'⚠️ Бронь №{booking_id} закрыта из-за удаления фонда. История доступна в разделе «Мои бронирования».')
        except Exception as err:
            print('Уведомление о закрытии брони не доставлено:',err)
    kb=InlineKeyboardMarkup()
    kb.add_button('🏠 Главное меню',button_types.callback,'load_start')
    if access.is_global(db.get_user(id=actor.id)):
        kb.add_button('🏛️ Все фонды',button_types.callback,'funds_panel')
    await bot.edit_msg(mid(update),
        f'✅ Фонд удалён. Удалено пунктов: {result["points"]}. '
        f'Закрыто броней: {len(result["bookings"])}. История сохранена.',kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'fund_admin_revoke')
async def fund_admin_revoke(update,bot):
    actor=db.get_user(id=sender_id(update))
    data=safe_json_loads(update['callback']['payload'])
    fid=int(data.get('fund') or 0)
    target=db.get_user(id=data.get('user'))
    if not access.is_global(actor) or not db.get_fund(fid) or not target or access.is_global(target) or target.user_type!=access.FUND_ADMIN or target.fund_id!=fid:
        await bot.send_msg(sender_id(update),'⛔ Недостаточно прав или роль уже изменена.')
        return
    db.set_account_role(target.id,access.USER)
    await show_fund({**update,'callback':{**update['callback'],
        'payload':payload('fund_show',fund=fid)}},bot)

def get_fund_admins(fund_id):
    import sqlite3
    with sqlite3.connect(db.database_name) as conn:
        rows=conn.execute('SELECT id FROM users WHERE user_type=3 AND fund_id=?',(fund_id,))
        return [u for (id_,) in rows if (u:=db.get_user(id=id_))]


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     in ('fund_edit','fund_assign_admin','fund_move_point'))
async def fund_action(update,bot):
    actor=db.get_user(id=sender_id(update))
    data=safe_json_loads(update['callback']['payload'])
    fid=int(data.get('fund') or 0)
    if not access.can_manage_fund(actor,fid):return
    if data['command'] != 'fund_edit' and not access.is_global(actor):return
    bot.set_next_step(actor.id,payload(data['command']+'_input',fund=fid,field=data.get('field')))
    label={'fund_edit':'Введите новое значение поля «'+str(data.get('field'))+'»: ',
           'fund_assign_admin':'Введите MAX ID пользователя (он должен сначала запустить бота):',
           'fund_move_point':'Введите ID пункта, который нужно перенести в этот фонд:'}[data['command']]
    await bot.edit_msg(mid(update),label,keyboard_to_start.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command')
                     in ('fund_edit_input','fund_assign_admin_input','fund_move_point_input'))
async def fund_action_input(update,bot):
    actor=db.get_user(id=sender_id(update))
    data=safe_json_loads(bot.get_next_step(actor.id))
    fid=int(data.get('fund') or 0)
    if not access.can_manage_fund(actor,fid):
        bot.clear_next_step(actor.id)
        return
    value=update.get('message',{}).get('body',{}).get('text','').strip()
    kind=data['command']
    ok=False
    if kind=='fund_edit_input':
        ok=db.edit_fund(fid,**{data['field']:value})
    elif access.is_global(actor):
        try: target=int(value)
        except ValueError: target=0
        if kind=='fund_assign_admin_input':
            account=db.get_user(id=target)
            if account and account.id != actor.id and not access.is_global(account):
                ok=db.set_account_role(target,access.FUND_ADMIN,fid)
        elif kind=='fund_move_point_input':
            point=db.get_homestay(id=target)
            if point:
                # При переносе снимаем все старые назначения, чтобы доступ не перетекал между фондами.
                import sqlite3
                with sqlite3.connect(db.database_name) as conn:
                    conn.execute('DELETE FROM point_managers WHERE point_id=?',(point.id,))
                    conn.execute('UPDATE users SET id_homestay=NULL WHERE id_homestay=?',(point.id,))
                    conn.execute('UPDATE users SET id_homestay=(SELECT MIN(point_id) '
                                 'FROM point_managers WHERE manager_id=users.id) '
                                 'WHERE user_type=1 AND id_homestay IS NULL')
                point.fund_id=fid
                ok=db.insert_or_update_homestay(point)
    if ok:
        bot.clear_next_step(actor.id)
    await bot.send_msg(actor.id,'✅ Изменения сохранены.' if ok else '⚠️ Не удалось выполнить действие. Проверьте ID, права и уникальность названия.',
                       [[{'text':'Вернуться к фонду','type':'callback','payload':payload('fund_show',fund=fid)}]])
