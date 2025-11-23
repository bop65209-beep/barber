# web_version/app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from database import DB_PATH
from persian_calendar import PersianCalendar
from time_utils import generate_time_slots, is_time_available

app = Flask(__name__)
app.secret_key = "supersecretkey"

WEEK_DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]

def get_schedule(day_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT is_open, start_time, end_time FROM daily_schedules WHERE day_name = ?", (day_name,))
    row = cur.fetchone()
    conn.close()
    return {"is_open": bool(row[0]), "start_time": row[1], "end_time": row[2]} if row else None

@app.route("/")
def index():
    week = PersianCalendar.get_jalali_week_dates()
    return render_template("index.html", week=week)

@app.route("/book/<date_str>/<day_name>")
def book(date_str, day_name):
    schedule = get_schedule(day_name)
    if not schedule or not schedule["is_open"]:
        flash(f"روز {day_name} تعطیل است!")
        return redirect("/")

    slots = generate_time_slots(schedule["start_time"], schedule["end_time"])
    available = [s for s in slots if is_time_available(date_str, s)]

    if not available:
        flash(f"در {day_name} ({date_str}) همه زمان‌ها پر است!")
        return redirect("/")

    return render_template("index.html", 
                         selected_date=date_str, 
                         day_name=day_name,
                         slots=available)

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"].strip()
    phone = request.form["phone"].strip()
    date = request.form["date"]
    time_slot = request.form["time_slot"]

    if len(name.split()) < 2:
        flash("نام و نام خانوادگی کامل وارد کنید!")
        return redirect(f"/book/{date}/{PersianCalendar.get_persian_day_name(jdatetime.datetime.strptime(date, '%Y/%m/%d').weekday())}")

    if not phone.startswith("09") or len(phone) != 11:
        flash("شماره موبایل معتبر نیست!")
        return redirect(f"/book/{date}/...")

    # چک دوباره (جلوگیری از تداخل)
    if not is_time_available(date, time_slot):
        flash("این زمان دیگر در دسترس نیست!")
        return redirect("/")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO bookings (customer_name, customer_phone, booking_date, booking_time) VALUES (?, ?, ?, ?)",
                (name, phone, date, time_slot))
    conn.commit()
    conn.close()

    flash(f"رزرو شما با موفقیت ثبت شد! شماره رزرو: {cur.lastrowid}")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)