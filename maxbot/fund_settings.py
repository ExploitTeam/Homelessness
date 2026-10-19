"""Управление фондами из чата MAX, без изменений REST API."""
import json
from maxbot.bot_manager import bot, keyboard_to_start
from maxbot.inline_keyboard import InlineKeyboardMarkup,button_types
from maxbot.functions import safe_json_loads
from database import db_manager as db
from database import access


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
    await bot.edit_msg(mid(update),'🏛️ Фонды. Выберите фонд или создайте новый.',kb.keyboard)


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
    admins=[u for u in get_fund_admins(f_id)]
    points=[h for h in db.get_all_homestays() if h.fund_id==f_id]
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Фонды',button_types.callback,'funds_panel')
    kb.add_button('✏️ Название',button_types.callback,payload('fund_edit',fund=f_id,field='name'))
    kb.add_button('📝 Описание',button_types.callback,payload('fund_edit',fund=f_id,field='description'))
    if access.is_global(actor):
        kb.add_button('👤 Назначить администратора фонда',button_types.callback,
                      payload('fund_assign_admin',fund=f_id))
        kb.add_button('📍 Перенести пункт в фонд',button_types.callback,
                      payload('fund_move_point',fund=f_id))
    text=(f"🏛️ {f['name']} (ID {f_id})\n📝 {f['description'] or 'Без описания'}\n"
          f"👤 Администраторы: {', '.join(str(a.id) for a in admins) or 'Не назначены'}\n"
          f"📍 Пунктов: {len(points)}")
    await bot.edit_msg(mid(update),text,kb.keyboard)


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
                point.fund_id=fid
                ok=db.insert_or_update_homestay(point)
    if ok:
        bot.clear_next_step(actor.id)
    await bot.send_msg(actor.id,'✅ Изменения сохранены.' if ok else '⚠️ Не удалось выполнить действие. Проверьте ID, права и уникальность названия.',
                       [[{'text':'Вернуться к фонду','type':'callback','payload':payload('fund_show',fund=fid)}]])
