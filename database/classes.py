import parser.coordinate_finder_v2 as coordinates_finder_v2
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
                f"📍 Привязка к точке: {address if address else 'без привязки'}\n"
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
        self.all_beds = all_beds
        self.available_beds = available_beds
        self.open_time = open_time
        self.close_time = close_time
        self.is_working = is_working
        self.additional_info = additional_info
        self.homestay_type = homestay_type

        if longtitude is None and latitude is None:
            self.latitude, self.longtitude, _ = coordinates_finder_v2.get_coordinates(address)
        else:
            self.latitude = latitude
            self.longtitude = longtitude
        

    def __str__(self):
        from database.db_manager import get_user
        usr = get_user(id_homestay=self.id)
        name = ""
        if usr:
            name = usr.username
        return (f"📍 Адрес: {self.address}\n"
                f"🔵 Тип: {HomestayTypes.homestay_type.label if self.homestay_type else '-'}\n"
                f"😎 Менеджер: {name if name else 'n/a'}\n"
                f"👤 Всего мест: {self.all_beds}\n"
                f"👤 Свободно: {self.available_beds}\n"
                f"⏳ Часы работы: {self.open_time} - {self.close_time}\n"
                f"{'🟢  Работает' if self.is_working else '🔴  Закрыто'}\n"
                f"❗️ Дополнительная информация: {self.additional_info if self.additional_info else 'отсутствует'}\n") # Дописать!!!!

