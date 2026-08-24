import os
import json
import time
import base64
import sqlite3
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)

# ============================================================
#  CONFIG — แก้ตรงนี้ให้ตรงกับเครื่อง AI Server จริงของทีมคุณ
# ============================================================
FORGE_API_URL = "http://192.168.1.185:7860"   # IP ของเครื่อง AI Server (Stability Matrix / Forge)
FORGE_API_USER = "admin"                     # ต้องตรงกับ --api-auth ที่ตั้งไว้ใน Launch Options
FORGE_API_PASS = "cdti1234"

SECRET_KEY = "change-this-to-a-long-random-string-before-deploy"  # TODO: เปลี่ยนก่อนใช้งานจริง

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
#  APP SETUP
# ============================================================
app = Flask(__name__)
app.secret_key = SECRET_KEY

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "กรุณาเข้าสู่ระบบก่อนใช้งาน"
login_manager.login_message_category = "error"


# ---------- DB helpers ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            negative_prompt TEXT,
            steps INTEGER,
            cfg_scale REAL,
            width INTEGER,
            height INTEGER,
            sampler TEXT,
            seed INTEGER,
            checkpoint TEXT,
            image_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()

    # --- migration: เผื่อฐานข้อมูลเก่าที่สร้างมาก่อนมีคอลัมน์ is_admin ---
    existing_cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    if "is_admin" not in existing_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # --- migration: เผื่อฐานข้อมูลเก่าที่สร้างมาก่อนมีคอลัมน์ checkpoint ---
    existing_gen_cols = [row["name"] for row in conn.execute("PRAGMA table_info(generations)")]
    if "checkpoint" not in existing_gen_cols:
        conn.execute("ALTER TABLE generations ADD COLUMN checkpoint TEXT")
        conn.commit()

    # ถ้ายังไม่มี admin เลยสักคน ให้ยกคนที่สมัครสมาชิกไว้ก่อนใครเป็น admin อัตโนมัติ
    has_admin = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_admin = 1").fetchone()["c"]
    if not has_admin:
        conn.execute(
            "UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)"
        )
        conn.commit()

    conn.close()


# ---------- Flask-Login user model ----------
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = bool(is_admin)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return User(row["id"], row["username"], row["is_admin"])
    return None


# ============================================================
#  AUTH ROUTES
# ============================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not password:
            flash("กรุณากรอก username และ password ให้ครบ", "error")
            return redirect(url_for("register"))
        if len(password) < 4:
            flash("password ต้องยาวอย่างน้อย 4 ตัวอักษร", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("รหัสผ่านทั้งสองช่องไม่ตรงกัน", "error")
            return redirect(url_for("register"))

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            flash("username นี้มีคนใช้แล้ว", "error")
            return redirect(url_for("register"))

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), datetime.utcnow().isoformat()),
        )
        new_user_id = cursor.lastrowid

        # ถ้ายังไม่มี admin คนไหนในระบบเลย ให้คนที่เพิ่งสมัครนี้เป็น admin คนแรกอัตโนมัติ
        has_admin = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_admin = 1").fetchone()["c"]
        if not has_admin:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (new_user_id,))

        conn.commit()
        conn.close()
        flash("สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if row and check_password_hash(row["password_hash"], password):
            login_user(User(row["id"], row["username"], row["is_admin"]))
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("username หรือ password ไม่ถูกต้อง", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ============================================================
#  MAIN PAGE
# ============================================================
@app.route("/")
@login_required
def index():
    conn = get_db()
    history = conn.execute(
        "SELECT * FROM generations WHERE user_id = ? ORDER BY id DESC LIMIT 24",
        (current_user.id,),
    ).fetchall()
    conn.close()
    return render_template("generate.html", history=history)


# ============================================================
#  ADMIN: ดูภาพที่ทุก user สร้าง พร้อม prompt/ค่าตั้งค่า
# ============================================================
ADMIN_RECORD_LIMIT = 300  # กันโหลดหนักถ้าข้อมูลเยอะมาก


@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        flash("หน้านี้สำหรับ admin เท่านั้น", "error")
        return redirect(url_for("index"))

    conn = get_db()
    records = conn.execute(
        """
        SELECT generations.*, users.username AS username
        FROM generations
        JOIN users ON generations.user_id = users.id
        ORDER BY generations.id DESC
        LIMIT ?
        """,
        (ADMIN_RECORD_LIMIT,),
    ).fetchall()
    total_count = conn.execute("SELECT COUNT(*) AS c FROM generations").fetchone()["c"]
    conn.close()

    return render_template(
        "admin.html",
        records=records,
        total_count=total_count,
        shown_count=len(records),
    )


@app.route("/admin/delete/<int:record_id>", methods=["POST"])
@login_required
def admin_delete(record_id):
    if not current_user.is_admin:
        flash("หน้านี้สำหรับ admin เท่านั้น", "error")
        return redirect(url_for("index"))

    conn = get_db()
    record = conn.execute(
        "SELECT * FROM generations WHERE id = ?", (record_id,)
    ).fetchone()

    if not record:
        conn.close()
        flash("ไม่พบรายการนี้ (อาจถูกลบไปแล้ว)", "error")
        return redirect(url_for("admin"))

    # ลบไฟล์ภาพออกจากดิสก์ด้วย ไม่ใช่แค่ลบ record ใน DB
    # (image_path ที่เก็บไว้เป็นรูปแบบ "outputs/xxx.png" ซึ่งอยู่ใต้โฟลเดอร์ static/)
    image_full_path = os.path.join(BASE_DIR, "static", record["image_path"])
    if os.path.isfile(image_full_path):
        try:
            os.remove(image_full_path)
        except OSError:
            pass  # ลบไฟล์ไม่สำเร็จก็ไม่เป็นไร อย่างน้อย record ใน DB ต้องลบได้

    conn.execute("DELETE FROM generations WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    flash("ลบรายการนี้แล้ว", "success")
    return redirect(url_for("admin"))


# ============================================================
#  API: samplers (สำหรับทำ dropdown ให้เหมือนใน Forge)
# ============================================================
@app.route("/api/samplers")
@login_required
def api_samplers():
    try:
        resp = requests.get(
            f"{FORGE_API_URL}/sdapi/v1/samplers",
            auth=(FORGE_API_USER, FORGE_API_PASS),
            timeout=10,
        )
        resp.raise_for_status()
        names = [s["name"] for s in resp.json()]
        return jsonify(names)
    except requests.exceptions.RequestException:
        # เผื่อ AI Server ต่อไม่ติดตอนโหลดหน้า ให้ fallback เป็นค่าที่พบบ่อย
        return jsonify(["Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "DPM++ 2M Karras"])


# ============================================================
#  API: checkpoints (รายชื่อโมเดล/checkpoint ที่มีในเครื่อง AI Server)
# ============================================================
@app.route("/api/checkpoints")
@login_required
def api_checkpoints():
    try:
        resp = requests.get(
            f"{FORGE_API_URL}/sdapi/v1/sd-models",
            auth=(FORGE_API_USER, FORGE_API_PASS),
            timeout=10,
        )
        resp.raise_for_status()
        # title คือค่าที่ต้องใช้ตอนสั่งสลับ checkpoint ผ่าน API
        # model_name คือชื่อที่อ่านง่ายกว่า เอาไว้โชว์ใน dropdown
        checkpoints = [
            {"title": m["title"], "model_name": m.get("model_name", m["title"])}
            for m in resp.json()
        ]
        return jsonify(checkpoints)
    except requests.exceptions.RequestException:
        return jsonify([])  # ให้ frontend รู้ว่าดึงไม่ได้ แล้วซ่อน dropdown นี้ไป


# ============================================================
#  API: png-info (อ่าน prompt/ค่าตั้งค่าที่ฝังอยู่ในไฟล์ PNG)
# ============================================================
@app.route("/api/png-info", methods=["POST"])
@login_required
def api_png_info():
    uploaded = request.files.get("image")
    if not uploaded or uploaded.filename == "":
        return jsonify({"error": "กรุณาเลือกไฟล์ภาพ"}), 400

    raw_bytes = uploaded.read()
    if not raw_bytes:
        return jsonify({"error": "ไฟล์ภาพว่างเปล่าหรืออ่านไม่ได้"}), 400

    b64_image = "data:image/png;base64," + base64.b64encode(raw_bytes).decode()

    try:
        resp = requests.post(
            f"{FORGE_API_URL}/sdapi/v1/png-info",
            json={"image": b64_image},
            auth=(FORGE_API_USER, FORGE_API_PASS),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"เชื่อมต่อ AI Server ไม่ได้: {e}"}), 502

    result = resp.json()
    info_text = result.get("info") or ""
    if not info_text.strip():
        return jsonify({"error": "ไฟล์นี้ไม่มีข้อมูล generation ฝังอยู่ (อาจไม่ใช่ภาพที่สร้างจาก Stable Diffusion)"}), 422

    parsed = result.get("parameters") or {}

    return jsonify({
        "info": info_text,      # ข้อความดิบทั้งหมด เผื่ออยากโชว์แบบเต็ม ๆ
        "parameters": parsed,   # dict ที่ parse มาให้แล้ว เช่น prompt/steps/cfg_scale/seed
    })


# ============================================================
#  API: generate (text-to-image)
# ============================================================
@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    data = request.get_json(force=True, silent=True) or {}

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "กรุณากรอก prompt"}), 400

    negative_prompt = data.get("negative_prompt", "")
    sampler = data.get("sampler") or "Euler a"
    checkpoint = (data.get("checkpoint") or "").strip()  # ค่าว่าง = ใช้ checkpoint ที่โหลดอยู่ตอนนี้

    try:
        steps = int(data.get("steps", 20))
        cfg_scale = float(data.get("cfg_scale", 7))
        width = int(data.get("width", 512))
        height = int(data.get("height", 512))
        seed = int(data.get("seed", -1))
    except (TypeError, ValueError):
        return jsonify({"error": "ค่าพารามิเตอร์ไม่ถูกต้อง"}), 400

    # กันค่าที่มากเกินไปจนเครื่อง AI Server ค้างนาน/พังได้
    steps = max(1, min(steps, 50))
    cfg_scale = max(1, min(cfg_scale, 30))
    width = max(64, min(width, 1024))
    height = max(64, min(height, 1024))

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "sampler_name": sampler,
        "seed": seed,
        "batch_size": 1,
        # ไม่ต้องให้ Forge เซฟไฟล์ซ้ำไว้ในเครื่อง AI Server เอง
        # เพราะเว็บเราจะเซฟภาพ + บันทึกลง SQLite ของตัวเองอยู่แล้ว
        "do_not_save_samples": True,
        "do_not_save_grid": True,
    }

    if checkpoint:
        # สั่งสลับ checkpoint ก่อน generate — ถ้าเป็น checkpoint เดียวกับที่โหลดอยู่แล้ว
        # Forge จะข้ามขั้นตอนโหลดใหม่ให้เอง ไม่ได้ช้าซ้ำทุกครั้ง
        # restore_afterwards=False เพื่อให้ checkpoint นี้ค้างเป็นค่าปัจจุบันต่อไป
        # (ไม่ต้องสลับกลับไปกลับมาทุก request ซึ่งจะช้ามาก)
        payload["override_settings"] = {"sd_model_checkpoint": checkpoint}
        payload["override_settings_restore_afterwards"] = False

    try:
        resp = requests.post(
            f"{FORGE_API_URL}/sdapi/v1/txt2img",
            json=payload,
            auth=(FORGE_API_USER, FORGE_API_PASS),
            timeout=300,  # generate อาจใช้เวลานาน ต้องกันไม่ให้ timeout เร็วเกินไป
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"เชื่อมต่อ AI Server ไม่ได้: {e}"}), 502

    result = resp.json()
    images = result.get("images") or []
    if not images:
        return jsonify({"error": "AI Server ไม่ได้ส่งภาพกลับมา"}), 502

    # ตอนขอ seed = -1 (สุ่ม) Forge จะไม่ส่ง seed กลับมาใน "images"
    # แต่ค่า seed จริงที่ใช้ไปจะอยู่ใน field "info" (เป็น JSON string) แทน
    # ต้อง parse ตรงนี้เพื่อเอาค่าจริงมาเก็บ ไม่งั้นในฐานข้อมูล/หน้า admin จะเห็นแต่ -1 ตลอด
    actual_seed = seed
    actual_checkpoint = checkpoint or None
    try:
        info = json.loads(result.get("info") or "{}")
        if info.get("seed") is not None:
            actual_seed = info["seed"]
        # ถ้าไม่ได้เลือก checkpoint เอง ให้ลองอ่านชื่อโมเดลที่ Forge ใช้จริงกลับมาแทน
        if not actual_checkpoint and info.get("sd_model_name"):
            actual_checkpoint = info["sd_model_name"]
    except (ValueError, TypeError):
        pass  # ถ้า parse ไม่ได้ ก็ fallback ไปใช้ค่าที่มีอยู่แล้วแทน

    image_bytes = base64.b64decode(images[0])
    filename = f"{current_user.id}_{int(time.time() * 1000)}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    conn = get_db()
    conn.execute(
        """INSERT INTO generations
           (user_id, prompt, negative_prompt, steps, cfg_scale, width, height, sampler, seed, checkpoint, image_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (current_user.id, prompt, negative_prompt, steps, cfg_scale, width, height, sampler, actual_seed,
         actual_checkpoint, f"outputs/{filename}", datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "image_url": url_for("static", filename=f"outputs/{filename}"),
        "prompt": prompt,
        "seed": actual_seed,
    })


if __name__ == "__main__":
    init_db()
    # host="0.0.0.0" เพื่อให้เครื่องอื่นในวง LAN (เช่นเครื่อง Nginx / Frontend) ยิงเข้ามาได้
    app.run(host="0.0.0.0", port=5000, debug=True)
