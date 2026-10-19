"""Регрессии пользовательских замечаний, без доступа к реальному MAX."""
import asyncio
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_multifund as fixtures
from test_multifund import FakeBot, callback
from database import access, db_manager as db
from database.classes import Booking
from maxbot.bot_manager import bot as live_bot
from maxbot.formatting import point_card
from maxbot.fund_settings import fund_delete_confirm, fund_delete_prompt
from maxbot.user_settings import assign_fund_admin, select_admin_fund, profile_keyboard
from maxbot.homestay_settings import edit_user_button_pressed, point_fund
from maxbot.bookings_settings import _history_view


class FakeFormattedBot(FakeBot):
    async def send_msg(self, uid, text, keyboard=None, **kwargs):
        self.sent.append((uid, text, keyboard, kwargs))
    async def edit_msg(self, mid, text, keyboard=None, **kwargs):
        self.edited.append((mid, text, keyboard, kwargs))


class FixedBehaviorTests(unittest.TestCase):
    setUp=fixtures.MultiFundTests.setUp
    tearDown=fixtures.MultiFundTests.tearDown
    booking=fixtures.MultiFundTests.booking
    def test_create_fund_two_real_messages(self):
        delivered=[]
        async def send(*args,**kwargs):delivered.append(('send',args,kwargs))
        async def edit(*args,**kwargs):delivered.append(('edit',args,kwargs))
        a=self.global_admin.id
        async def simulate():
            with patch.object(live_bot,'send_msg',send),patch.object(live_bot,'edit_msg',edit):
                try:
                    await live_bot._route_update({**callback(a,'fund_create'),'update_type':'message_callback'})
                    first={'update_type':'message_created','message':{'sender':{'user_id':a},
                        'body':{'text':'Новый фонд','mid':'created-1'}}}
                    await live_bot._route_update(first)
                    self.assertFalse(any(f['name']=='Новый фонд' for f in db.get_funds()),'создан до описания')
                    self.assertEqual(json.loads(live_bot.get_next_step(a))['command'],'fund_new_description')
                    await live_bot._route_update({'update_type':'message_created',
                        'message':{'sender':{'user_id':a},'body':{'text':'Еда и ночлег','mid':'created-2'}}})
                    fund=next(f for f in db.get_funds() if f['name']=='Новый фонд')
                    self.assertEqual(fund['description'],'Еда и ночлег')
                    self.assertFalse(live_bot.get_next_step(a))
                finally:
                    live_bot.clear_next_step(a)
        asyncio.run(simulate())
        self.assertTrue(any('Добавьте описание' in x[1][1] for x in delivered))

    def test_global_admin_assign_and_revoke_fund_admin(self):
        fake=FakeFormattedBot()
        asyncio.run(select_admin_fund(callback(110,'select_admin_fund',user=115),fake))
        data=[json.loads(row[0]['payload']) for row in fake.edited[-1][2][1:]]
        self.assertEqual({x['fund'] for x in data}, {self.f1,self.f2})
        asyncio.run(assign_fund_admin(callback(110,'assign_fund_admin',user=115,fund=self.f2),fake))
        target=db.get_user(id=115)
        self.assertEqual((target.user_type,target.fund_id),(access.FUND_ADMIN,self.f2))
        self.assertFalse(access.can_manage_fund(target,self.f1))
        self.assertTrue(access.can_manage_fund(target,self.f2))
        self.assertTrue(any('Снять права администратора' in button['text']
                            for row in profile_keyboard(self.global_admin,target).keyboard for button in row))
        # Админ чужого фонда не может назначать администраторов.
        asyncio.run(assign_fund_admin(callback(111,'assign_fund_admin',user=113,fund=self.f1),fake))
        self.assertEqual(db.get_user(id=113).user_type,access.MANAGER)
        db.set_account_role(115,access.USER)
        self.assertIsNone(db.get_user(id=115).fund_id)

    def test_delete_own_fund_cascade_and_history(self):
        db.assign_manager(self.p1.id,self.manager_a.id)
        db.assign_manager(self.p2.id,self.manager_a.id)
        booking=self.booking()
        fake=FakeFormattedBot()
        # Чужой админ не может удалить, даже вызвав метод базы напрямую.
        self.assertIsNone(db.delete_fund(self.f1,self.admin_b.id))
        asyncio.run(fund_delete_prompt(callback(self.admin_a.id,'fund_delete_prompt',fund=self.f1),fake))
        self.assertEqual(len(fake.edited),1)
        self.assertTrue(any('Да, удалить' in button['text']
                            for row in fake.edited[-1][2] for button in row))
        asyncio.run(fund_delete_confirm(callback(self.admin_a.id,'fund_delete_confirm',fund=self.f1),fake))
        self.assertIsNone(db.get_fund(self.f1))
        self.assertIsNone(db.get_homestay(id=self.p1.id))
        self.assertEqual(db.get_user(id=self.admin_a.id).user_type,access.USER)
        self.assertEqual(db.get_user(id=self.manager_a.id).id_homestay,self.p2.id)
        self.assertEqual(db.get_booking_history(user_id=self.normal.id)[0]['status'],'removed')
        self.assertIsNone(db.get_booking(id=booking.id))
        new=self.booking(self.p2)
        self.assertGreater(new.id,booking.id)
        self.assertTrue(any(x[0]==self.normal.id and 'закрыта' in x[1] for x in fake.sent))

    def test_fund_filtered_point_menus_and_old_callback(self):
        fake=FakeFormattedBot()
        asyncio.run(edit_user_button_pressed({'callback':{'user':{'user_id':111},'payload':'edit_homestay'},
                                                'message':{'body':{'mid':'m'}}},fake))
        labels=[row[0]['text'] for row in fake.edited[-1][2]]
        self.assertTrue(any('Фонд А' in x for x in labels))
        self.assertFalse(any('Фонд Б' in x for x in labels))
        asyncio.run(point_fund(callback(111,'point_fund',fund=self.f2),fake))
        self.assertEqual(len(fake.edited),1)
        self.assertTrue(any('Недостаточно прав' in x[1] for x in fake.sent))
        asyncio.run(point_fund(callback(110,'point_fund',fund=self.f2),fake))
        self.assertIn('Точка Б',str(fake.edited[-1][2]))

    def test_public_cards_hide_ids_and_explain_phone(self):
        db.assign_manager(self.p1.id,self.manager_a.id)
        self.manager_a.phone_number=None
        db.insert_or_update_user(self.manager_a)
        public=str(db.get_homestay(id=self.p1.id))
        formatted=point_card(db.get_homestay(id=self.p1.id))
        self.assertNotIn(str(self.manager_a.id),public)
        self.assertNotIn(str(self.manager_a.id),formatted)
        self.assertNotIn('(ID',public)
        self.assertIn('Номер телефона не указан',public)
        self.assertIn('Номер телефона не указан',formatted)
        booking=self.booking()
        self.assertNotIn(str(self.manager_a.id),str(booking))
        history,_=_history_view(self.normal,1)
        self.assertNotIn(f'MAX ID: {self.normal.id}',history)

    def test_booking_sequence_outlives_deleted_history(self):
        a=self.booking()
        self.assertTrue(db.delete_booking(a,reason='cancelled'))
        # Даже принудительная ручная очистка журнала не откатывает счётчик.
        with sqlite3.connect(db.database_name) as conn:
            conn.execute('DELETE FROM booking_history')
        b=self.booking()
        self.assertGreater(b.id,a.id)
        self.assertFalse(db.insert_or_update_booking(a),'воскрешение ID недопустимо')
        db.initialize_database()
        c=self.booking()
        self.assertGreater(c.id,b.id)


if __name__ == '__main__':
    unittest.main()

class MaxWireFormatTests(unittest.TestCase):
    def test_max_wire_format_for_send_and_edit(self):
        from maxbot.maxapi import Bot
        class Response:
            status=200
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def json(self):return {'success':True}
        class Session:
            def __init__(self):self.bodies=[]
            def post(self,*args,**kwargs):
                self.bodies.append(kwargs['json']);return Response()
            def put(self,*args,**kwargs):
                self.bodies.append(kwargs['json']);return Response()
        instance=Bot('dummy')
        instance.session=Session()
        async def work():
            await instance.send_msg(113,'**Заголовок**',markdown=True)
            await instance.send_msg(113,'Текст без оформления')
            await instance.edit_msg('mid-1','**Новое**',markdown=True)
        asyncio.run(work())
        self.assertEqual(instance.session.bodies[0]['format'],'markdown')
        self.assertNotIn('format',instance.session.bodies[1])
        self.assertEqual(instance.session.bodies[2]['format'],'markdown')
