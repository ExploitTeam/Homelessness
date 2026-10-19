"""Запуск: python -m unittest discover -s tests -v"""
import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import db_manager as db, access
from database.classes import Booking, Homestay, User
from maxbot.bookings_settings import change_booking, delete_my_booking
from maxbot.maxapi import Bot


class FakeBot:
    def __init__(self):
        self.sent=[]
        self.edited=[]
    async def send_msg(self, uid, text, keyboard=None, **kwargs):
        self.sent.append((uid,text,keyboard))
    async def edit_msg(self,mid,text,keyboard=None, **kwargs):
        self.edited.append((mid,text,keyboard))


def callback(uid,command,**kwargs):
    return {'callback': {'user':{'user_id':uid},
                         'payload':json.dumps({'command':command,**kwargs})},
            'message':{'body':{'mid':'message-1'}}}


class MultiFundTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_name=db.database_name
        db.database_name=str(Path(self.temp.name)/'test.db')
        db.initialize_database()
        self.f1=db.create_fund('Фонд А','Описание А')
        self.f2=db.create_fund('Фонд Б','Описание Б')
        self.global_admin=User(id=110,username='Главный',user_type=2)
        self.admin_a=User(id=111,username='А',user_type=3,fund_id=self.f1)
        self.admin_b=User(id=112,username='Б',user_type=3,fund_id=self.f2)
        self.manager_a=User(id=113,username='m1',user_type=1)
        self.manager_b=User(id=114,username='m2',user_type=1)
        self.normal=User(id=115,username='user',user_type=0)
        for user in (self.global_admin,self.admin_a,self.admin_b,self.manager_a,self.manager_b,self.normal):
            self.assertTrue(db.insert_or_update_user(user))
        self.p1=Homestay(address='Точка А',all_beds=5,available_beds=4,
                        open_time='09:00',close_time='18:00',is_working=1,
                        longtitude=37.62,latitude=55.75,fund_id=self.f1)
        self.p2=Homestay(address='Точка Б',all_beds=2,available_beds=2,
                        open_time='09:00',close_time='18:00',is_working=1,
                        longtitude=37.6,latitude=55.7,fund_id=self.f2)
        for point in (self.p1,self.p2):
            self.assertTrue(db.insert_or_update_homestay(point))

    def tearDown(self):
        db.database_name=self.old_name
        self.temp.cleanup()

    def booking(self,point=None):
        result=Booking(user_id=self.normal.id,homestay_id=(point or self.p1).id,
                       date_time='2026-10-19T12:00:00')
        self.assertTrue(db.insert_or_update_booking(result))
        return result

    def test_scoping_and_many_to_many(self):
        self.assertTrue(db.assign_manager(self.p1.id,self.manager_a.id))
        self.assertTrue(db.assign_manager(self.p1.id,self.manager_b.id))
        self.assertTrue(db.assign_manager(self.p2.id,self.manager_b.id))
        self.assertEqual({m.id for m in db.get_homestay_managers(self.p1.id)},{113,114})
        self.assertEqual(len(db.get_manager_points(self.manager_b.id)),2)
        self.assertTrue(access.can_manage_point(self.manager_b,self.p1.id))
        self.assertFalse(access.can_manage_point(self.manager_a,self.p2.id))
        self.assertFalse(access.can_manage_point(self.admin_a,self.p2.id))
        self.assertTrue(access.can_manage_point(self.admin_a,self.p1.id))
        self.assertTrue(access.can_manage_point(self.global_admin,self.p2.id))
        self.assertFalse(access.can_assign_manager(self.admin_a,self.manager_b,self.p2))
        self.assertFalse(access.can_manage_account(self.admin_a,self.manager_b))
        self.assertTrue(db.unassign_manager(self.p1.id,self.manager_b.id))
        self.assertEqual({m.id for m in db.get_homestay_managers(self.p1.id)},{113})

    def test_history_survives_delete_and_id_never_reused(self):
        first=self.booking()
        self.assertTrue(db.approve_booking(first.id,actor_id=self.manager_a.id,point_id=self.p1.id))
        self.assertFalse(db.approve_booking(first.id,actor_id=self.manager_a.id,point_id=self.p1.id))
        self.assertTrue(db.delete_booking(first,reason='cancelled',actor_id=self.normal.id))
        self.assertIsNone(db.get_booking(id=first.id))
        self.assertEqual(db.get_homestay(id=self.p1.id).available_beds,5)
        history=db.get_booking_history(user_id=self.normal.id)
        self.assertEqual(history[0]['status'],'cancelled')
        self.assertEqual([e['event'] for e in db.get_booking_events(first.id)],
                         ['pending','approved','cancelled'])
        second=self.booking()
        self.assertGreater(second.id,first.id)
        self.assertEqual(db.count_booking_history(user_id=self.normal.id),2)
        self.assertEqual(db.get_booking_history(homestay_id=self.p1.id,
                                                search_user_id=self.normal.id)[0]['booking_id'],second.id)
        self.assertEqual(db.count_booking_history(homestay_id=self.p1.id,search_user_id=999),0)

    def test_delete_once_only(self):
        booking=self.booking()
        self.assertTrue(db.delete_booking(booking,reason='rejected',actor_id=113))
        self.assertFalse(db.delete_booking(booking,reason='expired'))
        self.assertEqual(db.get_homestay(id=self.p1.id).available_beds,5)
        self.assertEqual(db.get_booking_history(user_id=self.normal.id)[0]['status'],'rejected')

    def test_unauthorized_callback_cannot_approve_or_delete_other_point(self):
        db.assign_manager(self.p1.id,self.manager_a.id)
        booking=self.booking()
        fake=FakeBot()
        asyncio.run(change_booking(callback(self.admin_b.id,'staff_approve_booking',
                                           booking_id=booking.id,homestay_id=self.p1.id),fake))
        self.assertFalse(db.get_booking(id=booking.id).is_approved)
        asyncio.run(change_booking(callback(self.manager_a.id,'staff_approve_booking',
                                           booking_id=booking.id,homestay_id=self.p2.id),fake))
        self.assertFalse(db.get_booking(id=booking.id).is_approved)
        asyncio.run(change_booking(callback(self.manager_a.id,'staff_approve_booking',
                                           booking_id=booking.id,homestay_id=self.p1.id),fake))
        self.assertTrue(db.get_booking(id=booking.id).is_approved)
        self.assertEqual(len([msg for msg in fake.sent if msg[0]==115]),1)
        asyncio.run(delete_my_booking(callback(self.manager_a.id,'delete_my_booking',
                                               booking_id=booking.id,page=1),fake))
        self.assertIsNotNone(db.get_booking(id=booking.id))

    def test_notification_fanout_without_api_changes(self):
        db.assign_manager(self.p1.id,self.manager_a.id)
        db.assign_manager(self.p1.id,self.manager_b.id)
        booking=self.booking()
        client=Bot('fake')
        sent=[]
        async def mock_send(user_id,text,btns=None):
            sent.append(user_id)
            return {'ok':True}
        client._send_single=mock_send
        buttons=[[{'text':'Подтвердить','payload':json.dumps({'command':'approve_booking',
                                                               'booking_id':booking.id})}]]
        asyncio.run(client.send_msg(self.manager_a.id,'Новая заявка! Бронь',buttons))
        self.assertEqual(set(sent),{self.manager_a.id,self.manager_b.id})
        self.assertEqual(len(sent),2)

    def test_rename_fund_preserves_point(self):
        self.assertTrue(db.edit_fund(self.f1,name='Переименован'))
        self.assertEqual(db.get_homestay(id=self.p1.id).fund_id,self.f1)
        self.assertFalse(access.can_create_point(self.admin_a,self.f2))


class LegacyMigrationTests(unittest.TestCase):
    def test_old_database_migrates_idempotently(self):
        with tempfile.TemporaryDirectory() as temp:
            old_name=db.database_name
            db.database_name=str(Path(temp)/'legacy.db')
            try:
                with sqlite3.connect(db.database_name) as conn:
                    conn.executescript('''
                        CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,user_type INTEGER,
                            phone_number TEXT,id_homestay INTEGER,last_booking TEXT);
                        CREATE TABLE homestays(id INTEGER PRIMARY KEY,address TEXT,all_beds INTEGER,
                            available_beds INTEGER,open_time TEXT,close_time TEXT,is_working INTEGER,
                            additional_info TEXT,homestay_type INTEGER,longtitude REAL,latitude REAL);
                        CREATE TABLE bookings(id INTEGER PRIMARY KEY,user_id INTEGER,homestay_id INTEGER,
                            date_time TEXT,is_approved INTEGER);
                        INSERT INTO users VALUES(100,'old',1,'',1,NULL);
                        INSERT INTO users VALUES(101,'visitor',0,'',NULL,NULL);
                        INSERT INTO homestays VALUES(1,'Old point',10,9,'10:00','19:00',1,'',0,10.0,20.0);
                        INSERT INTO bookings VALUES(28,101,1,'2026-10-17T09:00:00',0);
                    ''')
                db.initialize_database()
                db.initialize_database()
                point=db.get_homestay(id=1)
                self.assertEqual(db.get_fund(point.fund_id)['name'],'Основной фонд')
                self.assertEqual([x.id for x in db.get_homestay_managers(1)],[100])
                self.assertEqual(len(db.get_booking_history(user_id=101)),1)
                b=db.get_booking(id=28)
                self.assertTrue(db.delete_booking(b,reason='expired'))
                new=Booking(user_id=101,homestay_id=1,date_time='2026-10-19T12:00:00')
                self.assertTrue(db.insert_or_update_booking(new))
                self.assertEqual(new.id,29)
            finally:
                db.database_name=old_name


if __name__=='__main__':
    unittest.main()
