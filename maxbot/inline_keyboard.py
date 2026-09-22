from enum import Enum

class button_types(Enum):
    callback = 'callback'
    link = 'link'
    request_contact = 'request_contact'
    request_geo_location = 'request_geo_location'
    open_app = "open_app"
    message = "message"
    clipboard = "clipboard"

class InlineKeyboardMarkup:
    def __init__(self):
        self.keyboard = []
    def add_button(self,
                   name : str,
                   type : button_types,
                   payload : str = "",
                   url : str = ""):
        dt = dict()
        if name:
            dt['text'] = name
        if type:
            dt['type'] = type.value
        if payload:
            dt['payload'] = payload
        if url:
            dt['url'] = url
        self.keyboard.append([
            dt
        ])