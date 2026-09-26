import warnings

from database.classes import Homestay, User, Booking
from database.info import info
import sqlite3
from os import getenv
from dotenv import load_dotenv
import json
from urllib.parse import urlencode
from urllib.request import urlopen

load_dotenv()
database_name = f"{getenv('DB_NAME', 'default')}.db"


def initialize_database():
    """Используется для первоначальной инициализации БД."""

    with sqlite3.connect(database_name) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS homestays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                all_beds INTEGER NOT NULL,
                available_beds INTEGER DEFAULT 0,
                open_time TEXT NOT NULL DEFAULT "",
                close_time TEXT NOT NULL DEFAULT "",
                is_working INTEGER DEFAULT 0,
                additional_info TEXT,
                homestay_type INT DEFAULT 0,
                longtitude REAL,
                latitude REAL
            )
        """)
        try:
            cursor.execute("""
                ALTER TABLE homestays ADD COLUMN longtitude REAL;
            """)
        except Exception as e:
            print("Error adding column longtitude", e)
        try:
            cursor.execute("""
                ALTER TABLE homestays ADD COLUMN latitude REAL;
            """)
        except Exception as e:
            print("Error adding column latitude", e)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                user_type INTEGER DEFAULT 0,
                phone_number TEXT,
                id_homestay INTEGER,
                last_booking TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                homestay_id INTEGER,
                date_time TEXT NOT NULL,
                is_approved INTEGER DEFAULT 0,

                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (homestay_id) REFERENCES homestays(id)
            )
        """)    

        #Обновление точек:
        for i in get_all_homestays():
            insert_or_update_homestay(i)
        info("База данных инициализирована. ")


def get_user(id: int | None = None,
             username: str | None = None,
             id_homestay: int | None = None) -> User | None:
    """Используется для получения пользователя из БД по ключам или без них."""

    with sqlite3.connect(database_name) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        conditions = []
        parameters = []

        if id is not None:
            conditions.append("id = ?")
            parameters.append(id)

        if username is not None:
            conditions.append("username = ?")
            parameters.append(username)

        if id_homestay is not None:
            conditions.append("id_homestay = ?")
            parameters.append(id_homestay)

        if not conditions:
            return None

        query = f"""
            SELECT 
                id,
                username,
                user_type,
                phone_number,
                id_homestay,
                last_booking
            FROM users
            WHERE {" AND ".join(conditions)}
        """

        cursor.execute(query, parameters)

        row = cursor.fetchone()

        if row is None:
            return None

        return User(
            id=row[0],
            username=row[1],
            user_type=row[2],
            phone_number=row[3],
            id_homestay=row[4],
            last_booking=row[5]
        )


def get_homestay(id : int | None = None,
                 address: str | None = None,
                 is_working : int | None = None) -> Homestay | None:
    """Используется для получения ночлега из БД по ключам или без них."""

    with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            conditions = []
            parameters = []

            if id is not None:
                conditions.append("id = ?")
                parameters.append(id)

            if address is not None:
                conditions.append("address = ?")
                parameters.append(address)

            if is_working is not None:
                conditions.append("is_working = ?")
                parameters.append(is_working)

            if not conditions:
                return None

            query = f"""
                SELECT
                    id,
                    address,
                    all_beds,
                    available_beds,
                    open_time,
                    close_time,
                    is_working,
                    additional_info,
                    homestay_type,
                    longtitude,
                    latitude
                FROM homestays
                WHERE {" AND ".join(conditions)}
            """

            cursor.execute(query, parameters)

            row = cursor.fetchone()

            if row is None:
                return None

            return Homestay(
                id=row[0],
                address=row[1],
                all_beds=row[2],
                available_beds=row[3],
                open_time=row[4],
                close_time=row[5],
                is_working=row[6],
                additional_info=row[7],
                homestay_type=row[8],
                longtitude=row[9],
                latitude=row[10]
            )


def get_booking(id: int | None = None) -> Booking | None:
    with sqlite3.connect(database_name) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        if id is None:
            return None


        query = """
            SELECT 
                id,
                user_id,
                homestay_id,
                date_time,
                is_approved
            FROM bookings
            WHERE id = ?
        """

        cursor.execute(query, (id,))

        row = cursor.fetchone()

        if row is None:
            return None

        return Booking(
            id = row[0],
            user_id = row[1],
            homestay_id = row[2],
            date_time = row[3],
            is_approved = row[5],
        )


def insert_or_update_user(user : User | None = None) -> bool:
    """Добавление или изменения пользователя в БД."""

    if user is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (
                    id,
                    username,
                    user_type,
                    phone_number,
                    id_homestay,
                    last_booking
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    username = excluded.username, 
                    user_type = excluded.user_type,
                    phone_number = excluded.phone_number,
                    id_homestay = excluded.id_homestay,
                    last_booking = excluded.last_booking
            """, (
                user.id,
                user.username,
                user.user_type,
                user.phone_number,
                user.id_homestay,
                user.last_booking
            ))
        return True

    except sqlite3.Error:
        return False


def insert_or_update_homestay(homestay : Homestay | None = None) -> bool:
    """Добавление или изменения пользователя в БД."""

    if homestay is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            if homestay.id == 0:
                cursor.execute("""
                    INSERT INTO homestays (
                        address,
                        all_beds,
                        available_beds,
                        open_time,
                        close_time,
                        is_working,
                        additional_info,
                        homestay_type,
                        longtitude,
                        latitude
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    homestay.address,
                    homestay.all_beds,
                    homestay.available_beds,
                    homestay.open_time,
                    homestay.close_time,
                    homestay.is_working,
                    homestay.additional_info,
                    homestay.homestay_type,
                    homestay.longtitude,
                    homestay.latitude
                ))

                homestay.id = cursor.lastrowid

                return True

            else:
                cursor.execute("""
                    UPDATE homestays
                    SET
                        address = ?,
                        all_beds = ?,
                        available_beds = ?,
                        open_time = ?,
                        close_time = ?,
                        is_working = ?,
                        additional_info = ?,
                        homestay_type = ?,
                        longtitude = ?,
                        latitude = ?
                    WHERE id = ?
                """, (
                    homestay.address,
                    homestay.all_beds,
                    homestay.available_beds,
                    homestay.open_time,
                    homestay.close_time,
                    homestay.is_working,
                    homestay.additional_info,
                    homestay.homestay_type,
                    homestay.longtitude,
                    homestay.latitude,
                    homestay.id
                ))

                return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def insert_or_update_booking(booking : Booking | None = None) -> bool:
    if booking is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO bookings (
                    id,
                    user_id,
                    homestay_id,
                    date_time,
                    is_approved
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    user_id = excluded.user_id, 
                    homestay_id = excluded.homestay_id,
                    date = excluded.date,
                    time = excluded.time,
                    is_approved = excluded.is_approved
            """, (
                booking.id,
                booking.user_id,
                booking.homestay_id,
                booking.date_time,
                booking.is_approved,
            ))
        return True

    except sqlite3.Error:
        return False


def get_all_homestays() -> list[Homestay]:
    """Возвращает список всех ночлегов из БД."""

    with sqlite3.connect(database_name) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                address,
                all_beds,
                available_beds,
                open_time,
                close_time,
                is_working,
                additional_info,
                homestay_type,
                longtitude,
                latitude
            FROM homestays
        """)

        rows = cursor.fetchall()

        return [
            Homestay(
                id=row[0],
                address=row[1],
                all_beds=row[2],
                available_beds=row[3],
                open_time=row[4],
                close_time=row[5],
                is_working=row[6],
                additional_info=row[7],
                homestay_type=row[8],
                longtitude=row[9],
                latitude=row[10]
            )
            for row in rows
        ]


def get_user_bookings(user : User | None = None) -> list[Booking]:
    if user is None:
        return []

    with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
    
            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    homestay_id,
                    date_time,
                    is_approved
                FROM bookings
                WHERE user_id = ?
            """, (user.id,))
    
            rows = cursor.fetchall()
    
            return [
                Booking(
                    id = row[0],
                    user_id = row[1],
                    homestay_id = row[2],
                    date_time = row[3],
                    is_approved = row[5],
                )
                for row in rows
            ]


def get_homestay_bookings(homestay : Homestay | None = None) -> list[Booking]:
    if homestay is None:
        return []

    with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
    
            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    homestay_id,
                    date_time,
                    is_approved
                FROM bookings
                WHERE homestay_id = ?
            """, (homestay.id,))
    
            rows = cursor.fetchall()
    
            return [
                Booking(
                    id = row[0],
                    user_id = row[1],
                    homestay_id = row[2],
                    date_time = row[3],
                    is_approved = row[5],
                )
                for row in rows
            ]


def delete_user(user: User | None = None) -> bool:
    """Удаляет пользователя из БД."""

    if user is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM users
                WHERE id = ?
            """, (user.id,))

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def delete_homestay(homestay: Homestay | None = None) -> bool:
    """Удаляет ночлег из БД."""

    if homestay is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM homestays
                WHERE id = ?
            """, (homestay.id,))

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def delete_booking(booking: Booking | None = None) -> bool:
    """Удаляет пользователя из БД."""

    if booking is None:
        return False

    try:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM booking
                WHERE id = ?
            """, (booking.id,))

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def calculate_route_distance(
    lat1,
    lon1,
    lat2,
    lon2,
    api_key,
    profile="car"
):
    """
    Возвращает расстояние по маршруту между двумя координатами.

    :param lat1: широта начальной точки
    :param lon1: долгота начальной точки
    :param lat2: широта конечной точки
    :param lon2: долгота конечной точки
    :param api_key: API-ключ GraphHopper
    :param profile: тип маршрута (car, bike, foot и т.д.)
    :return: расстояние в километрах
    """

    params = [
        ("point", f"{lat1},{lon1}"),
        ("point", f"{lat2},{lon2}"),
        ("profile", profile),
        ("calc_points", "false"),
        ("key", api_key),
    ]

    url = "https://graphhopper.com/api/1/route?" + urlencode(params)

    try:
        with urlopen(url, timeout=10) as response:
            data = json.load(response)

    except Exception as e:
        raise RuntimeError(f"Ошибка при запросе к GraphHopper: {e}")

    try:
        # GraphHopper возвращает distance в метрах
        distance_meters = data["paths"][0]["distance"]
    except (KeyError, IndexError):
        raise RuntimeError(f"GraphHopper вернул неожиданный ответ: {data}")

    return distance_meters / 1000


def sort_homestays_by_distance(user_longitude : float, user_latitude : float) -> list[Homestay]:
    homestays = get_all_homestays()

    def dist_sort(homestay):
        return calculate_route_distance(user_latitude, user_longitude,
                                homestay.latitude, homestay.longtitude,
                                getenv("GRAPHHOPPER_API_KEY", None), "foot")
    
    homestays.sort(key=lambda h: dist_sort(h))

    return homestays