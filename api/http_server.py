from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database.db_manager import *

app = FastAPI(title="HOMELESSNESS API")

@app.get("/places/{user_id}")
async def info(user_id : int):
    longitude, latitude, address  = "", "", ""
    all_beds, available_beds, open_time, close_time, additional_info = "", "", "", "", ""
    homestay_type = ""
    is_working = True
    id = 0
    return {
        "user_id": user_id,
        "places" : [
            {
                "id" : id,
                "longitude" : longitude,
                "latitude" : latitude,
                "address" : address,
                "all_beds" : all_beds,
                "available_beds" : available_beds,
                "open_time" : open_time,
                "close_time" : close_time,
                "additional_info" : additional_info,
                "is_working" : is_working,
                "homestay_type" : homestay_type
            },
        ]
    }

class BookingRequest(BaseModel):
    user_id: int
    id_homestay: int

@app.post("/book")
async def book(user_id : int):
    pass