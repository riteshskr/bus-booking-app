from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os
from pyngrok import ngrok
app = Flask(__name__)
app.secret_key = "secret123"
DB = "bus.db"

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # Routes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    routes = ["Route 1", "Route 2"]
    for r in routes:
        cur.execute("INSERT OR IGNORE INTO routes (name) VALUES (?)", (r,))

    # Buses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            route_id INTEGER
        )
    """)
    buses = [("Bus A",1), ("Bus B",1), ("Bus C",2)]
    for name, route_id in buses:
        cur.execute("INSERT OR IGNORE INTO buses (name, route_id) VALUES (?,?)", (name, route_id))

    # Schedule (bus + time)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER,
            departure_time TEXT
        )
    """)
    schedules = [(1,"09:00 AM"),(1,"03:00 PM"),(2,"10:00 AM"),(3,"08:00 AM")]
    for bus_id, time in schedules:
        cur.execute("INSERT OR IGNORE INTO schedule (bus_id, departure_time) VALUES (?,?)",(bus_id,time))

    # Seats
    #cur.execute("""DROP TABLE IF EXISTS seats""")
    #conn.commit()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER,
            seat_no TEXT,
            booked INTEGER DEFAULT 0,
            passenger TEXT,
            mobile TEXT,
            counter TEXT,
            from_place text,
            to_place text
        )
    """)
    cur.execute("SELECT id FROM schedule")
    schedule_ids = cur.fetchall()
    for sch in schedule_ids:
        for i in range(1,41):
            cur.execute("INSERT OR IGNORE INTO seats (schedule_id, seat_no) VALUES (?,?)",(sch[0], f"S{i}"))

    conn.commit()
    conn.close()

# ================= HOME =================
@app.route("/", strict_slashes=False)
def index():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM routes")
    routes = cur.fetchall()
    conn.close()
    html = """
    <div style="text-align:center;font-family:Arial;">
        <h1>🚌 Bus Booking System</h1>
        <h2>Select Route</h2>
        <div style="display:inline-block;">
        {% for r in routes %}
            <div style="margin:10px;">
                <a href="/buses/{{r[0]}}" style="font-size:18px;text-decoration:none;background:#3498db;color:white;padding:10px 20px;border-radius:8px;transition:0.3s;">
                    {{r[1]}}
                </a>
            </div>
        {% endfor %}
        </div>
        <br><br><a href="/admin" style="font-size:16px;color:#2c3e50;">🔐 Admin Panel</a>
    </div>
    """
    return render_template_string(html,routes=routes)

# ================= BUS SELECTION =================
@app.route("/buses/<int:route_id>", strict_slashes=False)
def buses(route_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM buses WHERE route_id=?",(route_id,))
    buses = cur.fetchall()
    conn.close()
    html="""
    <div style="text-align:center;font-family:Arial;">
        <h2>Select Bus</h2>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;">
        {% for b in buses %}
            <a href="/schedule/{{b[0]}}" style="margin:8px;font-size:16px;text-decoration:none;background:#1abc9c;color:white;padding:12px 24px;border-radius:8px;transition:0.3s;">
                {{b[1]}}
            </a>
        {% endfor %}
        </div>
        <br><a href="/" style="font-size:16px;color:#2c3e50;">Back</a>
    </div>
    """
    return render_template_string(html,buses=buses)

# ================= SCHEDULE SELECTION =================
@app.route("/schedule/<int:bus_id>", strict_slashes=False)
def schedule(bus_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, departure_time FROM schedule WHERE bus_id=?",(bus_id,))
    schedules = cur.fetchall()
    conn.close()
    html="""
    <div style="text-align:center;font-family:Arial;">
        <h2>Select Departure Time</h2>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;">
        {% for s in schedules %}
            <a href="/seats/{{s[0]}}" style="margin:8px;font-size:16px;text-decoration:none;background:#e67e22;color:white;padding:12px 24px;border-radius:8px;transition:0.3s;">
                {{s[1]}}
            </a>
        {% endfor %}
        </div>
        <br><a href="/buses/{{bus_id}}" style="font-size:16px;color:#2c3e50;">Back</a>
    </div>
    """
    return render_template_string(html,schedules=schedules,bus_id=bus_id)

# ================= SEAT SELECTION =================
@app.route("/seats/<int:schedule_id>", strict_slashes=False)
def seats(schedule_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT id, seat_no, booked, passenger, mobile, from_place, to_place 
    FROM seats WHERE schedule_id=?
    """, (schedule_id,))
    seats = cur.fetchall()
    conn.close()
    html="""
    <div style="text-align:center;font-family:Arial;">
        <h2>Seats</h2>
        <div style="display:flex;flex-wrap:wrap;justify-content:center;">
        {% for s in seats %}
            {% if s[2]==0 %}
                <a href="/book_form/{{s[0]}}" style="margin:5px;width:60px;height:60px;line-height:60px;background:#2ecc71;color:white;border-radius:8px;text-decoration:none;display:inline-block;">
                    {{s[1]}}
                </a>
            {% else %}
                <div style="margin:5px;width:60px;height:60px;line-height:1.2;background:#e74c3c;color:white;border-radius:8px;display:inline-block;">
                   {{s[1]}}<br>{{s[5]}}<br> ➝
                    {{s[6]}}
                    <form method="post" action="/cancel/{{s[0]}}" style="margin-top:2px;">
                        <button style="background:#c0392b;color:white;border:none;padding:3px 6px;border-radius:6px;font-size:10px;cursor:pointer;">Cancel</button>
                    </form>
                </div>
            {% endif %}
        {% endfor %}
        </div>
        <br><a href="/schedule/{{get_bus(schedule_id)}}" style="font-size:16px;color:#2c3e50;">Back</a>
    </div>
    """
    def get_bus(schedule_id):
        conn=sqlite3.connect(DB)
        cur=conn.cursor()
        cur.execute("SELECT bus_id FROM schedule WHERE id=?",(schedule_id,))
        bus_id=cur.fetchone()[0]
        conn.close()
        return bus_id
    return render_template_string(html,seats=seats,get_bus=get_bus,schedule_id=schedule_id)

# ================= BOOK FORM =================
@app.route("/book_form/<int:seat_id>",methods=["GET","POST"], strict_slashes=False)
def book_form(seat_id):
    if request.method=="POST":
        passenger = request.form.get("passenger","").strip()
        mobile = request.form.get("mobile","").strip()
        counter = request.form.get("counter","Online")
        from_place = request.form.get("from_place")
        to_place = request.form.get("to_place")
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("UPDATE seats SET booked=1, passenger=?, mobile=?, counter=?,from_place=?,to_place = ? WHERE id=?",
                    (passenger,mobile,counter,from_place, to_place,seat_id))
        conn.commit()
        cur.execute("SELECT schedule_id FROM seats WHERE id=?",(seat_id,))
        schedule_id = cur.fetchone()[0]
        conn.close()
        return redirect(url_for("seats",schedule_id=schedule_id))
    html="""
    <div style="text-align:center;font-family:Arial;">
        <h3>Booking Details</h3>
        <form method="post">
            Name:<br><input type="text" name="passenger" required style="padding:5px;"><br><br>
            Mobile:<br><input type="text" name="mobile" pattern="[0-9]{10}" placeholder="10 digit" required style="padding:5px;"><br><br>
            From Place:<br> <input type="text" name="from_place" required><br><br>
            To Place:<br><input type="text" name="to_place" required><br><br>
            Booking Counter:<br>
            <select name="counter" required style="padding:5px;">
                <option value="Online">Online</option>
                <option value="Counter A">Counter A</option>
                <option value="Counter B">Counter B</option>
            </select><br><br>
            <button type="submit" style="padding:8px 16px;background:#3498db;color:white;border:none;border-radius:6px;cursor:pointer;">Confirm Booking</button>
        </form>
    </div>
    """
    return render_template_string(html)

# ================= CANCEL =================
@app.route("/cancel/<int:seat_id>",methods=["POST"], strict_slashes=False)
def cancel(seat_id):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE seats SET booked=0,passenger='',mobile='',counter='',from_place = ' ',to_place = ' ' WHERE id=?",(seat_id,))
    conn.commit()
    cur.execute("SELECT schedule_id FROM seats WHERE id=?",(seat_id,))
    schedule_id = cur.fetchone()[0]
    conn.close()
    return redirect(url_for("seats",schedule_id=schedule_id))

# ================= ADMIN PANEL =================
@app.route("/admin",methods=["GET","POST"], strict_slashes=False)
def admin_login():
    msg=""
    if request.method=="POST":
        u=request.form.get("username")
        p=request.form.get("password")
        if u==ADMIN_USER and p==ADMIN_PASS:
            session["admin"]=True
            return redirect(url_for("admin_dashboard"))
        else:
            msg="❌ Invalid Login"
    html="""
    <div style="text-align:center;font-family:Arial;">
        <h2>Admin Login</h2>
        <form method="post">
            Username:<br><input type="text" name="username" required style="padding:5px;"><br><br>
            Password:<br><input type="password" name="password" required style="padding:5px;"><br><br>
            <button type="submit" style="padding:8px 16px;background:#3498db;color:white;border:none;border-radius:6px;cursor:pointer;">Login</button>
        </form>
        <p style="color:red;">{{msg}}</p>
        <br><a href="/" style="font-size:16px;color:#2c3e50;">Back</a>
    </div>
    """
    return render_template_string(html,msg=msg)

@app.route("/admin/dashboard", strict_slashes=False)
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("SELECT id,name FROM routes")
    routes = cur.fetchall()
    conn.close()
    html = "<h2>Admin Dashboard</h2><ul>{% for r in routes %}<li><a href='/admin/buses/{{r[0]}}'>{{r[1]}}</a></li>{% endfor %}</ul><br><a href='/admin/logout'>Logout</a>"
    return render_template_string(html,routes=routes)

# ================= RUN APP =================
if __name__=="__main__":
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)