"""Безопасное форматирование ограниченного Markdown, поддерживаемого MAX."""
import re
from datetime import datetime


def format_date(value):
    """Показываем даты в удобном виде, не изменяя ISO-время в хранилище.

    Если поступил незнакомый формат, не теряем информацию.
    """
    if value is None or value == '':
        return 'Дата не указана'
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            text = str(value)
            return text.replace('T', ' ', 1) if re.match(r'^\d{4}-\d{2}-\d{2}T', text) else text
    return moment.strftime('%d.%m.%Y в %H:%M')


def escape(value):
    """Не позволяем пользовательскому имени/адресу нарушить разметку MAX."""
    return re.sub(r"([\\`*_\[\]~+^#>])", r"\\\1", str(value if value is not None else ''))


def manager_label(manager):
    # MAX ID сотрудника не предназначен для публичного просмотра.
    return manager.username or 'Сотрудник пункта'


def contact_label(manager):
    return manager.phone_number or 'Номер телефона не указан'


def point_card(point):
    from database import db_manager as db
    from database.classes import HomestayTypes
    from maxbot.functions import is_point_open
    fund = db.get_fund(point.fund_id)
    try:
        kind = HomestayTypes(point.homestay_type).label
    except (ValueError, TypeError):
        kind = 'Не указан'
    try:
        currently_open = point.is_working and is_point_open(point.open_time, point.close_time)
    except (ValueError, TypeError):
        currently_open = False
    managers = db.get_homestay_managers(point.id)
    staff = '\n'.join(f'• {escape(manager_label(m))} — {escape(contact_label(m))}' for m in managers) or 'Не назначены'
    return (f'**📍 {escape(point.address or "Адрес не указан")}**\n\n'
            f'🏛️ **Фонд:** {escape(fund["name"] if fund else "Не указан")}\n'
            f'🧭 **Категория:** {escape(kind)}\n\n'
            f'🛏️ Свободных мест: {point.available_beds}/{point.all_beds}\n'
            f'🕒 Часы работы: {escape(point.open_time or "—")}–{escape(point.close_time or "—")}\n'
            f'{"🟢 Пункт работает" if point.is_working else "🔴 Пункт не работает"}; '
            f'{"сейчас открыт" if currently_open else "сейчас закрыт"}\n\n'
            f'**📞 Контакты сотрудников:**\n{staff}\n\n'
            f'ℹ️ {escape(point.additional_info or "Дополнительная информация отсутствует")}')
