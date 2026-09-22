import time
from geopy.geocoders import Nominatim

# Инициализируем один раз наружу с валидным User-Agent
geolocator = Nominatim(user_agent="HomelessnessMaxBotApp/1.0 (your-email@gmail.com)")


def normalize_address(address: str) -> str:
    """Приводит сокращения адресов к полному виду, который гарантированно понимает Nominatim"""
    # Переводим в нижний регистр для удобства замен
    addr = address.lower()

    # Словарь замен сокращений на полные слова
    replacements = {
        "пр. девят": "проспект девят",
        "пр-кт ": "проспект ",
        "ул. ": "улица ",
        "г. ": "город ",
        "пер. ": "переулок ",
        "б-р ": "бульвар ",
        " наб. ": " набережная "
    }

    for short, full in replacements.items():
        addr = addr.replace(short, full)

    # Возвращаем строку, сделав первую букву заглавной (капитализация)
    return addr.strip().capitalize()


def get_coordinates(address: str) -> tuple[float, float]:
    # 1. Очищаем от мусорных пробелов и переносов строк \n
    clean_address = " ".join(address.split()).strip()
    if not clean_address:
        return (0.0, 0.0)

    # 2. Нормализуем сокращения ("пр." -> "проспект")
    ready_address = normalize_address(clean_address)
    print(f"🔍 Отправляем в геокодер нормализованный адрес: '{ready_address}'")

    try:
        time.sleep(1.0)  # Задержка по правилам OSM
        location = geolocator.geocode(ready_address, timeout=10, language="ru")

        if location:
            print(f"✅ Успешно найдено! Координаты: {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude

    except Exception as e:
        print(f"⚠️ Ошибка сети геокодера: {e}")

    # 3. Резервный фолбек, чтобы база данных не оставалась пустой
    print(f"❌ Не удалось найти на карте даже после нормализации. Ставим дефолтный центр города.")
    if "санкт-петербург" in ready_address.lower() or "спб" in ready_address.lower():
        return (59.9343, 30.3351)  # Центр СПб
    return (55.7558, 37.6173)  # Центр Москвы
