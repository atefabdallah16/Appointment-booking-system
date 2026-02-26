import os
import psycopg2
from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret123"

# التصحيح هنا:
DATABASE_URL = "postgresql://postgres:a01027625506@localhost:5432/mydb"

def get_db():
    # تأكد أن DATABASE_URL نص صريح وليس None
    return psycopg2.connect(DATABASE_URL)

# -----------------------
# إنشاء الجدول
# -----------------------
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            name TEXT,
            phone TEXT,
            booking_datetime TIMESTAMP,
            status TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# -----------------------
# إلغاء الحجوزات بعد 15 دقيقة
# -----------------------
def cancel_expired():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, booking_datetime FROM bookings WHERE status='active'")
    rows = cur.fetchall()
    now = datetime.now()

    for row in rows:
        if now > row[1] + timedelta(minutes=15):
            cur.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (row[0],))

    conn.commit()
    cur.close()
    conn.close()

# -----------------------
@app.route("/")
def home():
    cancel_expired()
    return render_template("index.html")

# -----------------------
@app.route("/book", methods=["POST"])
def book():
    name = request.form["name"]
    phone = request.form["phone"]
    time_str = request.form["time"]

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    booking_datetime = datetime.strptime(today + " " + time_str, "%Y-%m-%d %H:%M")

    if booking_datetime <= now:
        return "❌ لا يمكن الحجز في وقت ماضي"

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM bookings
        WHERE booking_datetime=%s AND status='active'
    """, (booking_datetime,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return "❌ هذا الموعد محجوز بالفعل"

    cur.execute("""
        INSERT INTO bookings (name, phone, booking_datetime, status)
        VALUES (%s, %s, %s, %s)
    """, (name, phone, booking_datetime, "active"))

    conn.commit()
    cur.close()
    conn.close()

    return render_template("success.html")

# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == "101010":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "❌ الصفحه خاصه بالمسؤول فقط"
    return render_template("login.html")

# -----------------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    cancel_expired()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bookings ORDER BY booking_datetime")
    bookings = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("admin.html", bookings=bookings)

# -----------------------
@app.route("/delete_all")
def delete_all():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bookings")
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin")

# -----------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)