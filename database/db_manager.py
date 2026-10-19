from database.classes import Homestay, User, Booking
from database.info import info
import sqlite3
from os import getenv
from dotenv import load_dotenv
from datetime import datetime, timezone
from contextlib import contextmanager, closing

load_dotenv()
database_name = f"{getenv('DB_NAME', 'database')}.db"


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")



@contextmanager
def _connect(timeout=5):
    # sqlite3.Connection.__exit__ не закрывает соединение, поэтому closing обязателен.
    with closing(sqlite3.connect(database_name, timeout=timeout)) as conn:
        with conn:
            yield conn

def initialize_database():
    """Идемпотентная миграция без потери существующих пунктов и бронирований."""
    with _connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT, user_type INTEGER DEFAULT 0,
                phone_number TEXT, id_homestay INTEGER, last_booking TEXT
            );
            CREATE TABLE IF NOT EXISTS homestays (
                id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT NOT NULL,
                all_beds INTEGER NOT NULL, available_beds INTEGER DEFAULT 0,
                open_time TEXT NOT NULL DEFAULT '', close_time TEXT NOT NULL DEFAULT '',
                is_working INTEGER DEFAULT 0, additional_info TEXT,
                homestay_type INTEGER DEFAULT 0, longtitude REAL, latitude REAL
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY, user_id INTEGER, homestay_id INTEGER,
                date_time TEXT NOT NULL, is_approved INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(homestay_id) REFERENCES homestays(id)
            );
            CREATE TABLE IF NOT EXISTS funds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS point_managers (
                point_id INTEGER NOT NULL REFERENCES homestays(id) ON DELETE CASCADE,
                manager_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY(point_id, manager_id)
            );
            CREATE INDEX IF NOT EXISTS idx_pm_manager ON point_managers(manager_id);
            -- Счётчик никогда не очищается, даже когда активные брони удалены.
            CREATE TABLE IF NOT EXISTS booking_ids (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );
            CREATE TABLE IF NOT EXISTS booking_history (
                booking_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                homestay_id INTEGER NOT NULL, fund_id INTEGER,
                address_snapshot TEXT NOT NULL DEFAULT '',
                date_time TEXT NOT NULL, is_approved INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                updated_at TEXT NOT NULL, finished_at TEXT,
                actor_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_bh_user ON booking_history(user_id, date_time);
            CREATE INDEX IF NOT EXISTS idx_bh_point ON booking_history(homestay_id, date_time);
            CREATE INDEX IF NOT EXISTS idx_bh_point_user ON booking_history(homestay_id, user_id);
            CREATE TABLE IF NOT EXISTS booking_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL, event TEXT NOT NULL,
                occurred_at TEXT NOT NULL, actor_id INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_be_booking ON booking_events(booking_id);
        """)
        def add_column(table, name, definition):
            names = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if name not in names:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        add_column('users', 'fund_id', 'INTEGER REFERENCES funds(id)')
        add_column('homestays', 'fund_id', 'INTEGER REFERENCES funds(id)')
        add_column('homestays', 'longtitude', 'REAL')
        add_column('homestays', 'latitude', 'REAL')
        # Без переназначения старые пункты переносим в один фонд.
        if conn.execute('SELECT COUNT(*) FROM homestays WHERE fund_id IS NULL').fetchone()[0]:
            conn.execute("INSERT OR IGNORE INTO funds(name, description) VALUES (?, ?)",
                         ('Основной фонд', 'Создан автоматически при обновлении бота'))
            fund_id = conn.execute("SELECT id FROM funds WHERE name = ?", ('Основной фонд',)).fetchone()[0]
            conn.execute('UPDATE homestays SET fund_id=? WHERE fund_id IS NULL', (fund_id,))
        # Преобразуем прежнюю связь 1:1, сохраняя её для старого REST API.
        conn.execute("""INSERT OR IGNORE INTO point_managers(point_id, manager_id)
                        SELECT id_homestay, id FROM users
                        WHERE user_type=1 AND id_homestay IN (SELECT id FROM homestays)""")
        # При переходе с версии без счётчика резервируем все старые ID.
        max_used = conn.execute("SELECT MAX(id) FROM (SELECT id FROM bookings UNION ALL SELECT booking_id FROM booking_history)").fetchone()[0] or 0
        seq_row = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='booking_ids'").fetchone()
        if max_used > (seq_row[0] if seq_row else 0):
            conn.execute('INSERT INTO booking_ids(id) VALUES(?)', (max_used,))
        now = _utc_now()
        conn.execute("""INSERT OR IGNORE INTO booking_history
                        (booking_id,user_id,homestay_id,fund_id,address_snapshot,
                         date_time,is_approved,status,updated_at)
                        SELECT b.id,b.user_id,b.homestay_id,h.fund_id,h.address,
                               b.date_time,b.is_approved,
                               CASE WHEN b.is_approved=1 THEN 'approved' ELSE 'pending' END,?
                        FROM bookings b JOIN homestays h ON h.id=b.homestay_id""", (now,))
    info('База данных инициализирована (миграции применены).')


def get_user(id: int | None = None,
             username: str | None = None,
             id_homestay: int | None = None) -> User | None:
    """Используется для получения пользователя из БД по ключам или без них."""

    with _connect() as conn:
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
            conditions.append("(id_homestay = ? OR id IN (SELECT manager_id FROM point_managers WHERE point_id = ?))")
            parameters.extend([id_homestay, id_homestay])
            conditions.append('user_type = 1')

        if not conditions:
            return None

        query = f"""
            SELECT 
                id,
                username,
                user_type,
                phone_number,
                id_homestay,
                last_booking, fund_id
            FROM users
            WHERE {" AND ".join(conditions)}
            ORDER BY id
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
            last_booking=row[5],
            fund_id=row[6]
        )


def get_homestay(id : int | None = None,
                 address: str | None = None,
                 is_working : int | None = None) -> Homestay | None:
    """Используется для получения ночлега из БД по ключам или без них."""

    with _connect() as conn:
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
                    latitude, fund_id
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
                latitude=row[10],
                fund_id=row[11]
            )


def get_booking(id: int | None = None) -> Booking | None:
    with _connect() as conn:
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
            is_approved = row[4],
        )


def insert_or_update_user(user : User | None = None) -> bool:
    """Добавление или изменения пользователя в БД."""

    if user is None:
        return False

    try:
        with _connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (
                    id,
                    username,
                    user_type,
                    phone_number,
                    id_homestay,
                    last_booking, fund_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    username = excluded.username, 
                    user_type = excluded.user_type,
                    phone_number = excluded.phone_number,
                    id_homestay = excluded.id_homestay,
                    last_booking = excluded.last_booking,
                    fund_id = excluded.fund_id
            """, (
                user.id,
                user.username,
                user.user_type,
                user.phone_number,
                user.id_homestay,
                user.last_booking,
                user.fund_id
            ))
        return True

    except sqlite3.Error:
        return False


def insert_or_update_homestay(homestay : Homestay | None = None) -> bool:
    """Добавление или изменения пользователя в БД."""

    if homestay is None:
        return False

    try:
        with _connect() as conn:
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
                        latitude, fund_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    homestay.fund_id
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
                        latitude = ?,
                        fund_id = ?
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
                    homestay.fund_id,
                    homestay.id
                ))

                return cursor.rowcount > 0

    except sqlite3.Error:
        return False

def insert_or_update_booking(booking: Booking | None = None) -> bool:
    if booking is None:
        return False

    try:
        with _connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            # Одно блокирование для выделения номера, записи и события.
            conn.execute('BEGIN IMMEDIATE')
            if booking.id:
                # Нельзя заново создать ранее удалённую заявку с тем же ID.
                if not cursor.execute('SELECT 1 FROM bookings WHERE id=?',
                                      (booking.id,)).fetchone():
                    return False
                cursor.execute("""UPDATE bookings SET user_id=?, homestay_id=?,
                    date_time=?, is_approved=? WHERE id=?""", (
                    booking.user_id,booking.homestay_id,booking.date_time,
                    booking.is_approved,booking.id))
            else:
                booking.id = cursor.execute('INSERT INTO booking_ids DEFAULT VALUES').lastrowid
                cursor.execute("""INSERT INTO bookings (
                    id, user_id, homestay_id, date_time, is_approved
                ) VALUES (?, ?, ?, ?, ?)""", (
                    booking.id, booking.user_id, booking.homestay_id,
                    booking.date_time, booking.is_approved,
                ))

            _record_booking(conn, booking, 'approved' if booking.is_approved else 'pending')

        return True

    except sqlite3.Error as e:
        print(f"\n\nSQL ERROR: {e}")
        return False


def get_all_homestays() -> list[Homestay]:
    """Возвращает список всех ночлегов из БД."""

    with _connect() as conn:
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
                latitude, fund_id
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
                latitude=row[10],
                fund_id=row[11]
            )
            for row in rows
        ]



def get_all_bookings() -> list[Booking]:
    """Возвращает список всех броней из БД."""

    with _connect() as conn:
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
        """)

        rows = cursor.fetchall()

        return [
            Booking(
                id=row[0],
                user_id=row[1],
                homestay_id=row[2],
                date_time=row[3],
                is_approved=row[4],
            )
            for row in rows
        ]



def get_user_bookings(user : User | None = None) -> list[Booking]:
    if user is None:
        return []

    with _connect() as conn:
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
                    is_approved = row[4],
                )
                for row in rows
            ]


def get_homestay_bookings(homestay : Homestay | None = None) -> list[Booking]:
    if homestay is None:
        return []

    with _connect() as conn:
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
                    is_approved = row[4],
                )
                for row in rows
            ]


def delete_user(user: User | None = None) -> bool:
    """Удаляет пользователя из БД."""

    if user is None:
        return False

    try:
        with _connect() as conn:
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
        with _connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM homestays
                WHERE id = ?
            """, (homestay.id,))

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def delete_booking(booking: Booking | None = None, reason: str = 'removed',
                   actor_id: int | None = None, restore_bed: bool = True) -> bool:
    """Атомарно закрывает бронь, освобождает место и сохраняет журнал."""
    if booking is None or reason not in {'removed', 'cancelled', 'rejected', 'expired'}:
        return False
    try:
        with _connect(timeout=15) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT id,user_id,homestay_id,date_time,is_approved FROM bookings WHERE id=?',
                               (booking.id,)).fetchone()
            if not row:
                return False
            current = Booking(*row)
            _record_booking(conn, current, reason, actor_id=actor_id, finished=True)
            if restore_bed:
                conn.execute("""UPDATE homestays SET available_beds = MIN(all_beds,available_beds+1)
                                WHERE id=?""", (current.homestay_id,))
            conn.execute('DELETE FROM bookings WHERE id=?', (current.id,))
        return True
    except sqlite3.Error as exc:
        print('DELETE BOOKING ERROR:', exc)
        return False


#
# def     calculate_route_distance(
#     lat1,
#     lon1,
#     lat2,
#     lon2,
#     api_key,
#     profile="car"
# ):
#     """
#     Возвращает расстояние по маршруту между двумя координатами.
#
#     :param lat1: широта начальной точки
#     :param lon1: долгота начальной точки
#     :param lat2: широта конечной точки
#     :param lon2: долгота конечной точки
#     :param api_key: API-ключ GraphHopper
#     :param profile: тип маршрута (car, bike, foot и т.д.)
#     :return: расстояние в километрах
#     """
#
#     params = [
#         ("point", f"{lat1},{lon1}"),
#         ("point", f"{lat2},{lon2}"),
#         ("profile", profile),
#         ("calc_points", "false"),
#         ("key", api_key),
#     ]
#
#     url = "https://graphhopper.com/api/1/route?" + urlencode(params)
#
#     try:
#         with urlopen(url, timeout=10) as response:
#             data = json.load(response)
#
#     except Exception as e:
#         raise RuntimeError(f"Ошибка при запросе к GraphHopper: {e}")
#
#     try:
#         # GraphHopper возвращает distance в метрах
#         distance_meters = data["paths"][0]["distance"]
#     except (KeyError, IndexError):
#         raise RuntimeError(f"GraphHopper вернул неожиданный ответ: {data}")
#
#     return distance_meters / 1000



def calculate_route_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Возвращает расстояние по маршруту между двумя координатами.

    :param lat1: широта начальной точки
    :param lon1: долгота начальной точки
    :param lat2: широта конечной точки
    :param lon2: долгота конечной точки
    :return: расстояние по прямой
    """
    import math
    return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)


def sort_homestays_by_distance(user_longitude : float, user_latitude : float) -> list[Homestay]:
    homestays = get_all_homestays()
    #
    # def dist_sort(homestay):
    #     return calculate_route_distance(user_latitude, user_longitude,
    #                             homestay.latitude, homestay.longtitude,
    #                             getenv("GRAPHHOPPER_API_KEY", None), "foot")

    def dist_sort(homestay):
        return calculate_route_distance(user_latitude, user_longitude,
                                homestay.latitude, homestay.longtitude) if homestay.latitude is not None and homestay.longtitude is not None else float('inf')
    
    homestays.sort(key=lambda h: dist_sort(h))

    return homestays

# ------------------ ФОНДЫ И МЕНЕДЖЕРЫ ------------------

def get_fund(fund_id):
    if not fund_id:
        return None
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT * FROM funds WHERE id=?', (fund_id,)).fetchone()
        return dict(row) if row else None


def get_funds():
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(x) for x in conn.execute('SELECT * FROM funds ORDER BY name')]


def create_fund(name, description=''):
    name = (name or '').strip()
    if not name or len(name) > 120 or len(description or '') > 1500:
        return None
    with _connect() as conn:
        try:
            row = conn.execute('INSERT INTO funds(name,description) VALUES(?,?)', (name,description or ''))
            return row.lastrowid
        except sqlite3.IntegrityError:
            return None


def edit_fund(fund_id, name=None, description=None):
    fund = get_fund(fund_id)
    if not fund:
        return False
    new_name = (name if name is not None else fund['name']).strip()
    new_desc = description if description is not None else fund['description']
    if not new_name or len(new_name) > 120 or len(new_desc) > 1500:
        return False
    with _connect() as conn:
        try:
            return conn.execute('UPDATE funds SET name=?,description=? WHERE id=?',
                                (new_name,new_desc,fund_id)).rowcount > 0
        except sqlite3.IntegrityError:
            return False



def delete_fund(fund_id, actor_id):
    """Необратимое удаление фонда с пунктами. Журнал заявок не удаляем.

    Права перепроверяем внутри транзакции, чтобы старые callback не работали
    после отзыва роли. Возвращаем список затронутых броней для уведомлений.
    """
    from database.access import global_admin_ids, BOT_ADMIN, FUND_ADMIN
    with _connect(timeout=15) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN IMMEDIATE')
        role = conn.execute('SELECT user_type,fund_id FROM users WHERE id=?',
                            (actor_id,)).fetchone()
        fund = conn.execute('SELECT id FROM funds WHERE id=?', (fund_id,)).fetchone()
        allowed = role and (role[0] == BOT_ADMIN or actor_id in global_admin_ids()
                            or (role[0] == FUND_ADMIN and role[1] == fund_id))
        if not fund or not allowed:
            return None
        active = conn.execute("SELECT b.id,b.user_id,b.homestay_id,b.date_time,b.is_approved "
            "FROM bookings b JOIN homestays h ON h.id=b.homestay_id WHERE h.fund_id=?",
            (fund_id,)).fetchall()
        for row in active:
            booking = Booking(*row)
            _record_booking(conn, booking, 'removed', actor_id=actor_id, finished=True)
            conn.execute('DELETE FROM bookings WHERE id=?', (booking.id,))
        point_ids = [x[0] for x in conn.execute('SELECT id FROM homestays WHERE fund_id=?',
                                                (fund_id,))]
        # Сохраняем возможность читать историю и исключаем осиротевшие ссылки.
        conn.execute('UPDATE users SET id_homestay=NULL WHERE id_homestay IN '
                     '(SELECT id FROM homestays WHERE fund_id=?)', (fund_id,))
        conn.execute('DELETE FROM point_managers WHERE point_id IN '
                     '(SELECT id FROM homestays WHERE fund_id=?)', (fund_id,))
        conn.execute('DELETE FROM homestays WHERE fund_id=?', (fund_id,))
        # Выбираем действующий запасной пункт менеджера для старого API.
        conn.execute("UPDATE users SET id_homestay=(SELECT MIN(point_id) "
                     "FROM point_managers WHERE manager_id=users.id) "
                     "WHERE user_type=1 AND id_homestay IS NULL")
        conn.execute('UPDATE users SET user_type=0,fund_id=NULL,id_homestay=NULL '
                     'WHERE user_type=3 AND fund_id=?', (fund_id,))
        conn.execute('UPDATE users SET fund_id=NULL WHERE fund_id=?', (fund_id,))
        conn.execute('DELETE FROM funds WHERE id=?', (fund_id,))
        return {'points': len(point_ids), 'bookings': [(r[0],r[1]) for r in active]}

def get_manager_point_ids(manager_id):
    with _connect() as conn:
        return [r[0] for r in conn.execute('SELECT point_id FROM point_managers WHERE manager_id=?',
                                           (manager_id,))]


def manager_has_point(manager_id, point_id):
    return int(point_id) in get_manager_point_ids(manager_id)


def get_manager_points(manager_id):
    ids = set(get_manager_point_ids(manager_id))
    return [point for point in get_all_homestays() if point.id in ids]


def get_homestay_managers(point_id):
    with _connect() as conn:
        rows = conn.execute("""SELECT users.id FROM users JOIN point_managers pm ON pm.manager_id=users.id
                               WHERE pm.point_id=? AND users.user_type=1 ORDER BY users.id""",
                            (point_id,)).fetchall()
    return [u for uid, in rows if (u := get_user(id=uid))]


def assign_manager(point_id, manager_id):
    actor = get_user(id=manager_id)
    if not actor or actor.user_type != 1 or not get_homestay(id=point_id):
        return False
    with _connect() as conn:
        conn.execute('INSERT OR IGNORE INTO point_managers(point_id,manager_id) VALUES(?,?)',
                     (point_id,manager_id))
        # Старое поле нужно /api/places, /api/book без изменений.
        if not actor.id_homestay or actor.id_homestay < 1:
            conn.execute('UPDATE users SET id_homestay=? WHERE id=?', (point_id,manager_id))
    return True


def unassign_manager(point_id, manager_id):
    with _connect() as conn:
        cur = conn.execute('DELETE FROM point_managers WHERE point_id=? AND manager_id=?',
                           (point_id,manager_id))
        if cur.rowcount:
            other = conn.execute('SELECT point_id FROM point_managers WHERE manager_id=? ORDER BY point_id LIMIT 1',
                                 (manager_id,)).fetchone()
            conn.execute('UPDATE users SET id_homestay=? WHERE id=?',
                         (other[0] if other else None,manager_id))
        return cur.rowcount > 0


def set_account_role(user_id, role, fund_id=None):
    if role not in (0, 1, 2, 3):
        return False
    if role == 3 and not get_fund(fund_id):
        return False
    with _connect() as conn:
        changed = conn.execute('UPDATE users SET user_type=?,fund_id=?,id_homestay=CASE WHEN ?=1 THEN id_homestay ELSE NULL END WHERE id=?',
                               (role, fund_id if role == 3 else None, role, user_id)).rowcount
        if role != 1:
            conn.execute('DELETE FROM point_managers WHERE manager_id=?', (user_id,))
    return bool(changed)


# ------------------ АУДИТ БРОНИРОВАНИЙ ------------------

def _record_booking(conn, booking, status, actor_id=None, finished=False):
    point = conn.execute('SELECT address,fund_id FROM homestays WHERE id=?',
                         (booking.homestay_id,)).fetchone()
    now = _utc_now()
    conn.execute("""INSERT INTO booking_history
                    (booking_id,user_id,homestay_id,fund_id,address_snapshot,date_time,
                     is_approved,status,updated_at,finished_at,actor_id)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(booking_id) DO UPDATE SET
                      is_approved=excluded.is_approved, status=excluded.status,
                      updated_at=excluded.updated_at, finished_at=excluded.finished_at,
                      actor_id=excluded.actor_id""",
                 (booking.id,booking.user_id,booking.homestay_id,point[1] if point else None,
                  point[0] if point else '',booking.date_time,booking.is_approved,
                  status,now,now if finished else None,actor_id))
    # Не создаём дубликат события, если статус уже был установлен.
    last = conn.execute('SELECT event FROM booking_events WHERE booking_id=? ORDER BY id DESC LIMIT 1',
                        (booking.id,)).fetchone()
    if not last or last[0] != status:
        conn.execute('INSERT INTO booking_events(booking_id,event,occurred_at,actor_id) VALUES(?,?,?,?)',
                     (booking.id,status,now,actor_id))


def approve_booking(booking_id, actor_id=None, point_id=None):
    """Вторая одновременная попытка подтверждения вернёт False."""
    with _connect(timeout=15) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT id,user_id,homestay_id,date_time,is_approved FROM bookings WHERE id=?',
                           (booking_id,)).fetchone()
        if not row or row[4] or (point_id is not None and row[2] != point_id):
            return False
        conn.execute('UPDATE bookings SET is_approved=1 WHERE id=?', (booking_id,))
        new = Booking(*row[:4],is_approved=1)
        _record_booking(conn,new,'approved',actor_id=actor_id)
    return True


def get_booking_history(user_id=None, homestay_id=None, search_user_id=None, limit=250, offset=0):
    clauses, params = [], []
    if user_id is not None:
        clauses.append('user_id=?'); params.append(user_id)
    if homestay_id is not None:
        clauses.append('homestay_id=?'); params.append(homestay_id)
    if search_user_id is not None:
        clauses.append('user_id=?'); params.append(search_user_id)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with _connect() as conn:
        conn.row_factory=sqlite3.Row
        return [dict(r) for r in conn.execute('SELECT * FROM booking_history'+where+
                ' ORDER BY date_time DESC,booking_id DESC LIMIT ? OFFSET ?',
                (*params, max(1,min(limit,1000)),max(0,offset)))]


def get_booking_events(booking_id):
    with _connect() as conn:
        conn.row_factory=sqlite3.Row
        return [dict(r) for r in conn.execute('SELECT * FROM booking_events WHERE booking_id=? ORDER BY id',
                                               (booking_id,))]


def count_booking_history(user_id=None, homestay_id=None, search_user_id=None):
    clauses, params=[],[]
    for column,value in [('user_id',user_id),('homestay_id',homestay_id),('user_id',search_user_id)]:
        if value is not None:
            clauses.append(column+'=?')
            params.append(value)
    where=(' WHERE '+' AND '.join(clauses)) if clauses else ''
    with _connect() as conn:
        return conn.execute('SELECT COUNT(*) FROM booking_history'+where,params).fetchone()[0]
