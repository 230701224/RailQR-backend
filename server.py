from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ DATABASE ------------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_code TEXT UNIQUE,
        location TEXT,
        zone TEXT,
        description TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id INTEGER,
        reported_by INTEGER,
        title TEXT,
        description TEXT,
        severity TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        file_path TEXT,
        file_type TEXT,
        uploaded_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        entity TEXT,
        entity_id INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ------------------ HELPERS ------------------

def log_action(user_id, action, entity, entity_id):
    conn = get_db()
    conn.execute("""
        INSERT INTO audit_logs (user_id, action, entity, entity_id, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, action, entity, entity_id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# ------------------ AUTH ------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["email"],
            data["password"],
            data["role"],
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        return jsonify({"message": "User registered"}), 201
    except:
        return jsonify({"error": "User already exists"}), 400
    finally:
        conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute("""
        SELECT * FROM users WHERE email=? AND password=?
    """, (data["email"], data["password"])).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    token = str(uuid.uuid4())
    return jsonify({
        "token": token,
        "user": dict(user)
    })

# ------------------ TRACK / QR ------------------

@app.route("/track/<track_code>", methods=["GET"])
def get_track(track_code):
    conn = get_db()
    track = conn.execute("""
        SELECT * FROM tracks WHERE track_code=?
    """, (track_code,)).fetchone()
    conn.close()

    if not track:
        return jsonify({"error": "Track not found"}), 404

    return jsonify(dict(track))

# ------------------ CREATE TRACK (ADMIN / SETUP) ------------------

@app.route("/track", methods=["POST"])
def create_track():
    data = request.json
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tracks (track_code, location, zone, description)
        VALUES (?, ?, ?, ?)
    """, (
        data["track_code"],
        data["location"],
        data["zone"],
        data["description"]
    ))

    track_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Track created",
        "track_id": track_id
    }), 201

# ------------------ MAINTENANCE ------------------

@app.route("/maintenance", methods=["POST"])
def create_maintenance():
    data = request.json
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO maintenance_requests
        (track_id, reported_by, title, description, severity, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["track_id"],
        data["reported_by"],
        data["title"],
        data["description"],
        data["severity"],
        "reported",
        datetime.utcnow().isoformat()
    ))

    request_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(data["reported_by"], "Created", "Maintenance", request_id)

    return jsonify({"request_id": request_id}), 201

@app.route("/maintenance/all", methods=["GET"])
def all_maintenance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM maintenance_requests").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/maintenance/user/<int:user_id>", methods=["GET"])
def user_maintenance(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM maintenance_requests WHERE reported_by=?
    """, (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/maintenance/<int:req_id>/status", methods=["PUT"])
def update_status(req_id):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE maintenance_requests SET status=? WHERE id=?
    """, (data["status"], req_id))
    conn.commit()
    conn.close()

    log_action(data["user_id"], "Status Update", "Maintenance", req_id)
    return jsonify({"message": "Status updated"})

# ------------------ UPLOAD ------------------

@app.route("/upload/<int:request_id>", methods=["POST"])
def upload_file(request_id):
    file = request.files["file"]
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    conn = get_db()
    conn.execute("""
        INSERT INTO uploads (request_id, file_path, file_type, uploaded_at)
        VALUES (?, ?, ?, ?)
    """, (
        request_id,
        path,
        file.mimetype,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

    return jsonify({"message": "File uploaded", "path": path})

# ------------------ AI ANALYSIS (MOCK) ------------------

@app.route("/ai/analyze", methods=["POST"])
def ai_analyze():
    return jsonify({
        "damage_detected": True,
        "confidence": 0.91,
        "suggested_action": "Immediate inspection required"
    })

# ------------------ AUDIT LOGS ------------------

@app.route("/audit", methods=["GET"])
def audit_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_logs").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True)
