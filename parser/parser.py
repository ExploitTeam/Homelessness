from os import getenv
from dotenv import load_dotenv
import re
import requests
from bs4 import BeautifulSoup
import json


load_dotenv()
parse_url = getenv("PARSE_URL", "")

# Заголовки для эмуляции запроса от браузера
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Список URL для парсинга
PROJECTS = {
    "Ночной приют": "https://homeless.ru/projects/54449/",
    "Пункт обогрева": "https://homeless.ru/projects/1077259/",
}


def parse_cards_section(soup: BeautifulSoup) -> list:
    """Парсит блок с карточками адресов .cards-container .card."""
    cards_data = []
    cards = soup.select(".cards-container .card")

    for card in cards:
        # 1. Извлекаем номер
        count_tag = card.select_one(".count")
        count = count_tag.get_text(strip=True) if count_tag else ""

        # 2. Извлекаем текст из параграфа <p>
        p_tag = card.find("p")
        if not p_tag:
            continue

        raw_text = " ".join(p_tag.get_text().split())

        # 3. Отделяем адрес от даты конца работы (например, "до 15 апреля")
        match = re.search(r"^(.*?)(?:\s+(до\s+\d+\s+\w+))?$", raw_text)
        if match:
            address = match.group(1).strip()
            until_date = match.group(2) if match.group(2) else None
        else:
            address = raw_text
            until_date = None

        cards_data.append(
            {"number": count, "address": address, "until_date": until_date}
        )

    return cards_data


def parse_general_text(soup: BeautifulSoup) -> dict:
    """Поиск информации в обычном тексте (для страниц без карточек)."""
    addresses = set()
    schedules = set()

    keywords = re.compile(
        r"Адрес|Режим работы|Часы работы|Сезон работы", re.IGNORECASE
    )

    for text_node in soup.find_all(string=keywords):
        parent = text_node.parent
        container = parent.find_parent(["div", "li", "section", "p"]) or parent
        clean_text = " ".join(container.get_text().split())

        if re.search(r"Адрес", text_node, re.IGNORECASE):
            addresses.add(clean_text)
        elif re.search(r"Режим|Часы|Сезон", text_node, re.IGNORECASE):
            schedules.add(clean_text)

    return {"addresses": list(addresses), "schedules": list(schedules)}


def parse_project_page(url: str) -> dict:
    """Загружает страницу и собирает всю доступную информацию."""
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Название проекта
    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Без названия"

    # 2. Описание сезона/условий (например, <h4> внутри .conditions-cards)
    season_header_tag = soup.select_one(".conditions-cards h4")
    season_info = (
        season_header_tag.get_text(strip=True) if season_header_tag else None
    )

    # 3. Парсинг карточек адресов
    cards = parse_cards_section(soup)

    # 4. Общий парсинг по тексту (резервный)
    general_info = parse_general_text(soup)

    return {
        "url": url,
        "title": title,
        "season_info": season_info,
        "cards_addresses": cards,
        "general_addresses": general_info["addresses"],
        "general_schedules": general_info["schedules"],
    }


def main():
    all_projects_data = []

    for name, url in PROJECTS.items():
        print(f"Парсинг: {name} ({url})...")
        try:
            data = parse_project_page(url)
            all_projects_data.append(data)
        except Exception as e:
            print(f"Ошибка при обработке {url}: {e}")

    # Красивый вывод результатов
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ПАРСИНГА:")
    print("=" * 60 + "\n")

    for project in all_projects_data:
        print(f"📌 Проект: {project['title']}")
        print(f"🔗 URL: {project['url']}")

        if project["season_info"]:
            print(f"ℹ️  Сезон: {project['season_info']}")

        if project["cards_addresses"]:
            print("\n  🏢 Найденные адреса (из карточек):")
            for card in project["cards_addresses"]:
                date_str = (
                    f" [{card['until_date']}]" if card["until_date"] else ""
                )
                print(f"   • {card['number']} {card['address']}{date_str}")

        if project["general_addresses"]:
            print("\n  📍 Найденные адреса (из текста):")
            for addr in project["general_addresses"]:
                print(f"   • {addr}")

        if project["general_schedules"]:
            print("\n  ⏰ График работы (из текста):")
            for sched in project["general_schedules"]:
                print(f"   • {sched}")

        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()