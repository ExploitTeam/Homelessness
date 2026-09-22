import time
from geopy.geocoders import Nominatim

# Инициализируем один раз наружу с валидным User-Agent
geolocator = Nominatim(user_agent="HomelessnessMaxBotApp/1.0 (your-email@gmail.com)")


def normalize_address(address: str) -> str:
    """Улучшенная очистка адреса для гарантированного поиска в OSM"""
    addr = " ".join(address.lower().split()).strip()
    garbage_words = ["город ", "г. ", "область ", "обл. "]
    for word in garbage_words:
        if addr.startswith(word):
            addr = addr[len(word):].strip()

    replacements = {
        "пр. девят": "проспект девят",
        "пр-кт ": "проспект ",
        "ул. ": "улица ",
        "пер. ": "переулок ",
        "б-р ": "бульвар ",
        " наб. ": " набережная "
    }
    for short, full in replacements.items():
        addr = addr.replace(short, full)
    if "," not in addr:
        if addr.startswith("москва "):
            addr = addr.replace("москва ", "москва, ", 1)
        elif addr.startswith("санкт-петербург "):
            addr = addr.replace("санкт-петербург ", "санкт-петербург, ", 1)

    return addr.strip().capitalize()


def get_coordinates(address: str) -> tuple[float, float]:
    clean_address = " ".join(address.split()).strip()
    if not clean_address:
        return (0.0, 0.0)

    ready_address = normalize_address(clean_address)
    print(f"🔍 Отправляем в геокодер нормализованный адрес: '{ready_address}'")

    try:
        time.sleep(1.0)
        location = geolocator.geocode(ready_address, timeout=10, language="ru")

        if location:
            print(f"✅ Успешно найдено! Координаты: {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude

    except Exception as e:
        print(f"⚠️ Ошибка сети геокодера: {e}")

    print(f"❌ Не удалось найти на карте даже после нормализации. Ставим дефолтный центр города.")
    if "санкт-петербург" in ready_address.lower() or "спб" in ready_address.lower():
        return (59.9343, 30.3351)  # Центр СПб
    return (55.7558, 37.6173)  # Центр Москвы
