import sqlite3
from contextlib import contextmanager

DB_PATH = "bookings.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def add_booking(user_id: int, service: str, date: str, time: str, name: str, phone: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bookings (user_id, service, date, time, name, phone) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, service, date, time, name, phone),
        )


def get_taken_slots(date: str) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT time FROM bookings WHERE date = ?", (date,)
        ).fetchall()
    return {row[0] for row in rows}


def get_user_bookings(user_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT service, date, time FROM bookings WHERE user_id = ? ORDER BY date, time",
            (user_id,),
        ).fetchall()
    return rows
