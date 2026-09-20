from classes import Homestay, User
import sqlite3
from os import getenv
from dotenv import load_dotenv


load_dotenv()
database_name = f"{getenv('DB_NAME')}.db"


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
                homestay_type INT DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                user_type INTEGER DEFAULT 0,
                phone_number TEXT,
                id_homestay INTEGER,
                FOREIGN KEY (id_homestay) REFERENCES homestays(id)
            )
        """)

        conn.commit()


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
                id_homestay
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
            id_homestay=row[4]
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
                    additional_info
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
                additional_info=row[7]
            )


def insert_or_update_user(user : User | None = None):
    """Добавление или изменения пользователя в БД."""

    if user is not None:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            if user.id == 0:
                cursor.execute("""
                    INSERT INTO users (
                        username,
                        user_type,
                        phone_number,
                        id_homestay
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    user.username,
                    user.user_type,
                    user.phone_number,
                    user.id_homestay
                ))

                user.id = cursor.lastrowid

            else:
                cursor.execute("""
                    UPDATE users
                    SET
                        username = ?,
                        user_type = ?,
                        phone_number = ?,
                        id_homestay = ?
                    WHERE id = ?
                """, (
                    user.username,
                    user.user_type,
                    user.phone_number,
                    user.id_homestay,
                    user.id
                ))


def insert_or_update_homestay(homestay : Homestay | None = None):
    """Добавление или изменения пользователя в БД."""

    if homestay is not None:
        with sqlite3.connect(database_name) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            if homestay.id == 0:
                cursor.execute("""
                    INSERT INTO homestays (
                        id,
                        address,
                        all_beds,
                        available_beds,
                        open_time,
                        close_time,
                        is_working,
                        additional_info
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    homestay.address,
                    homestay.all_beds,
                    homestay.available_beds,
                    homestay.open_time,
                    homestay.close_time,
                    homestay.is_working,
                    homestay.additional_info
                ))

                homestay.id = cursor.lastrowid

            else:
                cursor.execute("""
                    UPDATE homestays
                    SET
                        id,
                        address = ?,
                        all_beds = ?,
                        available_beds = ?,
                        open_time = ?,
                        close_time = ?,
                        is_working = ?,
                        additional_info = ?
                    WHERE id = ?
                """, (
                    homestay.address,
                    homestay.all_beds,
                    homestay.available_beds,
                    homestay.open_time,
                    homestay.close_time,
                    homestay.is_working,
                    homestay.additional_info
                ))