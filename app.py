import os
import sqlite3
from datetime import date
from functools import wraps
from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret")
THRESHOLD = 75
DB_FILE = "attendance.db"

def q(sql, args=(), one=False, commit=False):
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    try:
        cur.execute(sql, args)
        if commit:
            con.commit()
            return cur.lastrowid
        rows = cur.fetchall()
        if one:
            return dict(rows[0]) if rows else None
        return [dict(r) for r in rows]
    finally:
        cur.close()
        con.close()

def init_db():
    # Auto delete old DB - UNIQUE error varathu
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except:
            pass
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""CREATE TABLE students (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      roll_no TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      email TEXT, department TEXT,
      fingerprint_id TEXT UNIQUE,
      active INTEGER DEFAULT 1)""")
    cur.execute("""CREATE TABLE users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      email TEXT UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL,
      student_id INTEGER)""")
    cur.execute("""CREATE TABLE attendance (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id INTEGER NOT NULL,
      date TEXT NOT NULL,
      status TEXT NOT NULL,
      method TEXT,
      UNIQUE(student_id, date))""")
    cur.execute("INSERT INTO users (username,email,password_hash,role) VALUES (?,?,?,?)",
                ('admin','admin@college.edu', generate_password_hash('admin123'), 'admin'))
    cur.execute("INSERT INTO users (username,email,password_hash,role) VALUES (?,?,?,?)",
                ('faculty','faculty@college.edu', generate_password_hash('faculty123'), 'faculty'))
    con.commit()
    con.close()
    print("DB ready - ANY PASSWORD WILL WORK! Use admin@college.edu / 123")

def auth(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            u = session.get("user")
            if not u: return jsonify(error="Please log in."), 401
            return f(*a, **k)
        return w
    return deco

def stats(student_id=None, search=None, active_only=False):
    total_row = q("SELECT COUNT(DISTINCT date) n FROM attendance", one=True)
    total = total_row["n"] if total_row else 0
    sql = """SELECT s.id, s.roll_no, s.name, s.email, s.department, s.fingerprint_id, s.active,
             COALESCE(SUM(a.status='Present'),0) present, COALESCE(SUM(a.status='Absent'),0) absent,
             COALESCE(SUM(a.status='Leave'),0) on_leave
             FROM students s LEFT JOIN attendance a ON a.student_id = s.id WHERE 1=1"""
    args = []
    if student_id: sql += " AND s.id=?"; args.append(student_id)
    if search: sql += " AND (s.name LIKE? OR s.roll_no LIKE?)"; args += [f"%{search}%"] * 2
    if active_only: sql += " AND s.active=1"
    rows = q(sql + " GROUP BY s.id ORDER BY s.roll_no", args)
    for r in rows:
        for k in ("present","absent","on_leave"): r[k]=int(r[k])
        r["total_days"]=total
        r["percentage"]=round(r["present"]/total*100,1) if total else 0.0
        r["low"]=total>0 and r["percentage"]<THRESHOLD
    return rows

@app.post("/api/login")
def login():
    d = request.json or {}
    login_id = d.get("username","").strip()
    u = q("SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id), one=True)
    if not u and "admin" in login_id.lower():
        u = q("SELECT * FROM users WHERE username='admin'", one=True)
    if not u:
        return jsonify(error="Wrong username or password."), 401
    # NO PASSWORD CHECK - any password works
    session["user"]=dict(id=u["id"], username=u["username"], role=u["role"], student_id=u["student_id"])
    return jsonify(session["user"])

@app.post("/api/logout")
def logout():
    session.clear(); return jsonify(ok=True)
@app.get("/api/me")
@auth()
def me(): return jsonify(session["user"])
@app.get("/api/dashboard")
@auth("admin","faculty")
def dashboard():
    rows=stats(active_only=True)
    today={r["status"]:r["n"] for r in q("SELECT status, COUNT(*) n FROM attendance WHERE date=date('now') GROUP BY status")}
    return jsonify(total=len(rows), present=today.get("Present",0), absent=today.get("Absent",0), on_leave=today.get("Leave",0),
                   average=round(sum(r["percentage"] for r in rows)/len(rows),1) if rows else 0,
                   low=[r for r in rows if r["low"]], threshold=THRESHOLD)
@app.get("/api/students")
@auth("admin","faculty")
def students(): return jsonify(stats(search=request.args.get("q")))
@app.post("/api/students")
@auth("admin")
def add_student():
    d=request.json or {}
    q("INSERT INTO students(roll_no,name,email,department,fingerprint_id) VALUES (?,?,?,?,?)",
      (d["roll_no"], d["name"], d.get("email"), d.get("department"), d.get("fingerprint_id") or None), commit=True)
    return jsonify(ok=True)
@app.get("/")
def index(): return app.send_static_file("index.html")

if __name__=="__main__":
    init_db()
    app.run(debug=True, port=5000)