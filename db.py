import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "clinic_bot.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                cabinet TEXT NOT NULL,
                lang TEXT NOT NULL DEFAULT 'ru'
            );

            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                work_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                FOREIGN KEY (doctor_id) REFERENCES doctors (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                hours TEXT NOT NULL,
                phone TEXT NOT NULL,
                map_url TEXT NOT NULL,
                type TEXT NOT NULL,
                lang TEXT NOT NULL DEFAULT 'ru'
            );

            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                keywords TEXT NOT NULL,
                lang TEXT NOT NULL DEFAULT 'ru'
            );

            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT NOT NULL,
                user_id TEXT,
                message TEXT,
                intent TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


def seed_demo_data():
    with get_conn() as conn:
        doctors_count = conn.execute("SELECT COUNT(*) as c FROM doctors").fetchone()["c"]
        if doctors_count:
            return

        conn.execute(
            "INSERT INTO doctors (full_name, specialization, cabinet, lang) VALUES (?, ?, ?, ?)",
            ("Иванова Ольга Сергеевна", "Терапевт", "101", "ru"),
        )
        conn.execute(
            "INSERT INTO doctors (full_name, specialization, cabinet, lang) VALUES (?, ?, ?, ?)",
            ("Пятровіч Аляксандр Мікалаевіч", "Тэрапеўт", "101", "be"),
        )
        doctor_ru_id = conn.execute("SELECT id FROM doctors WHERE lang='ru' LIMIT 1").fetchone()["id"]
        doctor_be_id = conn.execute("SELECT id FROM doctors WHERE lang='be' LIMIT 1").fetchone()["id"]

        conn.execute(
            "INSERT INTO schedule (doctor_id, work_date, start_time, end_time) VALUES (?, ?, ?, ?)",
            (doctor_ru_id, "2026-04-14", "08:00", "14:00"),
        )
        conn.execute(
            "INSERT INTO schedule (doctor_id, work_date, start_time, end_time) VALUES (?, ?, ?, ?)",
            (doctor_be_id, "2026-04-14", "08:00", "14:00"),
        )

        conn.execute(
            """
            INSERT INTO contacts (name, address, hours, phone, map_url, type, lang)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Центральная поликлиника",
                "г. Минск, ул. Примерная, 1",
                "Пн-Пт 08:00-20:00",
                "+375 17 000-00-00",
                "https://maps.google.com",
                "Отделение",
                "ru",
            ),
        )
        conn.execute(
            """
            INSERT INTO faq (category, question, answer, keywords, lang)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Запись",
                "Как записаться к врачу?",
                "Запись доступна через регистратуру по телефону +375 17 000-00-00.",
                "запись,регистратура,врач",
                "ru",
            ),
        )


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print(f"Database initialized at {DB_PATH}")
