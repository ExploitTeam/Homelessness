from urllib.request import Request, urlopen
from database import db_manager, classes
import parser.neural_network as neural_network


def download_html(url: str) -> str:
    """Скачивает HTML-код страницы и возвращает его в виде строки."""

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urlopen(request, timeout=60) as response:
        html = response.read()

    return html.decode("utf-8")


def proceed_parsing():
     with open("parser/sites_to_parse.txt") as sites:
         for site in sites.readlines():
            try:
                html_code = download_html(site.strip())

                result = neural_network.parse_html(html_code)

                for key in result:
                    current_homestay = result[key]
                    if not current_homestay["address"]:
                        continue
                    open_time, close_time = "", ""
                    additional_info = f"{current_homestay["homestay_type"]}. {current_homestay["work_months"]}."
                    if current_homestay["work_time"] != "":
                        open_time, close_time = current_homestay["work_time"].split("-")

                    homestay_object = classes.Homestay(address = current_homestay["address"],
                                                       open_time = open_time,
                                                       close_time = close_time,
                                                       additional_info = additional_info
                                                    )

                    db_manager.insert_or_update_homestay(homestay_object)
            except Exception as e:
                pass
