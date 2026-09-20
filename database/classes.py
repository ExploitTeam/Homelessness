class User:
    def __init__(self, id : int = 0, username : str | None = None,
                 user_type : int = 0, phone_number : str | None = None,
                 id_homestay : int | None = None):
        self.id = id
        self.username = username
        self.user_type = user_type
        self.phone_number = phone_number
        self.id_homestay = id_homestay


class Homestay:
    def __init__(self, id : int = 0, address : str | None = None,
                 all_beds: int = 0, available_beds : int = 0,
                 open_time : str | None = None, close_time : str | None = None,
                 is_working : int = 0, additional_info : str | None = None,
                 homestay_type : int | None = None):
        self.id = id
        self.address = address
        self.all_beds = all_beds
        self.available_beds = available_beds
        self.open_time = open_time
        self.close_time = close_time
        self.is_working = is_working
        self.additional_info = additional_info
        self.homestay_type = homestay_type
