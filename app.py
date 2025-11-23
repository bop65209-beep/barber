# app.py - نسخه کامل و مستقل (بدون نیاز به فایل‌های دیگه)
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import jdatetime
from typing import List, Tuple

app = Flask(__name__)
app.secret_key = "supersecretkey"

# دیتابیس داخلی
DB_PATH = "barbershop.db"

# ایجاد جدول‌ها (داخل کد)
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # جدول برنامه هفتگی
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_name TEXT UNIQUE,
            is_open BOOLEAN DEFAULT 1,
            start_time TEXT DEFAULT "09:00",
            end_time TEXT DEFAULT "17:00"
        )
    """)
    
    # جدول رزروها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # روزهای پیش‌فرض (اگر جدول خالی باشه)
    days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    for day in days:
        cursor.execute("""
            INSERT OR IGNORE INTO daily_schedules (day_name, is_open, start_time, end_time)
            VALUES (?, 1, "09:00", "17:00")
        """, (day,))
    
    conn.commit()
    conn.close()

# تابع برنامه روزانه
def get_daily_schedule(day_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_schedules WHERE day_name = ?", (day_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "day_name": row[1], "is_open": bool(row[2]), "start_time": row[3], "end_time": row[4]}
    return None

# تابع چک رزرو
def get_bookings_count_by_date_time(booking_date, booking_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE booking_date = ? AND booking_time = ?", (booking_date, booking_time))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# تقویم شمسی
class PersianCalendar:
    @staticmethod
    def get_jalali_week_dates() -> List[Tuple[str, str]]:
        today = jdatetime.date.today()
        start_of_week = today - jdatetime.timedelta(days=today.weekday())
        week_days = []
        days = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
        for i in range(7):
            current = start_of_week + jdatetime.timedelta(days=i)
            week_days.append((days[i], current.strftime("%Y/%m/%d")))
        return week_days

# تولید زمان‌ها
def generate_time_slots(start_time: str, end_time: str, slot_minutes: int = 30) -> List[str]:
    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    slots = []
    current = start
    while current + datetime.timedelta(minutes=slot_minutes) <= end:
        next_time = current + datetime.timedelta(minutes=slot_minutes)
        slots.append(f"{current.strftime('%H:%M')} - {next_time.strftime('%H:%M')}")
        current = next_time
    return slots

# چک آزاد بودن زمان
def is_time_available(booking_date: str, booking_time: str) -> bool:
    return get_bookings_count_by_date_time(booking_date, booking_time) == 0

# ثبت رزرو
def save_booking(customer_name, customer_phone, booking_date, booking_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (customer_name, customer_phone, booking_date, booking_time)
        VALUES (?, ?, ?, ?)
    """, (customer_name, customer_phone, booking_date, booking_time))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return booking_id

# ———————————————————————— روت‌ها ————————————————————————
@app.route("/")
def index():
    week = PersianCalendar.get_jalali_week_dates()
    return render_template("index.html", week=week)

@app.route("/book/<date_str>/<day_name>")
def book(date_str, day_name):
    schedule = get_daily_schedule(day_name)
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
        return redirect(f"/book/{date}/{day_name}")

    if not phone.isdigit() or len(phone) < 10:
        flash("شماره تلفن معتبر وارد کنید!")
        return redirect(f"/book/{date}/{day_name}")

    # چک دوباره (جلوگیری از تداخل)
    if not is_time_available(date, time_slot):
        flash("این زمان دیگر در دسترس نیست!")
        return redirect("/")

    booking_id = save_booking(name, phone, date, time_slot)
    flash(f"رزرو با موفقیت ثبت شد! شماره رزرو: #{booking_id}")
    return redirect("/")

# راه‌اندازی اولیه
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
