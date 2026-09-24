import parser.coordinates_finder as coordinates_finder
from enum import Enum


class HomestayTypes(Enum):
    SLEEP = 1
    HOMESTAY = 2
    SHOWER = 3
    NIGHT_BUS = 4
    PICKUP = 5
    CONSULTATION = 6

    @property
    def label(self) -> str:
        translations = {
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
                 id_homestay : int | None = None, last_booking : str | None = None):
        self.id = id
        self.username = username
        self.user_type = user_type
        self.phone_number = phone_number
        self.id_homestay = id_homestay
        self.last_booking = last_booking


    def __get_type(self):
        if self.user_type == 0:
            return "Пользователь"
        elif self.user_type == 1:
            return "Mенеджер"
        else:
            return "Администратор"

    def __str__(self):
        from database.db_manager import get_homestay
        homestay = get_homestay(self.id_homestay)
        address = ""
        if homestay:
            address = homestay.address
        return (f"🆔 {self.id}\n"
                f"👤 Username: {self.username}\n"
                f"⚡️ Тип учетной записи: {self.__get_type()}\n"
                f"📱 Телефон: {self.phone_number if self.phone_number else 'n/a'}\n"
                f"{f'📍 Привязка к точке: {address}\n' if address and self.id_homestay
                else '📍 Без привязки к точке\n' if self.user_type > 0 else ''}"
                f"🏠 Последнее бронирование: {'-' if self.last_booking is None else self.last_booking}\n")


class Homestay:
    def __init__(self, id : int = 0, address : str | None = None,
                 all_beds: int = 0, available_beds : int = 0,
                 open_time : str | None = None, close_time : str | None = None,
                 is_working : int = 0, additional_info : str | None = None,
                 homestay_type : int | None = None,
                 longtitude : float | None = None, latitude : float | None = None):
        self.id = id
        self.address = address
        self.all_beds = all_beds or 0
        self.available_beds = available_beds or 0
        self.open_time = open_time
        self.close_time = close_time
        self.is_working = is_working
        self.additional_info = additional_info
        self.homestay_type = homestay_type

        if not longtitude or not latitude:
            self.latitude, self.longtitude, _ = coordinates_finder.get_coordinates(address)
        else:
            self.latitude = latitude
            self.longtitude = longtitude
        

    def __str__(self):
        from database.db_manager import get_user
        from maxbot.functions import is_point_open
        usr = get_user(id_homestay=self.id)
        name = ""
        phone = ""
        manager = ""
        if usr:
            name = usr.username
            phone = usr.phone_number
            manager = (f"😎 Менеджер: {name if name else '-'}\n"
                       f"📱 Телефон менеджера: {phone if phone else '-'}\n")

        return (f"📍 Адрес: {self.address}\n"
                f"🔵 Тип: {HomestayTypes(self.homestay_type).label if self.homestay_type else '-'}\n"
                f"{manager}"
                f"👤 Всего мест: {self.all_beds}\n"
                f"👤 Свободно: {self.available_beds}\n"
                f"⏳ Часы работы: {self.open_time} - {self.close_time}\n"
                f"{'🟢  Работает' if self.is_working else '🔴  Не работает'}\n"
                f"{'🟢  СЕЙЧАС ОТКРЫТ\n' if is_point_open(self.open_time, self.close_time) and self.is_working
                else '🔴  СЕЙЧАС ЗАКРЫТ\n' if self.is_working else ''}"
                f"❗️ {self.additional_info if self.additional_info else 'Дополнительная информация отсутствует'}")

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