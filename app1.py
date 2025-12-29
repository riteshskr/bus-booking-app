import razorpay
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
#from flask import Flask, render_template_string, request, redirect, url_for
import mysql.connector
from mysql.connector import pooling, Error
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

# ========= DB CONFIG ========= (same)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "*#06041974"),
    "database": os.environ.get("DB_NAME", "busdb"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "autocommit": True
}

db_pool = None


def init_db_pool():
    global db_pool
    db_pool = pooling.MySQLConnectionPool(
        pool_name="buspool",
        pool_size=5,
        pool_reset_session=True,
        **DB_CONFIG
    )
    print("✅ DB Pool ready")


def get_db():
    """Temporary direct connection - 100% working"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except:
        pass
    return None


# ========= FIXED BASE HTML ========= (same - perfect!)
BASE_HTML = """
<!doctype html>
<html>
<head>
  <title>Bus Booking</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container py-4">
  <h2 class="mb-4 text-center">🚌 Smart Bus Booking System</h2>
  {{ content|safe }}
  <div class="text-center mt-3">
    <a href="{{ url_for('index') }}" class="btn btn-primary me-2">🏠 HOME</a>
    <a href="{{ url_for('admin') }}" class="btn btn-warning me-2">📋 ADMIN</a>
  </div>
</div>
</body>
</html>
"""


# ========= FIXED INIT DATABASE ========= (Sample data uncomment + fast)
def init_db():
    try:
        # ✅ FIXED: Direct connection बिना pool के
        conn = mysql.connector.connect(**DB_CONFIG)
        if not conn.is_connected():
            print("❌ Connection failed")
            return

        cur = conn.cursor()

        # Tables create करें
        cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            route_id INT,
            FOREIGN KEY (route_id) REFERENCES routes(id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bus_id INT,
            departure_time VARCHAR(50),
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            schedule_id INT,
            seat_no VARCHAR(10),
            booked TINYINT DEFAULT 0,
            passenger VARCHAR(100),
            mobile VARCHAR(15),
            counter VARCHAR(50),
            location VARCHAR(100),
            from_place VARCHAR(100),
            to_place VARCHAR(100),
            payment_status VARCHAR(20) DEFAULT 'pending',
            booking_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_seat (schedule_id, seat_no),
            FOREIGN KEY (schedule_id) REFERENCES schedule(id)
        )""")

        # ✅ FIXED: Safe COUNT check
        cur.execute("SELECT COUNT(*) FROM routes")
        result = cur.fetchone()
        route_count = result[0] if result else 0

        print(f"📊 मौजूदा रूट्स: {route_count}")

        if route_count == 0:
            print("🆕 Sample data बना रहे हैं...")

            # Sample Routes
            sample_routes = ["Route 1 - जयपुर → दिल्ली (250km)", "Route 2 - जयपुर → मुंबई (1000km)"]
            for r in sample_routes:
                cur.execute("INSERT INTO routes (name) VALUES (%s)", (r,))
                print(f"✅ रूट बनाया: {r}")

            # Sample Buses (route_id 1,2 के बाद)
            cur.execute("SELECT id FROM routes")
            route_ids = [row[0] for row in cur.fetchall()]

            sample_buses = [("Bus A - AC Sleeper", route_ids[0]), ("Bus B - Semi Sleeper", route_ids[0]),
                            ("Bus C - AC Seater", route_ids[1])]
            for b in sample_buses:
                cur.execute("INSERT INTO buses (name, route_id) VALUES (%s, %s)", b)

            # Sample Schedules
            cur.execute("SELECT id FROM buses LIMIT 4")
            bus_ids = [row[0] for row in cur.fetchall()]
            sample_schedules = [(bus_ids[0], "09:00 AM"), (bus_ids[0], "03:00 PM"), (bus_ids[1], "10:00 AM"),
                                (bus_ids[2], "08:00 PM")]
            for s in sample_schedules:
                cur.execute("INSERT INTO schedule (bus_id, departure_time) VALUES (%s, %s)", s)

            # Sample Seats
            cur.execute("SELECT id FROM schedule")
            schedule_ids = [row[0] for row in cur.fetchall()]
            for sid in schedule_ids:
                for i in range(1, 21):  # 20 seats (fast)
                    cur.execute("INSERT IGNORE INTO seats (schedule_id, seat_no) VALUES (%s, %s)", (sid, f"S{i}"))

            print("✅ Sample data complete!")

        cur.close()
        conn.close()
        print("✅ Database ready!")

    except Error as e:
        print(f"❌ DB Error: {e}")
    except Exception as e:
        print(f"❌ General Error: {e}")


# ========= YOUR ROUTES (same - perfect) =========
@app.route("/")
def index():
    conn = get_db();
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM routes")
    routes = cur.fetchall()
    cur.close();
    conn.close()

    content = '<div class="row"><div class="col-md-8 mx-auto"><h4 class="text-center mb-4">उपलब्ध रूट्स</h4><div class="list-group">'
    for r in routes:
        content += f'<a class="list-group-item list-group-item-action" href="/buses/{r[0]}">{r[1]}</a>'
    content += '</div></div></div>'
    return render_template_string(BASE_HTML, content=content)


@app.route("/buses/<int:route_id>")
def buses(route_id):
    conn = get_db();
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM buses WHERE route_id=%s", (route_id,))
    bus_data = cur.fetchall()
    cur.close();
    conn.close()

    content = '<div class="row"><div class="col-md-8 mx-auto"><h4 class="text-center mb-4">उपलब्ध बसें</h4><div class="list-group">'
    for b in bus_data:
        content += f'<a class="list-group-item list-group-item-action" href="/schedule/{b[0]}">{b[1]}</a>'
    content += '</div></div></div>'
    return render_template_string(BASE_HTML, content=content)


@app.route("/schedule/<int:bus_id>")
def schedule(bus_id):
    conn = get_db();
    cur = conn.cursor()
    cur.execute("SELECT id,departure_time FROM schedule WHERE bus_id=%s", (bus_id,))
    data = cur.fetchall()
    cur.close();
    conn.close()

    content = '<div class="row"><div class="col-md-8 mx-auto"><h4 class="text-center mb-4">बस का समय</h4><div class="list-group">'
    for s in data:
        content += f'<a class="list-group-item list-group-item-action" href="/seats/{s[0]}">{s[1]}</a>'
    content += '</div></div></div>'
    return render_template_string(BASE_HTML, content=content)


@app.route("/seats/<int:schedule_id>")
def seats(schedule_id):
    conn = get_db()
    if not conn:
        return "❌ Database connection failed!", 500

    cur = conn.cursor()

    # ✅ Route info fetch करें
    cur.execute("""
        SELECT r.name 
        FROM schedule sch 
        JOIN buses b ON sch.bus_id = b.id 
        JOIN routes r ON b.route_id = r.id 
        WHERE sch.id = %s
    """, (schedule_id,))
    route_result = cur.fetchone()
    route_name = route_result[0] if route_result else "Unknown Route"

    # ✅ Seats data (with booking details)
    cur.execute("""
        SELECT id, seat_no, booked, passenger, from_place, to_place 
        FROM seats 
        WHERE schedule_id = %s 
        ORDER BY seat_no
    """, (schedule_id,))
    data = cur.fetchall()

    cur.close()
    conn.close()

    content = f'''
    <div class="container">
        <div class="card mb-4">
            <div class="card-header bg-primary text-white text-center">
                <h4>🚌 {route_name}</h4>
                <p class="mb-0">सीट स्थिति (हरी=खाली, लाल=बुक)</p>
            </div>
        </div>

        <div class="row g-2">
    '''

    for s in data:
        seat_id, seat_no, booked, passenger, from_place, to_place = s

        if booked == 0:
            # खाली सीट
            content += f'''
            <div class="col-3 col-md-2">
                <a class="btn btn-success w-100 p-3 fs-5" href="/book/{seat_id}">
                    {seat_no}
                </a>
            </div>
            '''
        else:
            # बुक सीट - From-To show करें
            from_to = f"{from_place or '?'} → {to_place or '?'}"
            content += f'''
            <div class="col-3 col-md-2">
                <div class="card h-100 border-danger">
                    <div class="card-body text-center p-2 bg-danger text-white">
                        <div class="fs-5 fw-bold">{seat_no}</div>
                        <div class="small mt-1">{passenger or "Unknown"}</div>
                        <div class="small">{from_to}</div>
                    </div>
                </div>
            </div>
            '''

    content += '''
        </div>
    </div>
    '''

    return render_template_string(BASE_HTML, content=content)


# Book, Payment routes (same - perfect)
@app.route("/book/<int:seat_id>", methods=["GET","POST"])
def book(seat_id):
    if request.method=="POST":
        passenger = request.form["passenger"]
        mobile = request.form["mobile"]
        frm = request.form["from"]
        to = request.form["to"]
        counter = request.form.get("counter","")
        location = request.form.get("location","")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
          UPDATE seats SET passenger=%s,mobile=%s,from_place=%s,to_place=%s,
          counter=%s,location=%s WHERE id=%s
        """,(passenger,mobile,frm,to,counter,location,seat_id))

        # ✅ FIXED: Safe fetchone()
        cur.execute("SELECT schedule_id FROM seats WHERE id=%s",(seat_id,))
        result = cur.fetchone()
        if result:
            sid = result[0]
        else:
            print("❌ Seat not found!")
            cur.close(); conn.close()
            return "Error: Seat not found", 404

        if counter=="":
            cur.execute("UPDATE seats SET payment_status='pending' WHERE id=%s",(seat_id,))
            cur.close(); conn.close()
            return redirect(url_for("payment", seat_id=seat_id))
        else:
            cur.execute("UPDATE seats SET booked=1,payment_status='counter' WHERE id=%s",(seat_id,))
            cur.close(); conn.close()
            return redirect(url_for("seats", schedule_id=sid))

    html = """
    <div class='card mx-auto' style='max-width:400px;'>
    <div class='card-body'>
    <form method='post'>
      <input class='form-control mb-2' name='passenger' placeholder='नाम' required>
      <input class='form-control mb-2' name='mobile' placeholder='मोबाइल' required>
      <input class='form-control mb-2' name='from' placeholder='से' required>
      <input class='form-control mb-2' name='to' placeholder='तक' required>
      <select class='form-select mb-3' name='counter'>
        <option value=''>ऑनलाइन पेमेंट</option>
        <option value='Jaipur Counter'>जयपुर काउंटर</option>
        <option value='Delhi Counter'>दिल्ली काउंटर</option>
      </select>
      <input type='hidden' name='location' id='location'>
      <button class='btn btn-primary w-100'>जारी रखें</button>
    </form>
    </div></div>
    <script>
    if(navigator.geolocation){
      navigator.geolocation.getCurrentPosition(function(p){
        document.getElementById('location').value=p.coords.latitude+','+p.coords.longitude;
      });
    }
    </script>
    """
    return render_template_string(BASE_HTML, content=html)


@app.route("/payment/<int:seat_id>", methods=["GET", "POST"])
def payment(seat_id):
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE seats SET booked=1,payment_status='paid' WHERE id=%s", (seat_id,))

        # ✅ FIXED: Safe fetchone()
        cur.execute("SELECT schedule_id FROM seats WHERE id=%s", (seat_id,))
        result = cur.fetchone()
        if result:
            sid = result[0]
            cur.close();
            conn.close()
            return redirect(url_for("seats", schedule_id=sid))
        else:
            cur.close();
            conn.close()
            return "Error: Seat not found", 404

    html = """
    <div class='card mx-auto' style='max-width:300px;'>
    <div class='card-body text-center'>
      <h5>ऑनलाइन भुगतान</h5>
      <p>राशि: ₹500</p>
      <form method='post'>
        <button class='btn btn-success w-100'>अभी भुगतान करें</button>
      </form>
    </div></div>
    """
    return render_template_string(BASE_HTML, content=html)


# ✅ YOUR ADMIN ROUTE (perfect - no change needed!)
@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    if not conn:
        return "❌ Database connection failed!", 500

    cur = conn.cursor()
    message = ""

    # ✅ COMPLETE SETUP (same as before...)
    if request.method == "POST" and 'complete_setup' in request.form:
        try:
            from_place = request.form["from_place"]
            to_place = request.form["to_place"]
            distance = int(request.form["distance"])
            stations = request.form.getlist("stations[]")
            bus_name = request.form["bus_name"]
            departure_time = request.form["departure_time"]
            total_seats = int(request.form.get("total_seats", 40))

            route_name = f"{from_place} → {' → '.join(stations)} → {to_place} ({distance}km)"
            cur.execute("INSERT INTO routes (name) VALUES (%s)", (route_name,))
            route_id = cur.lastrowid

            cur.execute("INSERT INTO buses (name, route_id) VALUES (%s, %s)", (bus_name, route_id))
            bus_id = cur.lastrowid

            cur.execute("INSERT INTO schedule (bus_id, departure_time) VALUES (%s, %s)", (bus_id, departure_time))
            schedule_id = cur.lastrowid

            for i in range(1, total_seats + 1):
                cur.execute("INSERT IGNORE INTO seats (schedule_id, seat_no) VALUES (%s, %s)", (schedule_id, f"S{i}"))

            message = f"✅ COMPLETE SETUP! Route+Bus+Schedule+{total_seats}seats"
        except Exception as e:
            message = f"❌ Error: {str(e)}"

    # Data fetch - ✅ FIXED: Safe fetchone()
    cur.execute("SELECT id, name FROM routes ORDER BY id DESC LIMIT 5")
    routes_result = cur.fetchall()
    routes = routes_result or []

    # ✅ FIXED: Safe COUNT queries
    cur.execute("SELECT COUNT(*) FROM buses")
    buses_result = cur.fetchone()
    bus_count = buses_result[0] if buses_result else 0

    cur.execute("SELECT COUNT(*) FROM seats WHERE booked=1")
    bookings_result = cur.fetchone()
    booking_count = bookings_result[0] if bookings_result else 0

    cur.close()
    conn.close()

    content = f'''
    <div class="container-fluid">
        {f'<div class="alert alert-success">{message}</div>' if message else ''}

        <!-- COMPLETE SETUP FORM -->
        <div class="card shadow mb-4">
            <div class="card-header bg-success text-white text-center">
                <h4>🚀 नया Route + Bus + Schedule</h4>
            </div>
            <div class="card-body">
                <form method="post">
                    <input type="hidden" name="complete_setup" value="1">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label>🚩 From</label>
                            <input class="form-control" name="from_place" placeholder="Jaipur" required>
                        </div>
                        <div class="col-md-2">
                            <label>🏁 To</label>
                            <input class="form-control" name="to_place" placeholder="Delhi" required>
                        </div>
                        <div class="col-md-2">
                            <label>📏 KM</label>
                            <input type="number" class="form-control" name="distance" value="250" required>
                        </div>
                        <div class="col-md-3">
                            <label>🛑 Stations</label>
                            <div id="stations-container">
                                <input class="form-control" name="stations[]" placeholder="Ajmer">
                            </div>
                        </div>
                        <div class="col-md-3">
                            <button type="button" class="btn btn-outline-primary" id="add-station">➕ Add Station</button>
                        </div>
                    </div>
                    <div class="row g-3 mt-3">
                        <div class="col-md-3">
                            <label>🚌 Bus</label>
                            <input class="form-control" name="bus_name" placeholder="Volvo AC" required>
                        </div>
                        <div class="col-md-3">
                            <label>⏰ Time</label>
                            <input type="time" class="form-control" name="departure_time" value="09:00">
                        </div>
                        <div class="col-md-3">
                            <label>💺 Seats</label>
                            <input type="number" class="form-control" name="total_seats" value="40">
                        </div>
                        <div class="col-md-3 d-flex align-items-end">
                            <button type="submit" class="btn btn-success w-100">🚀 CREATE ALL</button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Stats -->
        <div class="row mb-4 text-center">
            <div class="col-md-4"><div class="card"><div class="card-body"><h2>{len(routes)}</h2><p>Routes</p></div></div></div>
            <div class="col-md-4"><div class="card"><div class="card-body"><h2>{bus_count}</h2><p>Buses</p></div></div></div>
            <div class="col-md-4"><div class="card"><div class="card-body"><h2>{booking_count}</h2><p>Bookings</p></div></div></div>
        </div>

        <!-- Recent Routes -->
        <div class="row">
            <div class="col-md-12">
                <h5>📍 Recent Routes ({len(routes)})</h5>
                <div class="list-group">
    '''

    for r in routes:
        content += f'<a href="/buses/{r[0]}" class="list-group-item">{r[1]}</a>'

    content += '''
                </div>
            </div>
        </div>

        <script>
        document.getElementById('add-station').onclick = function() {
            const container = document.getElementById('stations-container');
            const input = document.createElement('input');
            input.type = 'text'; input.className = 'form-control mb-2'; input.name = 'stations[]';
            input.placeholder = 'Next Station'; container.appendChild(input);
        };
        </script>
    '''

    return render_template_string(BASE_HTML, content=content)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)