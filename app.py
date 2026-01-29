from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3

# -------------------- APP SETUP --------------------

app = Flask(__name__)
app.secret_key = "lt_hospital_secret_key"

# Required for HTTPS (Render)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

# -------------------- DATABASE --------------------

DB_NAME = "appointments.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    # Ensure table always exists (Render-safe)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            symptoms TEXT NOT NULL,
            severity_score INTEGER,
            risk_level TEXT,
            priority INTEGER
        )
    """)
    conn.commit()
    return conn

# -------------------- HOME & STATIC PAGES --------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return redirect(url_for("index"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/packages")
def packages():
    return render_template("packages.html")

@app.route("/specialities")
def specialities():
    return render_template("specialities.html")

# -------------------- PATIENT --------------------

@app.route("/patient")
def patient():
    return render_template("patient.html")

@app.route("/book-appointment", methods=["POST"])
def book_appointment():
    # Accept both form and JSON
    if request.is_json:
        data = request.get_json()
        patient_name = data.get("patient_name")
        symptoms = data.get("symptoms", [])
    else:
        patient_name = request.form.get("patient_name")
        symptoms = request.form.getlist("symptoms")

    if not patient_name or not symptoms:
        return jsonify({"error": "Patient name and symptoms required"}), 400

    severity_score = len(symptoms) * 5

    if severity_score >= 15:
        risk_level = "High Risk"
        priority = 1
    elif severity_score >= 10:
        risk_level = "Medium Risk"
        priority = 2
    else:
        risk_level = "Low Risk"
        priority = 3

    conn = get_db()
    conn.execute("""
        INSERT INTO appointments (patient_name, symptoms, severity_score, risk_level, priority)
        VALUES (?, ?, ?, ?, ?)
    """, (
        patient_name,
        ",".join(symptoms),
        severity_score,
        risk_level,
        priority
    ))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Appointment booked successfully",
        "patient_name": patient_name,
        "risk_level": risk_level,
        "priority": priority
    })

# -------------------- DOCTOR LOGIN --------------------

@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "doctor" and password == "doctor123":
            session["doctor_logged_in"] = True
            return redirect(url_for("doctor_dashboard"))

        return render_template("doctor_login.html", error="Invalid credentials")

    return render_template("doctor_login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# -------------------- DOCTOR DASHBOARD --------------------

@app.route("/doctor")
def doctor_dashboard():
    if not session.get("doctor_logged_in"):
        return redirect(url_for("doctor_login"))

    return render_template("doctor.html")

# -------------------- APPOINTMENTS API --------------------

@app.route("/appointments")
def get_appointments():
    if not session.get("doctor_logged_in"):
        return jsonify([]), 401

    conn = get_db()
    rows = conn.execute("""
        SELECT id, patient_name, symptoms, severity_score, risk_level, priority
        FROM appointments
        ORDER BY priority ASC, id ASC
    """).fetchall()
    conn.close()

    return jsonify([
        {
            "id": r["id"],
            "patient_name": r["patient_name"],
            "symptoms": r["symptoms"].split(","),
            "severity_score": r["severity_score"],
            "risk_level": r["risk_level"],
            "priority": r["priority"]
        } for r in rows
    ])

@app.route("/delete-appointment/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    if not session.get("doctor_logged_in"):
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db()
    conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Appointment marked as consulted"})

# -------------------- RUN --------------------

if __name__ == "__main__":
    app.run()
