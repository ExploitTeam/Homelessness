import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_last_request_time = 0.0
MOSCOW_CENTER = (55.7558, 37.6173)


def _extract_house(text: str) -> str:
    raw = (text or "").lower().replace(" ", "")
    raw = (
        raw.replace("корпус", "к")
        .replace("корп.", "к")
        .replace("к.", "к")
        .replace("строение", "с")
        .replace("стр.", "с")
    )
    matches = re.findall(r"\d+[а-яa-z]?(?:к\d+)?(?:с\d+)?", raw)
    return matches[-1] if matches else ""


def _houses_equal(wanted: str, got: str) -> bool:
    if not wanted or not got:
        return False
    return _extract_house(wanted) == _extract_house(got)


def get_coordinates(address: str, city: str | None = None) -> tuple[float, float, bool] | None:
    global _last_request_time
    from parser.neural_network import clear_address

    if not address or not address.strip():
        raise ValueError("Адрес не может быть пустым.")

    #address = clear_address(address)
    elapsed = time.monotonic() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    query = address.strip()
    if city and city.lower() not in query.lower():
        query = f"{city}, {query}"

    wanted_house = _extract_house(query)
    needle = (city or "").lower()

    params = urlencode({
        "q": query,
        "format": "jsonv2",
        "limit": 10,
        "addressdetails": 1,
        "accept-language": "ru",
        "countrycodes": "ru",
    })
    request = Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "HomelessnessHelper/1.0 (contact: admin@homelessness.bot.nu)"},
    )
    _last_request_time = time.monotonic()
    with urlopen(request, timeout=10) as response:
        data = json.load(response)

    if not data:
        return (*MOSCOW_CENTER, False)

    exact = []
    for item in data:
        addr = item.get("address") or {}
        house = addr.get("house_number") or ""
        name = (item.get("display_name") or "").lower()
        place_city = (addr.get("city") or addr.get("town") or addr.get("village") or "").lower()

        if needle and needle not in name and needle not in place_city:
            continue
        if wanted_house and not _houses_equal(wanted_house, house):
            continue
        exact.append(item)

    if not exact:
        return (*MOSCOW_CENTER, False)

    best = exact[0]
    return float(best["lat"]), float(best["lon"]), True