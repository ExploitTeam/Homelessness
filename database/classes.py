class User:
    def __init__(self, id=0, username=None, type=0, id_homestay=0):
        self.id = id
        self.username = username
        self.type = type
        self.id_homestay = id_homestay

class Homestay:
    def __init__(self, id=0, address=None, max_people=0, current=0, time_work=None, is_open=False):
        self.id = id
        self.address = address
        self.max_people = max_people
        self.current = current
        self.time_work = time_work
        self.is_open = is_open