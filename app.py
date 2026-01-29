from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import pandas as pd
import numpy as np
import sqlite3
from joblib import load

app = Flask(__name__)
app.secret_key = "lt_hospital_secret_key"

# =============================
# DOCTOR CREDENTIALS (DEMO)
# =============================
DOCTOR_USERNAME = "doctor"
DOCTOR_PASSWORD = "doctor123"

# =============================
# LOAD ML MODEL
# =============================
model = load("ml/risk_model.pkl")

# =============================
# LOAD SYMPTOM SEVERITY DATA
# =============================
symptom_df = pd.read_csv("data/Symptom-severity.csv")
symptom_weight_map = dict(
    zip(symptom_df["Symptom"].str.lower(), symptom_df["weight"])
)

# =============================
# DATABASE HELPERS
# =============================
def get_db_connection():
    conn = sqlite3.connect("appointments.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
    conn.close()

init_db()

# =============================
# HOME & STATIC PAGES
# =============================
@app.route("/")
def status():
    return "Doctor-Patient Risk Assessment API is running"

@app.route("/home")
def home():
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

# =============================
# PATIENT PAGE
# =============================
@app.route("/patient")
def patient_ui():
    return render_template("patient.html")

# =============================
# DOCTOR LOGIN
# =============================
@app.route("/doctor-login")
def doctor_login_page():
    return render_template("doctor_login.html")

@app.route("/doctor-login", methods=["POST"])
def doctor_login():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == DOCTOR_USERNAME and password == DOCTOR_PASSWORD:
        session["doctor_logged_in"] = True
        return redirect(url_for("doctor_ui"))
    else:
        return render_template(
            "doctor_login.html",
            error="Invalid username or password"
        )

@app.route("/logout")
def logout():
    session.pop("doctor_logged_in", None)
    return redirect(url_for("home"))

# =============================
# DOCTOR DASHBOARD (PROTECTED)
# =============================
@app.route("/doctor")
def doctor_ui():
    if not session.get("doctor_logged_in"):
        return redirect(url_for("doctor_login_page"))
    return render_template("doctor.html")

# =============================
# BOOK APPOINTMENT
# =============================
@app.route("/book-appointment", methods=["POST"])
def book_appointment():
    data = request.get_json()

    patient_name = data.get("patient_name")
    symptoms = data.get("symptoms", [])

    if not patient_name or not symptoms:
        return jsonify({"error": "Patient name and symptoms required"}), 400

    total_severity = sum(
        symptom_weight_map.get(sym.lower(), 0)
        for sym in symptoms
    )

    prediction = model.predict(np.array([[total_severity]]))[0]
    risk = "High Risk" if prediction == 1 else "Low Risk"
    priority = 1 if risk == "High Risk" else 2

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments
        (patient_name, symptoms, severity_score, risk_level, priority)
        VALUES (?, ?, ?, ?, ?)
    """, (
        patient_name,
        ",".join(symptoms),
        total_severity,
        risk,
        priority
    ))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Appointment booked successfully",
        "risk_level": risk,
        "priority": priority
    })

# =============================
# VIEW APPOINTMENTS (DOCTOR)
# =============================
@app.route("/appointments")
def view_appointments():
    if not session.get("doctor_logged_in"):
        return redirect(url_for("doctor_login_page"))

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM appointments
        ORDER BY priority ASC, id ASC
    """).fetchall()
    conn.close()

    return jsonify([
        {
            "id": row["id"],
            "patient_name": row["patient_name"],
            "symptoms": row["symptoms"].split(","),
            "severity_score": row["severity_score"],
            "risk_level": row["risk_level"],
            "priority": row["priority"]
        }
        for row in rows
    ])

# =============================
# DELETE APPOINTMENT (DOCTOR)
# =============================
@app.route("/delete-appointment/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    if not session.get("doctor_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM appointments WHERE id = ?",
        (appointment_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Appointment marked as consulted and removed"
    })

# =============================
# RUN SERVER
# =============================
if __name__ == "__main__":
    app.run(debug=True)
