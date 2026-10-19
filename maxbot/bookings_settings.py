"""Активные брони, история и управление с проверкой доступа по пункту."""
import json
import os
from maxbot.bot_manager import bot,keyboard_to_start,HOMESTAYS_PER_PAGE
from maxbot.inline_keyboard import InlineKeyboardMarkup,button_types
from maxbot.functions import safe_json_loads
from database import db_manager as db,access


def _user(update):
    uid=(update.get('callback',{}).get('user',{}) or
         update.get('message',{}).get('sender',{})).get('user_id',0)
    return db.get_user(id=uid)


def _mid(update):
    return update.get('message',{}).get('body',{}).get('mid') or update.get('callback',{}).get('body',{}).get('mid')


def _payload(command,**kw):
    return json.dumps({'command':command,**kw})


def _pager(kb, command, page, total, **kw):
    if total <= HOMESTAYS_PER_PAGE:
        return
    n=max(1,(total+HOMESTAYS_PER_PAGE-1)//HOMESTAYS_PER_PAGE)
    row=InlineKeyboardMarkup()
    for text,index in [('◀️',max(1,page-1)),(f'{page}/{n}',page),('▶️',min(n,page+1))]:
        row.add_button(text,button_types.callback,_payload(command,page=index,**kw))
    kb.add_buttons_one_line(row.keyboard)


def _status(status):
    return {'pending':'🟠 Ожидает подтверждения','approved':'✅ Подтверждена',
            'cancelled':'↩️ Отменена пользователем','rejected':'❌ Отклонена сотрудником',
            'removed':'❌ Удалена сотрудником','expired':'⌛ Истекла автоматически'}.get(status,status)


def _history_entry(item):
    return (f"🆔 Бронь #{item['booking_id']} | {_status(item['status'])}\n"
            f"👤 MAX ID: {item['user_id']}\n"
            f"📍 {item['address_snapshot'] or 'Пункт удалён'}\n"
            f"📅 Создана: {item['date_time']}"
            + (f"\n⏱ Закрыта: {item['finished_at']}" if item['finished_at'] else ''))


def _send_text(texts):
    return '\n\n'.join(texts) if texts else 'Записей пока нет.'


async def _notify(bot,uid,text):
    try:
        if uid:
            await bot.send_msg(uid,text)
    except Exception as e:
        print('NOTIFICATION ERROR:',e)


async def _notify_managers(bot,point_id,text):
    for manager in db.get_homestay_managers(point_id):
        await _notify(bot,manager.id,text)


def _active_user_view(actor,page):
    bookings=sorted(db.get_user_bookings(actor),key=lambda b:b.date_time or '',reverse=True)
    total=len(bookings)
    page=min(max(1,page),max(1,(total+HOMESTAYS_PER_PAGE-1)//HOMESTAYS_PER_PAGE))
    visible=bookings[(page-1)*HOMESTAYS_PER_PAGE:page*HOMESTAYS_PER_PAGE]
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    kb.add_button('🕘 История всех моих броней',button_types.callback,'my_booking_history')
    _pager(kb,'my_bookings_page',page,total)
    for b in visible:
        kb.add_button(f'↩️ Отменить #{b.id}',button_types.callback,_payload('delete_my_booking',booking_id=b.id,page=page))
    return ('📋 Активные бронирования\n\n'+_send_text([str(b) for b in visible]),kb)


@bot.message_handler(func=lambda m,t: m.get('callback',{}).get('payload')=='my_bookings')
async def my_bookings(update,bot):
    actor=_user(update)
    if actor:
        text,kb=_active_user_view(actor,1)
        await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')=='my_bookings_page')
async def my_bookings_page(update,bot):
    actor=_user(update)
    if actor:
        page=int(safe_json_loads(update['callback']['payload']).get('page') or 1)
        text,kb=_active_user_view(actor,page)
        await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')=='delete_my_booking')
async def delete_my_booking(update,bot):
    actor=_user(update)
    if not actor:return
    data=safe_json_loads(update['callback']['payload'])
    booking=db.get_booking(id=data.get('booking_id'))
    if booking and booking.user_id==actor.id:
        summary=str(booking)
        if db.delete_booking(booking,reason='cancelled',actor_id=actor.id):
            await _notify_managers(bot,booking.homestay_id,
                                   f'↩️ Пользователь отменил бронь #{booking.id}.\n{summary}')
    text,kb=_active_user_view(actor,int(data.get('page') or 1))
    await bot.edit_msg(_mid(update),text,kb.keyboard)


def _history_view(actor,page,point_id=None,search_id=None):
    if point_id is None:
        kwargs={'user_id':actor.id}
    else:
        kwargs={'homestay_id':point_id,'search_user_id':search_id}
    total=db.count_booking_history(**kwargs)
    page=min(max(1,page),max(1,(total+HOMESTAYS_PER_PAGE-1)//HOMESTAYS_PER_PAGE))
    items=db.get_booking_history(limit=HOMESTAYS_PER_PAGE,offset=(page-1)*HOMESTAYS_PER_PAGE,**kwargs)
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ '+('К броням пункта' if point_id else 'Мои брони'),button_types.callback,
                  _payload('manage_homestay_bookings',homestay_id=point_id) if point_id else 'my_bookings')
    cmd='point_history_page' if point_id else 'my_history_page'
    _pager(kb,cmd,page,total,**({'point':point_id,'search':search_id} if point_id else {}))
    title=f'🕘 История бронирований пункта #{point_id}' if point_id else '🕘 История моих бронирований'
    if search_id is not None:
        title+=f'\nПоиск MAX ID: {search_id}'
    return title+f'\nВсего: {total}\n\n'+_send_text([_history_entry(x) for x in items]),kb


@bot.message_handler(func=lambda m,t: m.get('callback',{}).get('payload')=='my_booking_history')
async def my_booking_history(update,bot):
    actor=_user(update)
    if actor:
        text,kb=_history_view(actor,1)
        await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')=='my_history_page')
async def my_history_page(update,bot):
    actor=_user(update)
    if actor:
        data=safe_json_loads(update['callback']['payload'])
        text,kb=_history_view(actor,int(data.get('page') or 1))
        await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: m.get('callback',{}).get('payload')=='manage_bookings')
async def staff_point_list(update,bot):
    actor=_user(update)
    if not actor or (not access.managed_points(actor) and not access.is_global(actor)
                     and actor.user_type!=access.FUND_ADMIN):
        await bot.send_msg(actor.id if actor else 0,'⛔ Доступ разрешен только сотрудникам.')
        return
    points=access.managed_points(actor)
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    for point in points:
        kb.add_button('📍 '+point.address,button_types.callback,
                      _payload('manage_homestay_bookings',homestay_id=point.id))
    await bot.edit_msg(_mid(update),'📋 Выберите пункт для управления бронированиями:' if points
                       else 'Пока нет доступных пунктов.',kb.keyboard)


def _staff_booking_view(point_id,page):
    point=db.get_homestay(id=point_id)
    items=sorted(db.get_homestay_bookings(point),key=lambda b:b.date_time or '',reverse=True)
    total=len(items)
    page=min(max(1,page),max(1,(total+HOMESTAYS_PER_PAGE-1)//HOMESTAYS_PER_PAGE))
    visible=items[(page-1)*HOMESTAYS_PER_PAGE:page*HOMESTAYS_PER_PAGE]
    kb=InlineKeyboardMarkup()
    kb.add_button('⬅️ К пунктам',button_types.callback,'manage_bookings')
    kb.add_button('🕘 История всех броней',button_types.callback,_payload('point_history',point=point_id))
    kb.add_button('🔎 Поиск в истории по MAX ID',button_types.callback,_payload('point_history_search',point=point_id))
    _pager(kb,'manage_homestay_bookings_page',page,total,point=point_id)
    blocks=[]
    for b in visible:
        user=db.get_user(id=b.user_id)
        blocks.append(f"🆔 #{b.id} • {'✅ Подтверждена' if b.is_approved else '🟠 Ожидает'}\n"
                      f"👤 {user.username if user else '-'} (MAX ID {b.user_id})\n"
                      f"📅 {b.date_time}")
        row=InlineKeyboardMarkup()
        if not b.is_approved:
            row.add_button('✅ Подтвердить #'+str(b.id),button_types.callback,
                           _payload('staff_approve_booking',booking_id=b.id,homestay_id=point_id,page=page))
        row.add_button('❌ Отклонить #'+str(b.id),button_types.callback,
                       _payload('staff_delete_booking',booking_id=b.id,homestay_id=point_id,page=page))
        kb.add_buttons_one_line(row.keyboard)
    return (f'📋 Активные бронирования\n📍 {point.address if point else point_id}\n\n'
            +_send_text(blocks),kb)


async def _show_staff_view(update,bot):
    actor=_user(update)
    data=safe_json_loads(update['callback']['payload'])
    point=int(data.get('homestay_id') or data.get('point') or 0)
    if not access.can_manage_point(actor,point):
        await bot.send_msg(actor.id if actor else 0,'⛔ Нет доступа к этому пункту.')
        return
    text,kb=_staff_booking_view(point,int(data.get('page') or 1))
    await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     in ('manage_homestay_bookings','manage_homestay_bookings_page'))
async def manage_homestay_bookings(update,bot):
    await _show_staff_view(update,bot)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     in ('staff_approve_booking','approve_booking','staff_delete_booking','delete_booking'))
async def change_booking(update,bot):
    actor=_user(update)
    data=safe_json_loads(update['callback']['payload'])
    booking=db.get_booking(id=data.get('booking_id'))
    if not booking:
        await bot.send_msg(actor.id if actor else 0,'Заявка уже обработана или истекла.')
        return
    point_id=int(data.get('homestay_id') or booking.homestay_id)
    if point_id != booking.homestay_id or not access.can_manage_point(actor,point_id):
        await bot.send_msg(actor.id if actor else 0,'⛔ Не можете изменять чужую бронь.')
        return
    is_approve=data['command'] in ('staff_approve_booking','approve_booking')
    if is_approve:
        success=db.approve_booking(booking.id,actor_id=actor.id,point_id=point_id)
        if success:
            await _notify(bot,booking.user_id,f'✅ Ваша бронь #{booking.id} подтверждена!\n{booking}')
    else:
        summary=str(booking)
        success=db.delete_booking(booking,reason='rejected',actor_id=actor.id)
        if success:
            await _notify(bot,booking.user_id,
                          f'❌ Ваша бронь #{booking.id} отклонена сотрудником.\n{summary}')
    if success:
        await _notify_managers(bot,point_id,
                               f"{'✅ Подтверждена' if is_approve else '❌ Отклонена'} бронь #{booking.id} сотрудником {actor.id}.")
    else:
        await _notify(bot,actor.id,'Заявка уже была обработана другим сотрудником.')
    await _show_staff_view({**update,'callback':{**update['callback'],
        'payload':_payload('manage_homestay_bookings',homestay_id=point_id,
                           page=int(data.get('page') or 1))}},bot)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'update_booking_info')
async def update_booking_info(update,bot):
    actor=_user(update)
    data=safe_json_loads(update['callback']['payload'])
    booking=db.get_booking(id=data.get('booking_id'))
    if not actor or not booking or (actor.id!=booking.user_id and
                                    not access.can_manage_point(actor,booking.homestay_id)):
        await bot.send_msg(actor.id if actor else 0,'Бронь не найдена или недоступна.')
        return
    kb=InlineKeyboardMarkup()
    kb.add_button('🔄 Обновить',button_types.callback,_payload('update_booking_info',booking_id=booking.id))
    kb.add_button('⬅️ Главное меню',button_types.callback,'load_start')
    await bot.edit_msg(_mid(update),f'📋 Сведения о бронировании\n{booking}',kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     in ('point_history','point_history_page'))
async def point_history(update,bot):
    actor=_user(update)
    data=safe_json_loads(update['callback']['payload'])
    point=int(data.get('point') or 0)
    if not access.can_manage_point(actor,point):
        await bot.send_msg(actor.id if actor else 0,'⛔ Нет доступа к истории этого пункта.')
        return
    search_id=data.get('search')
    text,kb=_history_view(actor,int(data.get('page') or 1),point,
                          int(search_id) if search_id is not None else None)
    if search_id is not None:
        kb.add_button('❎ Сбросить поиск',button_types.callback,_payload('point_history',point=point))
    await bot.edit_msg(_mid(update),text,kb.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(m.get('callback',{}).get('payload')).get('command')
                     == 'point_history_search')
async def point_history_search(update,bot):
    actor=_user(update)
    point=int(safe_json_loads(update['callback']['payload']).get('point') or 0)
    if not access.can_manage_point(actor,point):
        await bot.send_msg(actor.id if actor else 0,'⛔ Нет доступа.')
        return
    bot.set_next_step(actor.id,_payload('history_search_input',point=point))
    await bot.edit_msg(_mid(update),'🔎 Введите числовой MAX ID пользователя для поиска в истории:',
                       keyboard_to_start.keyboard)


@bot.message_handler(func=lambda m,t: safe_json_loads(bot.get_next_step(
    m.get('message',{}).get('sender',{}).get('user_id',0))).get('command')=='history_search_input')
async def history_search_input(update,bot):
    actor=_user(update)
    if not actor:return
    point=safe_json_loads(bot.get_next_step(actor.id)).get('point')
    if not access.can_manage_point(actor,point):
        bot.clear_next_step(actor.id)
        return
    try: uid=int(update.get('message',{}).get('body',{}).get('text','').strip())
    except ValueError:
        await bot.send_msg(actor.id,'Введите числовой MAX ID.')
        return
    bot.clear_next_step(actor.id)
    text,kb=_history_view(actor,1,point,uid)
    kb.add_button('❎ Сбросить поиск',button_types.callback,_payload('point_history',point=point))
    await bot.send_msg(actor.id,text,kb.keyboard)
