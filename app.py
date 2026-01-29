from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import joblib
import os

# -------------------- APP SETUP --------------------

app = Flask(__name__)
app.secret_key = "lt_hospital_secret_key"

# REQUIRED FOR RENDER (HTTPS SESSIONS)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

# -------------------- DATABASE --------------------

DB_NAME = "appointments.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- LOAD ML MODEL --------------------

MODEL_PATH = os.path.join("ml", "risk_model.pkl")
model = joblib.load(MODEL_PATH)

# -------------------- HOME & STATIC PAGES --------------------

@app.route("/")
def index():
    return render_template("index.html")

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
    # SUPPORT BOTH JSON & FORM DATA (IMPORTANT FOR LIVE SERVER)
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

    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM appointments
        ORDER BY priority ASC, id ASC
    """).fetchall()
    conn.close()

    appointments = []
    for r in rows:
        appointments.append({
            "id": r["id"],
            "patient_name": r["patient_name"],
            "symptoms": r["symptoms"].split(","),
            "severity_score": r["severity_score"],
            "risk_level": r["risk_level"],
            "priority": r["priority"]
        })

    return render_template("doctor.html", appointments=appointments)

@app.route("/delete-appointment/<int:appointment_id>", methods=["POST"])
def delete_appointment(appointment_id):
    if not session.get("doctor_logged_in"):
        return redirect(url_for("doctor_login"))

    conn = get_db()
    conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("doctor_dashboard"))

# -------------------- RUN APP --------------------

if __name__ == "__main__":
    app.run()
