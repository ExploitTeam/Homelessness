"""Проверки навигации v3 и понятного представления дат/геолокации."""
import asyncio
import json
import unittest
from unittest.mock import patch

import test_multifund as fixtures
from test_multifund import callback
from database import db_manager as db
from database.classes import User
from maxbot.functions import do_on_start
from maxbot.fund_settings import fund_panel, show_fund
from maxbot.homestay_settings import point_fund, edit_user_button_pressed, choose_create_fund, create_input_address, create_input_beds
from maxbot.bookings_settings import _history_view, _active_user_view, _staff_booking_view
from maxbot.bot_manager import _render_geo_results, _build_geo_results_text
from maxbot.formatting import format_date, point_card


class FakeBot:
    def __init__(self):
        self.sent = []
        self.edited = []
        self.steps = {}

    async def send_msg(self, uid, text, keyboard=None, **kwargs):
        self.sent.append((uid, text, keyboard, kwargs))

    async def edit_msg(self, mid, text, keyboard=None, **kwargs):
        self.edited.append((mid, text, keyboard, kwargs))

    def set_next_step(self, uid, value):
        self.steps[uid] = value

    def get_next_step(self, uid):
        return self.steps.get(uid)

    def clear_next_step(self, uid):
        self.steps.pop(uid, None)


def flatten_buttons(record):
    return [button for row in record[2] or [] for button in row]


def click_payload(button):
    try:
        return json.loads(button.get('payload', '{}'))
    except (TypeError, ValueError):
        return button.get('payload')


class NavigationAndDatesTests(unittest.TestCase):
    setUp = fixtures.MultiFundTests.setUp
    tearDown = fixtures.MultiFundTests.tearDown
    booking = fixtures.MultiFundTests.booking

    def test_main_menu_admins_manager_and_normal(self):
        for user in (self.global_admin, self.admin_a, self.manager_a, self.normal):
            fake = FakeBot()
            asyncio.run(do_on_start(fake, {'user_id': user.id, 'first_name': user.username or ''}))
            labels = [b['text'] for b in flatten_buttons(fake.sent[-1])]
            self.assertNotIn('🕘 История моих броней', labels)
            self.assertIn('📋 Мои бронирования', labels)
            self.assertEqual('🏛️ Фонды' in labels, user.id in (110, 111))
            self.assertEqual('🏠 Управление пунктами' in labels, user.id == 113)
        _, booking_keyboard = _active_user_view(self.normal, 1)
        self.assertTrue(any('История' in b['text'] for row in booking_keyboard.keyboard for b in row))

    def test_admin_route_uses_funds_and_own_scopes(self):
        for user_id, expected in ((110, {'Фонд А', 'Фонд Б'}), (111, {'Фонд А'})):
            fake = FakeBot()
            asyncio.run(fund_panel(callback(user_id, 'funds_panel'), fake))
            buttons = flatten_buttons(fake.edited[-1])
            self.assertEqual({b['text'].removeprefix('🏛️ ') for b in buttons if b['text'].startswith('🏛️ ')}, expected)
        fake = FakeBot()
        asyncio.run(show_fund(callback(111, 'fund_show', fund=self.f1), fake))
        buttons = flatten_buttons(fake.edited[-1])
        go = next(b for b in buttons if b['text'] == '🏠 Управление пунктами')
        self.assertEqual(click_payload(go), {'command': 'point_fund', 'fund': self.f1})
        asyncio.run(point_fund(callback(111, 'point_fund', fund=self.f1), fake))
        buttons = flatten_buttons(fake.edited[-1])
        self.assertEqual(click_payload(buttons[0]), {'command': 'fund_show', 'fund': self.f1})
        self.assertIn('Точка А', ' '.join(b['text'] for b in buttons))
        self.assertNotIn('Точка Б', ' '.join(b['text'] for b in buttons))
        # Кнопка старой версии у администратора больше не открывает отдельный раздел.
        asyncio.run(edit_user_button_pressed(callback(111, 'old'), fake))
        self.assertIn('Управление фондами', fake.edited[-1][1])
        fake_other = FakeBot()
        asyncio.run(point_fund(callback(111, 'point_fund', fund=self.f2), fake_other))
        self.assertEqual(fake_other.edited, [])
        self.assertTrue(any('Недостаточно прав' in t for _, t, _, _ in fake_other.sent))
        asyncio.run(point_fund(callback(110, 'point_fund', fund=self.f2), fake))
        self.assertIn('Точка Б', ' '.join(b['text'] for b in flatten_buttons(fake.edited[-1])))

    def test_manager_without_points_gets_explanation_instead_of_error(self):
        fake = FakeBot()
        asyncio.run(edit_user_button_pressed(callback(113, 'edit_homestay'), fake))
        self.assertIn('не привязаны', fake.edited[-1][1])
        self.assertEqual(fake.sent, [])

    def test_manager_still_has_his_own_point_menu(self):
        self.assertTrue(db.assign_manager(self.p1.id, self.manager_a.id))
        fake = FakeBot()
        asyncio.run(edit_user_button_pressed(callback(113, 'edit_homestay'), fake))
        buttons = flatten_buttons(fake.edited[-1])
        self.assertTrue(any('Фонд А' in b['text'] for b in buttons))
        self.assertFalse(any('Фонд Б' in b['text'] for b in buttons))
        asyncio.run(point_fund(callback(113, 'point_fund', fund=self.f1), fake))
        buttons = flatten_buttons(fake.edited[-1])
        self.assertEqual(buttons[0]['payload'], 'edit_homestay')
        self.assertFalse(any(b['text'] == '➕ Создать пункт' for b in buttons))

    def test_new_point_back_navigation_keeps_fund_context(self):
        fake = FakeBot()
        asyncio.run(choose_create_fund(callback(111, 'choose_create_fund', fund=self.f1), fake))
        self.assertEqual(click_payload(flatten_buttons(fake.edited[-1])[0]),
                         {'command': 'point_fund', 'fund': self.f1})
        data = {'message': {'sender': {'user_id': 111}, 'body': {'text': 'Тестовая улица'}}}
        asyncio.run(create_input_address(data, fake))
        self.assertEqual(click_payload(flatten_buttons(fake.sent[-1])[0]),
                         {'command': 'point_fund', 'fund': self.f1})
        self.assertEqual(json.loads(fake.get_next_step(111))['fund_id'], self.f1)

    def test_create_point_success_returns_to_selected_fund(self):
        fake = FakeBot()
        fake.set_next_step(111, json.dumps({'command': 'create_input_beds',
                                             'fund_id': self.f1, 'address': 'Новый пункт'}))
        data = {'message': {'sender': {'user_id': 111},
                            'body': {'text': '3'}}}
        # Не обращаемся к геокодеру в тестах.
        with patch('maxbot.homestay_settings.coordinates_finder.get_coordinates',
                   return_value=(55.75, 37.62, True)):
            asyncio.run(create_input_beds(data, fake))
        self.assertEqual(click_payload(flatten_buttons(fake.sent[-1])[0]),
                         {'command': 'point_fund', 'fund': self.f1})
        self.assertIsNone(fake.get_next_step(111))
        newly_created = [h for h in db.get_all_homestays() if h.address == 'Новый пункт']
        self.assertEqual(len(newly_created), 1)
        self.assertEqual(newly_created[0].fund_id, self.f1)

    def test_geo_result_markdown_and_separators_keep_nearest_first(self):
        points = [db.get_homestay(self.p1.id), db.get_homestay(self.p2.id)]
        result = _build_geo_results_text(points, [], 1, 1, 2)
        self.assertIn('**📍 Ближайшие пункты помощи**\n\n', result)
        self.assertIn('🏛️ **Фонд:** Фонд А\n', result)
        self.assertIn('🏛️ **Фонд:** Фонд Б\n', result)
        self.assertIn('🧭 **Категория:**', result)
        self.assertIn('\n\n🏛️ **Фонд:**', result)
        self.assertLess(result.index('Точка А'), result.index('Точка Б'))
        text, keyboard, page = _render_geo_results([self.p2.id, self.p1.id], [], 1)
        self.assertLess(text.index('Точка Б'), text.index('Точка А'))
        self.assertEqual(page, 1)
        self.assertTrue(keyboard.keyboard)
        self.assertIn('**📞 Контакты сотрудников:**', point_card(points[0]))

    def test_dates_formatted_in_every_booking_surface_without_db_update(self):
        booking = self.booking()
        self.assertEqual(format_date('2026-10-19T17:08:20'), '19.10.2026 в 17:08')
        self.assertEqual(format_date('2026-10-19 17:08:20'), '19.10.2026 в 17:08')
        self.assertEqual(format_date('2026-10-19T17:08:20+00:00'), '19.10.2026 в 17:08')
        self.assertEqual(format_date(None), 'Дата не указана')
        self.assertIn('Дата: 19.10.2026 в 12:00', str(booking))
        self.assertNotIn('2026-10-19T', str(booking))
        active, _ = _active_user_view(self.normal, 1)
        staff, _ = _staff_booking_view(self.p1.id, 1)
        for text in (active, staff):
            self.assertIn('19.10.2026 в 12:00', text)
            self.assertNotIn('2026-10-19T', text)
        self.assertTrue(db.delete_booking(booking, reason='cancelled'))
        history, _ = _history_view(self.normal, 1)
        self.assertIn('19.10.2026 в 12:00', history)
        self.assertNotIn('2026-10-19T', history)
        self.normal.last_booking = '2026-10-19T17:08:20'
        self.assertIn('Последняя бронь: 19.10.2026 в 17:08', str(self.normal))
        self.assertEqual(db.get_booking_history(user_id=self.normal.id)[0]['date_time'],
                         '2026-10-19T12:00:00')


if __name__ == '__main__':
    unittest.main()
