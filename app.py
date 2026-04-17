import os
import sqlite3
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.secret_key = "secret123"

DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            booking_datetime TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def parse_dt(dt_str):
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Africa/Cairo"))
    return dt

def cancel_expired():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, booking_datetime FROM bookings WHERE status='active'")
    rows = cur.fetchall()
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    for row in rows:
        booking_time = parse_dt(row["booking_datetime"])
        # بعد 15 دقيقة من وقت الحجز يتلغى تلقائياً
        if now > booking_time:
            cur.execute("UPDATE bookings SET status='late_cancelled' WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()

@app.route("/")
def home():
    cancel_expired()
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    today_str = now.strftime("%Y-%m-%d")
    # جيب الحجوزات النشطة فقط (المُلغاة بتبقى متاحة تاني)
    cur.execute("SELECT booking_datetime FROM bookings WHERE status='active'")
    all_bookings = cur.fetchall()
    booked_times = []
    for row in all_bookings:
        dt = parse_dt(row["booking_datetime"])
        dt_cairo = dt.astimezone(ZoneInfo("Africa/Cairo"))
        if dt_cairo.strftime("%Y-%m-%d") == today_str:
            booked_times.append(dt_cairo.strftime("%H:%M"))
    conn.close()
    return render_template("index.html", booked_times=booked_times)

@app.route("/book", methods=["POST"])
def book():
    name = request.form["name"]
    phone = request.form["phone"]
    time_str = request.form["time"]
    now = datetime.now(ZoneInfo("Africa/Cairo"))
    target_date = now.strftime("%Y-%m-%d")
    booking_datetime = datetime.strptime(target_date + " " + time_str, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Africa/Cairo"))

    if booking_datetime < now:
        return "❌ عذراً، هذا الوقت قد مضى بالفعل اليوم"

    booking_str = booking_datetime.isoformat()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings WHERE booking_datetime=? AND status='active'", (booking_str,))
    if cur.fetchone():
        conn.close()
        return "❌ هذا الموعد محجوز بالفعل"

    cur.execute("INSERT INTO bookings (name, phone, booking_datetime, status) VALUES (?, ?, ?, ?)",
                (name, phone, booking_str, "active"))
    conn.commit()
    conn.close()
    return render_template("success.html")

@app.route("/public_schedule")
def public_schedule():
    cancel_expired()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT booking_datetime FROM bookings WHERE status='active' ORDER BY booking_datetime")
    raw = cur.fetchall()
    conn.close()
    bookings = [(parse_dt(row["booking_datetime"]),) for row in raw]
    return render_template("public_schedule.html", bookings=bookings)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "abdallah404":
            session["admin"] = True
            return redirect("/admin")
        return "❌ الباسورد خطأ"
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"): return redirect("/login")
    cancel_expired()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, booking_datetime, status FROM bookings ORDER BY booking_datetime")
    raw = cur.fetchall()
    conn.close()
    bookings = [(row["id"], row["name"], row["phone"], parse_dt(row["booking_datetime"]), row["status"]) for row in raw]
    return render_template("admin.html", bookings=bookings)

@app.route("/delete_all")
def delete_all():
    if not session.get("admin"): return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings")
    conn.commit()
    conn.close()
    return redirect("/admin")

init_db()

if __name__ == "__main__":
    app.run(debug=True)