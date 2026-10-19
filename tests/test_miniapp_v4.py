"""API mini-app: фонд, все менеджеры, отсутствие служебных ID, личная бронь.

Запуск: python -m unittest discover -s tests -v
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jwt
from fastapi.testclient import TestClient
from api import http_server as api
from database import db_manager as db
from database.classes import Homestay, User, Booking


class MiniAppAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_db = db.database_name
        self.previous_secret = api.JWT_SECRET
        db.database_name = str(Path(self.temp.name) / 'test.db')
        api.JWT_SECRET = 'test-only-jwt-secret'
        db.initialize_database()
        self.fund_id = db.create_fund('Светлый путь', 'Оказываем бесплатную поддержку и помощь.')
        self.users = [
            User(id=2601, username='Посетитель', user_type=0),
            User(id=2602, username='Чужой пользователь', user_type=0),
            User(id=2603, username='Первый менеджер', user_type=1, phone_number='+7 920 111-22-33'),
            User(id=2604, username='Второй менеджер', user_type=1, phone_number=None),
        ]
        for user in self.users:
            self.assertTrue(db.insert_or_update_user(user))
        self.point = Homestay(
            address='Москва, примерная улица, 10', all_beds=6,
            available_beds=3, open_time='18:00', close_time='08:00',
            is_working=1, homestay_type=2,
            additional_info='Можно получить горячий ужин.',
            longtitude=37.6173, latitude=55.75, fund_id=self.fund_id,
        )
        self.assertTrue(db.insert_or_update_homestay(self.point))
        self.assertTrue(db.assign_manager(self.point.id, self.users[2].id))
        self.assertTrue(db.assign_manager(self.point.id, self.users[3].id))
        self.client = TestClient(api.app)

    def tearDown(self):
        self.client.close()
        db.database_name = self.previous_db
        api.JWT_SECRET = self.previous_secret
        self.temp.cleanup()

    def headers(self, user_id):
        token = jwt.encode({
            'sub': str(user_id),
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        }, api.JWT_SECRET, algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    def test_response_contains_fund_and_all_managers_without_service_ids(self):
        response = self.client.get('/api/places', headers=self.headers(2601))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_id'], 2601)
        self.assertEqual(len(data['places']), 1)
        place = data['places'][0]
        self.assertEqual(place['fund'], {
            'name': 'Светлый путь',
            'description': 'Оказываем бесплатную поддержку и помощь.',
        })
        self.assertEqual(place['category_label'], 'Ночной приют')
        self.assertEqual(place['address'], self.point.address)
        self.assertEqual({person['name'] for person in place['managers']},
                         {'Первый менеджер', 'Второй менеджер'})
        self.assertEqual(place['managers'][1]['phone'], None)
        self.assertEqual(place['manager_info']['username'], 'Первый менеджер')
        self.assertNotIn('id', place['manager_info'])
        self.assertNotIn('id', place['managers'][0])
        self.assertNotIn('user_type', json.dumps(place, ensure_ascii=False))
        self.assertEqual(place['booking'], {})

    def test_only_the_requesting_users_booking_is_shown(self):
        own = Booking(user_id=2601, homestay_id=self.point.id,
                      date_time='2026-10-19T12:00:00')
        self.assertTrue(db.insert_or_update_booking(own))
        own_view = self.client.get('/api/places', headers=self.headers(2601)).json()
        other_view = self.client.get('/api/places', headers=self.headers(2602)).json()
        self.assertEqual(own_view['places'][0]['booking']['id'], own.id)
        self.assertEqual(other_view['places'][0]['booking'], {})

    def test_booking_still_works_and_notifies_managers_without_duplicates(self):
        with patch.object(api, 'send_bot_msg', new_callable=AsyncMock) as notify:
            response = self.client.post('/api/book', json={'id_homestay': self.point.id},
                                        headers=self.headers(2601))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreater(response.json()['booking_id'], 0)
        self.assertEqual(db.get_homestay(id=self.point.id).available_beds, 2)
        recipients = [call.args[0] for call in notify.await_args_list]
        # MAX Bot.send_msg самостоятельно рассылает остальным менеджерам.
        self.assertEqual(recipients, [2603, 2601])
        conflict = self.client.post('/api/book', json={'id_homestay': self.point.id},
                                    headers=self.headers(2601))
        self.assertIn(conflict.status_code, (409, 429))

    def test_unauthed_places_denied(self):
        self.assertEqual(self.client.get('/api/places').status_code, 401)

    def test_built_client_static_modules_are_served(self):
        homepage = self.client.get('/')
        self.assertEqual(homepage.status_code, 200)
        self.assertIn('/src/main.js', homepage.text)
        self.assertEqual(self.client.get('/src/main.js').status_code, 200)
        self.assertEqual(self.client.get('/vendor/react-vendor.mjs').status_code, 200)
