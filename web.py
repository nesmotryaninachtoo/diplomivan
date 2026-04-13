import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

from db import get_conn, init_db, seed_demo_data
from services import LANG_TEXT, free_text_reply, get_contacts, get_faq, get_schedule, log_stat

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
DEFAULT_LANG = os.getenv("BOT_DEFAULT_LANGUAGE", "ru")


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)

    return wrapper


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(force=True)
    text = (payload.get("text") or "").strip()
    lang = payload.get("lang") or DEFAULT_LANG

    if text.lower().startswith("расписание"):
        reply = get_schedule(lang, "", payload.get("date", "2026-04-14"))
        intent = "schedule"
    elif "контакт" in text.lower():
        reply = get_contacts(lang)
        intent = "contacts"
    elif "faq" in text.lower() or "вопрос" in text.lower():
        reply = get_faq(lang)
        intent = "faq"
    else:
        reply = free_text_reply(lang, text)
        intent = "free_text"

    log_stat("web", payload.get("user_id", "web-user"), text, intent)
    return jsonify({"reply": reply})


@app.get("/widget.js")
def widget_js():
    js = """
(function () {
  const root = document.createElement('div');
  root.innerHTML = `
  <style>
    #clinic-chat-btn{position:fixed;bottom:20px;right:20px;background:#0a7;color:#fff;border:none;padding:12px;border-radius:50%;cursor:pointer;z-index:9999}
    #clinic-chat-box{position:fixed;bottom:70px;right:20px;width:320px;background:white;border:1px solid #ccc;border-radius:10px;display:none;z-index:9999;font-family:sans-serif}
    #clinic-log{height:260px;overflow:auto;padding:10px;font-size:14px}
    #clinic-input-wrap{display:flex;border-top:1px solid #ddd}
    #clinic-input{flex:1;padding:8px;border:none}
  </style>
  <button id="clinic-chat-btn">💬</button>
  <div id="clinic-chat-box">
    <div id="clinic-log"></div>
    <div id="clinic-input-wrap">
      <input id="clinic-input" placeholder="Ваш вопрос" />
      <button id="clinic-send">➤</button>
    </div>
  </div>`;
  document.body.appendChild(root);

  const btn = document.getElementById('clinic-chat-btn');
  const box = document.getElementById('clinic-chat-box');
  const log = document.getElementById('clinic-log');
  const input = document.getElementById('clinic-input');
  const send = document.getElementById('clinic-send');

  btn.onclick = () => box.style.display = box.style.display === 'block' ? 'none' : 'block';

  async function ask() {
    const text = input.value.trim();
    if (!text) return;
    log.innerHTML += `<div><b>Вы:</b> ${text}</div>`;
    input.value = '';
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, user_id: 'widget-user', lang: 'ru'})
    });
    const data = await res.json();
    log.innerHTML += `<div><b>Бот:</b> ${data.reply}</div>`;
    log.scrollTop = log.scrollHeight;
  }

  send.onclick = ask;
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') ask(); });
})();
"""
    return app.response_class(js, mimetype="application/javascript")


@app.get("/widget")
def widget_html():
    return """<!doctype html><html><head><meta charset='utf-8'><title>Widget</title></head><body>
<script src='/widget.js'></script>
</body></html>"""


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
    return render_template_string(
        """
        <h2>Admin login</h2>
        <form method="post">
          <input type="password" name="password" placeholder="Password" />
          <button type="submit">Login</button>
        </form>
        """
    )


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        entity = request.form.get("entity")
        if entity == "faq":
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO faq (category, question, answer, keywords, lang) VALUES (?, ?, ?, ?, ?)",
                    (
                        request.form.get("category"),
                        request.form.get("question"),
                        request.form.get("answer"),
                        request.form.get("keywords"),
                        request.form.get("lang", "ru"),
                    ),
                )
        elif entity == "contact":
            with get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO contacts (name, address, hours, phone, map_url, type, lang)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.form.get("name"),
                        request.form.get("address"),
                        request.form.get("hours"),
                        request.form.get("phone"),
                        request.form.get("map_url"),
                        request.form.get("type"),
                        request.form.get("lang", "ru"),
                    ),
                )

    with get_conn() as conn:
        stats = conn.execute(
            "SELECT channel, intent, COUNT(*) as qty FROM stats GROUP BY channel, intent ORDER BY qty DESC"
        ).fetchall()

    return render_template_string(
        """
        <h2>Admin panel</h2>
        <h3>Add FAQ</h3>
        <form method="post">
          <input type="hidden" name="entity" value="faq" />
          <input name="category" placeholder="Category" required>
          <input name="question" placeholder="Question" required>
          <input name="answer" placeholder="Answer" required>
          <input name="keywords" placeholder="Keywords" required>
          <input name="lang" value="ru" placeholder="Lang">
          <button type="submit">Save FAQ</button>
        </form>

        <h3>Add Contact</h3>
        <form method="post">
          <input type="hidden" name="entity" value="contact" />
          <input name="name" placeholder="Name" required>
          <input name="address" placeholder="Address" required>
          <input name="hours" placeholder="Hours" required>
          <input name="phone" placeholder="Phone" required>
          <input name="map_url" placeholder="Map URL" required>
          <input name="type" placeholder="Type" required>
          <input name="lang" value="ru" placeholder="Lang">
          <button type="submit">Save Contact</button>
        </form>

        <h3>Stats</h3>
        <ul>
          {% for row in stats %}
            <li>{{ row['channel'] }} / {{ row['intent'] }}: {{ row['qty'] }}</li>
          {% endfor %}
        </ul>
        """,
        stats=stats,
    )


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    app.run(host="0.0.0.0", port=5000, debug=True)
