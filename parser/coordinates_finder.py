import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
_last_request_time = 0.0


def get_coordinates(address: str, city: str | None = None) -> tuple[float, float, bool] | None:
    global _last_request_time
    from parser.neural_network import clear_address
    if not address or not address.strip():
        raise ValueError("Адрес не может быть пустым.")
    address = clear_address(address)
    elapsed = time.monotonic() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    query = address.strip()
    if city and city.lower() not in query.lower():
        query = f"{city}, {query}"

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
        return 55.7558, 37.6173, False

    needle = (city or "").lower()

    def score(item: dict) -> int:
        name = (item.get("display_name") or "").lower()
        addr = item.get("address") or {}
        points = 0
        if needle and needle in name:
            points += 10
        if needle and needle in (addr.get("city") or addr.get("town") or "").lower():
            points += 10
        if item.get("class") == "building" or item.get("type") in {"house", "apartments"}:
            points += 3
        return points

    best = max(data, key=score)
    if city and score(best) < 10:
        # город в запросе есть, но среди ответов его нет — лучше не врать
        return 55.7558, 37.6173, False

    return float(best["lat"]), float(best["lon"]), True