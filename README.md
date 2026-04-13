# Медицинский чат-бот (Telegram + Web widget)

Проект реализует двухканального бота:
- Telegram (aiogram)
- Виджет на сайте (Flask)

## Функционал
- Приветствие и выбор языка (ru/be)
- Главное меню (расписание, контакты, FAQ, платные услуги, обратная связь)
- Расписание врачей из SQLite
- Контакты/адреса отделений и ФАПов
- FAQ по категориям
- Обработка свободного текста по ключевым словам
- Обратная связь (коллбэк/номер регистратуры)
- Админ-панель с паролем для обновления FAQ/контактов и просмотра статистики

## Быстрый старт
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python db.py
```

### Запуск Telegram-бота
```bash
python bot.py
```

### Запуск Flask
```bash
python web.py
```

- API чата: `POST /api/chat`
- JS виджет: `GET /widget.js`
- Тестовая страница с виджетом: `GET /widget`
- Админка: `GET /admin/login`

## Деплой (Ubuntu + nginx + systemd)
1. Создать systemd unit для `python bot.py` (polling или webhook).
2. Создать systemd unit для `gunicorn web:app`.
3. Проксировать nginx на Flask/Gunicorn.
4. Для Telegram использовать polling (просто) или webhook (с HTTPS).

## Интеграция каналов
- Telegram: создать бота в @BotFather, вставить токен в `.env`
- Сайт: вставить в HTML
```html
<script src="https://your-domain/widget.js"></script>
```
