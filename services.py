from typing import Optional

from db import get_conn

LANG_TEXT = {
    "ru": {
        "welcome": "Здравствуйте! Выберите язык / Калі ласка, абярыце мову:",
        "menu": "Главное меню:",
        "no_schedule": "На выбранную дату и специализацию расписание не найдено.",
        "contacts_title": "Контакты и адреса:",
        "faq_title": "FAQ:",
        "feedback": "Оставьте номер для обратного звонка или позвоните в регистратуру: +375 17 000-00-00",
        "unknown": "Не удалось распознать запрос. Выберите пункт меню или свяжитесь с оператором: +375 17 000-00-00",
        "paid": "Платные услуги: уточняйте в отделении платных услуг по телефону +375 17 000-00-01",
    },
    "be": {
        "welcome": "Вітаем! Абярыце мову:",
        "menu": "Галоўнае меню:",
        "no_schedule": "Расклад для выбранай даты і спецыялізацыі не знойдзены.",
        "contacts_title": "Кантакты і адрасы:",
        "faq_title": "FAQ:",
        "feedback": "Пакіньце нумар для зваротнага званка або тэлефануйце ў рэгістратуру: +375 17 000-00-00",
        "unknown": "Запыт не распазнаны. Абярыце пункт меню або звяжыцеся з аператарам: +375 17 000-00-00",
        "paid": "Платныя паслугі: удакладняйце па тэлефоне +375 17 000-00-01",
    },
}


def log_stat(channel: str, user_id: Optional[str], message: str, intent: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO stats (channel, user_id, message, intent) VALUES (?, ?, ?, ?)",
            (channel, user_id, message, intent),
        )


def get_schedule(lang: str, specialization: str, date_str: str) -> str:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT d.full_name, d.specialization, d.cabinet, s.work_date, s.start_time, s.end_time
            FROM schedule s
            JOIN doctors d ON d.id = s.doctor_id
            WHERE d.lang = ?
              AND d.specialization LIKE ?
              AND s.work_date = ?
            ORDER BY s.start_time
            """,
            (lang, f"%{specialization}%", date_str),
        ).fetchall()

    if not rows:
        return LANG_TEXT[lang]["no_schedule"]

    result = []
    for row in rows:
        result.append(
            f"{row['work_date']} {row['start_time']}-{row['end_time']} | {row['specialization']} | {row['full_name']} | каб. {row['cabinet']}"
        )
    return "\n".join(result)


def get_contacts(lang: str) -> str:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, address, hours, phone, map_url, type FROM contacts WHERE lang = ?",
            (lang,),
        ).fetchall()

    if not rows:
        return LANG_TEXT[lang]["contacts_title"] + "\n-"

    lines = [LANG_TEXT[lang]["contacts_title"]]
    for row in rows:
        lines.append(
            f"{row['type']}: {row['name']}\n{row['address']}\n{row['hours']}\n{row['phone']}\n{row['map_url']}"
        )
    return "\n\n".join(lines)


def get_faq(lang: str, category: Optional[str] = None) -> str:
    query = "SELECT category, question, answer FROM faq WHERE lang = ?"
    params = [lang]
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        return LANG_TEXT[lang]["faq_title"] + "\n-"

    lines = [LANG_TEXT[lang]["faq_title"]]
    for row in rows:
        lines.append(f"[{row['category']}] {row['question']}\n{row['answer']}")
    return "\n\n".join(lines)


def free_text_reply(lang: str, text: str) -> str:
    with get_conn() as conn:
        faq = conn.execute(
            "SELECT answer FROM faq WHERE lang = ? AND keywords LIKE ? LIMIT 1",
            (lang, f"%{text.lower()}%"),
        ).fetchone()

    if faq:
        return faq["answer"]

    if "плат" in text.lower():
        return LANG_TEXT[lang]["paid"]

    return LANG_TEXT[lang]["unknown"]
