# ==============================
# FILE: app.py
# ==============================

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

app = Flask(__name__)
app.config['SECRET_KEY'] = "roadguard_secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ==============================
# DATABASE MODELS
# ==============================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_name = db.Column(db.String(100))
    from_location = db.Column(db.String(200))
    to_location = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    distance = db.Column(db.Float, default=0)
    avg_speed = db.Column(db.Float, default=0)

class Pothole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    severity = db.Column(db.String(50))
    speed = db.Column(db.Float)
    time = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================
# LOGIN MANAGER
# ==============================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==============================
# ROUTES
# ==============================

@app.route('/')
def home():
    return redirect(url_for("login"))

# ------------------------------
# LOGIN
# ------------------------------
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for("dashboard"))

    return render_template("login.html")

# ------------------------------
# LOGOUT
# ------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ------------------------------
# DASHBOARD
# ------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    trips = Trip.query.order_by(Trip.id.desc()).all()
    return render_template("dashboard.html", trips=trips)

# ------------------------------
# START TRIP
# ------------------------------
@app.route('/start_trip', methods=["POST"])
@login_required
def start_trip():
    driver = request.form['driver']
    from_loc = request.form['from']
    to_loc = request.form['to']

    new_trip = Trip(
        driver_name=driver,
        from_location=from_loc,
        to_location=to_loc
    )

    db.session.add(new_trip)
    db.session.commit()

    return redirect(url_for("dashboard"))

# ------------------------------
# LIVE DATA FROM RASPBERRY PI
# ------------------------------
@app.route('/raspberry_data', methods=["POST"])
def raspberry_data():
    data = request.json

    trip_id = data.get("trip_id")
    lat = data.get("latitude")
    lon = data.get("longitude")
    severity = data.get("severity")
    speed = data.get("speed")
    distance = data.get("distance")

    trip = Trip.query.get(trip_id)
    if not trip:
        return jsonify({"status": "Trip not found"})

    # Update distance & avg speed
    trip.distance += float(distance)
    trip.avg_speed = float(speed)

    pothole = Pothole(
        trip_id=trip_id,
        latitude=lat,
        longitude=lon,
        severity=severity,
        speed=speed
    )

    db.session.add(pothole)
    db.session.commit()

    return jsonify({"status": "Data Stored"})

# ------------------------------
# HISTORY
# ------------------------------
@app.route('/history')
@login_required
def history():
    trips = Trip.query.filter(Trip.end_time != None).all()
    return render_template("history.html", trips=trips)

# ------------------------------
# ADMIN PANEL
# ------------------------------
@app.route('/admin')
@login_required
def admin():
    total_trips = Trip.query.count()
    total_potholes = Pothole.query.count()
    unsafe = Pothole.query.filter_by(severity="Unsafe").count()

    return render_template("admin.html",
                           total_trips=total_trips,
                           total_potholes=total_potholes,
                           unsafe=unsafe)

# ==============================
# END TRIP + AUTO PDF
# ==============================

@app.route('/end_trip/<int:trip_id>')
@login_required
def end_trip(trip_id):

    trip = Trip.query.get(trip_id)
    potholes = Pothole.query.filter_by(trip_id=trip_id).all()

    if not trip:
        return "Trip Not Found"

    trip.end_time = datetime.utcnow()
    db.session.commit()

    # Calculations
    total_distance = trip.distance
    avg_speed = trip.avg_speed
    total_potholes = len(potholes)
    safe = len([p for p in potholes if p.severity == "Safe"])
    unsafe = len([p for p in potholes if p.severity == "Unsafe"])

    # Create PDF
    filename = f"Trip_Report_{trip.id}.pdf"
    filepath = os.path.join(os.getcwd(), filename)

    doc = SimpleDocTemplate(filepath)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("RoadGuardAI - Trip Report", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Driver Name", trip.driver_name],
        ["From", trip.from_location],
        ["To", trip.to_location],
        ["Start Time", str(trip.start_time)],
        ["End Time", str(trip.end_time)],
        ["Total Distance (km)", f"{total_distance:.2f}"],
        ["Average Speed (km/h)", f"{avg_speed:.2f}"],
        ["Total Potholes", total_potholes],
        ["Safe", safe],
        ["Unsafe", unsafe],
    ]

    table = Table(data, colWidths=[220, 250])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))

    elements.append(Paragraph("Pothole Locations:", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    for p in potholes:
        text = f"Lat: {p.latitude} | Lon: {p.longitude} | Severity: {p.severity} | Speed: {p.speed}"
        elements.append(Paragraph(text, styles["Normal"]))
        elements.append(Spacer(1, 0.1 * inch))

    doc.build(elements)

    return send_file(filepath, as_attachment=True)

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create default user if not exists
        if not User.query.filter_by(username="admin").first():
            user = User(username="admin", password="admin123")
            db.session.add(user)
            db.session.commit()

    app.run(debug=True)