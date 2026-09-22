import json
import time
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_last_request_time = 0.0


@lru_cache(maxsize=256)
def get_coordinates(address: str) -> tuple[float, float] | None:
    """
    Возвращает координаты места по его адресу.

    Параметры:
        address: адрес в виде строки.

    Возвращает:
        tuple[float, float] | tuple[None, None]:
        Кортеж (долгота, широта), если место найдено.
        Кортеж (None, None), если место не найдено или произошла ошибка.

    Пример:
        latitude, longitude = get_coordinates(
            "Красная площадь, Москва"
        )
    """

    global _last_request_time

    if not address or not address.strip():
        raise ValueError("Адрес не может быть пустым.")

    # Nominatim ограничивает публичный API максимум одним запросом в секунду.
    elapsed = time.monotonic() - _last_request_time

    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    params = urlencode({
        "q": address,
        "format": "jsonv2",
        "limit": 1,
        "accept-language": "ru",
    })

    url = f"https://nominatim.openstreetmap.org/search?{params}"

    # User-Agent обязателен для публичного Nominatim API.
    request = Request(
        url,
        headers={
            "User-Agent": "MyGeocoder/1.0"
        }
    )

    try:
        _last_request_time = time.monotonic()

        with urlopen(request, timeout=10) as response:
            data = json.load(response)

    except HTTPError as error:
        print(f"HTTP ошибка: {error.code} {error.reason}")
        return (None, None)

    except URLError as error:
        print(f"Ошибка подключения: {error.reason}")
        return (None, None)

    except TimeoutError:
        print("Превышено время ожидания.")
        return (None, None)

    if not data:
        return (None, None)

    result = data[0]

    longitude = float(result["lon"])
    latitude = float(result["lat"])

    return latitude, longitude
