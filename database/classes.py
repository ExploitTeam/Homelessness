import parser.coordinates_finder as coordinates_finder
from enum import Enum
from datetime import datetime, timezone

class HomestayTypes(Enum):
    NO_STATED = 0
    SLEEP = 1
    HOMESTAY = 2
    SHOWER = 3
    NIGHT_BUS = 4
    PICKUP = 5
    CONSULTATION = 6

    @property
    def label(self) -> str:
        translations = {
            HomestayTypes.NO_STATED: "Не указан",
            HomestayTypes.SLEEP: "Пункт обогрева",
            HomestayTypes.HOMESTAY: "Ночной приют",
            HomestayTypes.SHOWER: "Бесплатный душ",
            HomestayTypes.NIGHT_BUS: "Ночной автобус с едой, медикаментами и соц. помощью",
            HomestayTypes.PICKUP: "Пункт выдачи одежды и средств гигиены",
            HomestayTypes.CONSULTATION: "Консультационная служба по юридическим и социальным вопросоам, выдача еды, одежды и средств гигены"
        }
        return translations[self]


class User:
    def __init__(self, id : int = 0, username : str | None = None,
                 user_type : int = 0, phone_number : str | None = None,
                 id_homestay : int | None = None, last_booking : str | None = None,
                 fund_id : int | None = None):
        self.id = id
        self.username = username
        self.user_type = user_type
        self.phone_number = phone_number
        self.id_homestay = id_homestay
        self.last_booking = last_booking
        self.fund_id = fund_id


    def __get_type(self):
        if self.user_type == 0:
            return "Пользователь"
        elif self.user_type == 1:
            return "Mенеджер"
        elif self.user_type == 2:
            return "Администратор бота"
        elif self.user_type == 3:
            return "Администратор фонда"
        return "Неизвестная роль"

    def __str__(self):
        from database.db_manager import get_manager_points, get_fund
        points = get_manager_points(self.id) if self.user_type == 1 else []
        fund = get_fund(self.fund_id) if self.fund_id else None
        return (f"🆔 {self.id}\n"
                f"👤 Имя: {self.username or '-'}\n"
                f"⚡️ Роль: {self.__get_type()}\n"
                f"📱 Телефон: {self.phone_number or 'Номер телефона не указан'}\n"
                f"{'🏛️ Фонд: ' + fund['name'] + chr(10) if fund else ''}"
                f"{'📍 Пункты: ' + ', '.join(str(p.id) + ' — ' + p.address for p in points) + chr(10) if points else ''}"
                f"🏠 Последняя бронь: {self.last_booking or '-'}")


class Homestay:
    def __init__(self, id : int = 0, address : str | None = None,
                 all_beds: int = 0, available_beds : int = 0,
                 open_time : str | None = None, close_time : str | None = None,
                 is_working : int = 0, additional_info : str | None = None,
                 homestay_type : int | None = None,
                 longtitude : float | None = None, latitude : float | None = None,
                 fund_id : int | None = None):
        self.id = id
        self.address = address
        self.all_beds = all_beds or 0
        self.available_beds = available_beds or 0
        self.open_time = open_time
        self.close_time = close_time
        self.is_working = is_working
        self.additional_info = additional_info
        self.homestay_type = homestay_type
        self.fund_id = fund_id

        # Не выполняем сетевые запросы при каждом чтении существующей записи.
        if id == 0 and (longtitude is None or latitude is None) and address:
            self.latitude, self.longtitude, _ = coordinates_finder.get_coordinates(address)
        else:
            self.latitude = latitude
            self.longtitude = longtitude
        

    def __str__(self):
        from database.db_manager import get_homestay_managers, get_fund
        from maxbot.functions import is_point_open
        managers = get_homestay_managers(self.id)
        fund = get_fund(self.fund_id)
        manager_text = "\n".join(
            f"😎 {manager.username or 'Сотрудник пункта'}, телефон: {manager.phone_number or 'Номер телефона не указан'}"
            for manager in managers
        ) or "Не назначены"
        try:
            opened = is_point_open(self.open_time, self.close_time)
        except (ValueError, TypeError):
            opened = False
        return (f"🏛️ Фонд: {fund['name'] if fund else '-'}\n"
                f"📍 Адрес: {self.address}\n"
                f"🔵 Тип: {HomestayTypes(self.homestay_type).label if self.homestay_type in [t.value for t in HomestayTypes] else '-'}\n"
                f"👥 Менеджеры: {manager_text}\n"
                f"👤 Всего мест: {self.all_beds}\n"
                f"👤 Свободно: {self.available_beds}\n"
                f"⏳ Часы работы: {self.open_time} - {self.close_time}\n"
                f"{'🟢 Работает' if self.is_working else '🔴 Не работает'}\n"
                f"{'🟢 Сейчас открыто' if opened and self.is_working else '🔴 Сейчас закрыто'}\n"
                f"❗️ {self.additional_info or 'Дополнительная информация отсутствует'}")

    def to_json(self):
        return {
            "id": self.id,
            "address": self.address,
            "all_beds": self.all_beds,
            "available_beds": self.available_beds,
            "open_time": self.open_time,
            "close_time": self.close_time,
            "is_working": self.is_working ,
            "additional_info": self.additional_info,
            "homestay_type": self.homestay_type,
            "longtitude": self.longtitude,
            "latitude": self.latitude,
        }


class Booking:
    def __init__(self, id : int = 0, user_id : int | None = None,
                 homestay_id : int | None = None, date_time : str | None = None,
                 is_approved : int = 0):
        self.id = id
        self.user_id = user_id
        self.homestay_id = homestay_id
        self.date_time = date_time
        self.is_approved = is_approved

    def to_json(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "homestay_id": self.homestay_id,
            "date_time": self.date_time,
            "is_approved": self.is_approved
        }

    def booking_age(self):
        if not self.date_time:
            return None
        created = datetime.fromisoformat(self.date_time)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created


    def __str__(self):
        from database.db_manager import get_homestay, get_homestay_managers
        homestay = get_homestay(id=self.homestay_id)
        address = homestay.address if homestay else "Пункт удалён"
        managers = get_homestay_managers(self.homestay_id)
        manager_text = "; ".join(f"{m.username or 'Сотрудник пункта'} ({m.phone_number or 'Номер телефона не указан'})" for m in managers) or "не назначены"
        return (f"ID бронирования: {self.id}\n"
                f"Дата: {self.date_time}\n"
                f"📍 Адрес: {address}\n"
                f"👥 Менеджеры: {manager_text}\n"
                f"{'🟢 Подтверждено' if self.is_approved else '🟠 Ожидает подтверждения'}")
