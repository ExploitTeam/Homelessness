import ssl

from langchain_gigachat import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from os import getenv
from dotenv import load_dotenv
import json

load_dotenv()

model = GigaChat(
    credentials=getenv("GIGA_API_KEY"),
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2",
    verify_ssl_certs=True,
    ssl_context=ssl.create_default_context(cafile="maxbot/Russian_Trusted_CA.pem"),
    temperature=0,
)

def parse_html(html_page):
    with open("parser/sys_prompt.md", encoding="utf-8") as prompt:
        system_prompt = prompt.read()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=html_page),
    ]

    giga_response = model.invoke(messages)
    response_text = giga_response.content

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as error:
        print("GigaChat вернул некорректный JSON:")
        print(response_text)
        raise ValueError("Ответ GigaChat не является корректным JSON") from error


    return result

    