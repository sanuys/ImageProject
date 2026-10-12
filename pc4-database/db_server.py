"""
============================================================
 PC4 : DATABASE SERVER   (10.187.226.35 : 5100)
------------------------------------------------------------
 โจทย์คือ "แยกฐานข้อมูลออกไปอยู่คนละเครื่องกับ Backend"
 แต่ SQLite เป็นไฟล์ local ไม่มีโปรโตคอลเครือข่ายในตัว
 (แชร์ไฟล์ .db ผ่าน SMB/network drive = ไฟล์พังง่ายมาก ห้ามทำ)

 วิธีที่ถูกต้องคือ ครอบ SQLite ด้วย "บริการเล็ก ๆ" ตัวนี้
 แล้วให้เครื่อง Backend (10.187.226.226) คุยผ่าน HTTP บน LAN แทน
 -> ได้ Distributed System จริง: Backend ไม่แตะไฟล์ .db โดยตรงเลย

 เครื่องนี้เป็นเจ้าของไฟล์ database.db เพียงเครื่องเดียว
============================================================
"""

import os
import sqlite3
import threading

from flask import Flask, request, jsonify

from schema import init_db

# ============================================================
#  CONFIG  — แก้ได้ที่นี่ หรือ override ผ่าน environment variable
# ============================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database.db"))
DB_PORT = int(os.environ.get("DB_PORT", "5100"))

# โทเคนลับ ต้องตรงกับค่า DB_TOKEN ใน pc2-backend/config.py
DB_TOKEN = os.environ.get("DB_TOKEN", "cdti-db-secret-2026")

# อนุญาตเฉพาะ IP ของเครื่อง Backend (และตัวเอง) — ใส่ set() ว่างเพื่อปิดการตรวจ IP
ALLOWED_CLIENT_IPS = {"10.187.226.226", "127.0.0.1", "::1"}

app = Flask(__name__)

# SQLite เขียนพร้อมกันหลาย thread ไม่ได้ ใช้ lock กันไว้ชั้นหนึ่ง
_write_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # ใช้โหมด DELETE (ค่าปกติของ SQLite) แทน WAL
    # เดิมใช้ WAL -> การลบ/เพิ่มข้อมูลจะไปค้างอยู่ในไฟล์ database.db-wal ก่อน
    # ถ้าเปิด database.db ดูด้วยโปรแกรมอื่นค้างไว้ ไฟล์หลักจะยังเห็นข้อมูลเก่า (เหมือนลบไม่ออก)
    # โหมด DELETE เขียนลง database.db ตรง ๆ ทุกครั้งที่ commit — เห็นผลทันที
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ============================================================
#  AUTH: ตรวจโทเคน + IP ต้นทาง ก่อนทุก request
# ============================================================
@app.before_request
def check_client():
    if request.path == "/health":
        return None

    if ALLOWED_CLIENT_IPS and request.remote_addr not in ALLOWED_CLIENT_IPS:
        return jsonify({"error": f"IP {request.remote_addr} ไม่ได้รับอนุญาตให้เข้าถึงฐานข้อมูล"}), 403

    if request.headers.get("X-DB-Token") != DB_TOKEN:
        return jsonify({"error": "DB token ไม่ถูกต้อง"}), 401

    return None


# ============================================================
#  API: /sql  — รัน SQL หนึ่งคำสั่ง
#  body: {"sql": "...", "params": [...], "fetch": "all" | "one" | "none"}
#  resp: {"rows": [...], "lastrowid": int, "rowcount": int}
# ============================================================
@app.route("/sql", methods=["POST"])
def run_sql():
    data = request.get_json(force=True, silent=True) or {}
    sql = (data.get("sql") or "").strip()
    params = data.get("params") or []
    fetch = data.get("fetch", "all")

    if not sql:
        return jsonify({"error": "ไม่ได้ส่งคำสั่ง SQL มา"}), 400

    try:
        with _write_lock:
            conn = get_conn()
            try:
                cur = conn.execute(sql, tuple(params))

                rows = []
                if fetch == "all":
                    rows = [dict(r) for r in cur.fetchall()]
                elif fetch == "one":
                    row = cur.fetchone()
                    rows = [dict(row)] if row else []

                conn.commit()   # autocommit ทุกคำสั่ง — ฝั่ง Backend จึงไม่ต้อง commit เอง

                # แสดง log คำสั่งที่แก้ข้อมูลบนหน้าต่างของเครื่องนี้ ไว้ยืนยันว่าลบ/เพิ่มสำเร็จจริง
                verb = sql.split(None, 1)[0].upper()
                if verb in ("INSERT", "UPDATE", "DELETE"):
                    # แสดง params เฉพาะคำสั่ง DELETE (กันรหัสผ่านที่ hash แล้วโผล่บนจอตอนสมัครสมาชิก)
                    extra = f"  params={params}" if verb == "DELETE" else ""
                    print(f"[DB] {' '.join(sql.split())}{extra}  -> {cur.rowcount} แถว", flush=True)
                result = {
                    "rows": rows,
                    "lastrowid": cur.lastrowid,
                    "rowcount": cur.rowcount,
                }
            finally:
                conn.close()
    except sqlite3.Error as e:
        return jsonify({"error": f"SQL error: {e}"}), 400

    return jsonify(result)


# ============================================================
#  API: /sql/batch — รันหลายคำสั่งใน transaction เดียว (atomic)
#  body: {"statements": [{"sql": "...", "params": [...]}, ...]}
# ============================================================
@app.route("/sql/batch", methods=["POST"])
def run_batch():
    data = request.get_json(force=True, silent=True) or {}
    statements = data.get("statements") or []
    if not statements:
        return jsonify({"error": "ไม่ได้ส่งคำสั่ง SQL มา"}), 400

    lastrowids = []
    try:
        with _write_lock:
            conn = get_conn()
            try:
                for st in statements:
                    cur = conn.execute(st.get("sql", ""), tuple(st.get("params") or []))
                    lastrowids.append(cur.lastrowid)
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                raise
            finally:
                conn.close()
    except sqlite3.Error as e:
        return jsonify({"error": f"SQL error: {e}"}), 400

    return jsonify({"lastrowids": lastrowids})


# ============================================================
#  API: /health — ให้เครื่องอื่นเช็คว่า DB Server ยังมีชีวิต
# ============================================================
@app.route("/health")
def health():
    try:
        conn = get_conn()
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        gens = conn.execute("SELECT COUNT(*) AS c FROM generations").fetchone()["c"]
        edits = conn.execute("SELECT COUNT(*) AS c FROM edits").fetchone()["c"]
        conn.close()
    except sqlite3.Error as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

    return jsonify({
        "status": "ok",
        "role": "database",
        "db_path": DB_PATH,
        "users": users,
        "generations": gens,
        "edits": edits,
    })


if __name__ == "__main__":
    conn = get_conn()
    init_db(conn)
    conn.close()
    print(f"[DB SERVER] ไฟล์ฐานข้อมูล : {DB_PATH}")
    print(f"[DB SERVER] เปิดรับ       : http://0.0.0.0:{DB_PORT}")
    print(f"[DB SERVER] อนุญาต IP     : {ALLOWED_CLIENT_IPS or 'ทุก IP'}")
    # threaded=True เพื่อรับหลาย request พร้อมกันได้ (มี _write_lock กันชนกันอยู่แล้ว)
    app.run(host="0.0.0.0", port=DB_PORT, threaded=True)
