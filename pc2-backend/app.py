"""
============================================================
 PC2 : BACKEND (Flask)   172.20.56.107 : 5000
------------------------------------------------------------
 เครื่องนี้ไม่ render HTML อีกต่อไปแล้ว — เป็น JSON API ล้วน ๆ
   * หน้าเว็บ (HTML/CSS/JS)  อยู่ที่ PC1 เสิร์ฟโดย Nginx
   * ฐานข้อมูล               อยู่ที่ PC4 คุยผ่าน db_client
   * สร้างภาพด้วย AI         อยู่ที่ PC3 คุยผ่าน HTTP (Forge API)
   * ไฟล์ภาพผลลัพธ์          เก็บที่ PC4 (ข้างฐานข้อมูล) route /media/<path> ดึงจาก PC4 มาส่งต่อ
   * แก้ไขภาพ (OpenCV)       ทำบนเครื่องนี้ เพราะเป็นงาน CPU เบา ๆ ไม่ต้องใช้ GPU
============================================================
"""

import json
import mimetypes
import time
import uuid
import base64
from datetime import datetime

import cv2
import numpy as np
import requests
from flask import Flask, Response, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user,
)

import config
from db_client import get_db, db_health, DatabaseError, put_file, get_file, delete_file
import image_ops   # ฟังก์ชัน Image Processing ทั้ง 4 กลุ่ม แยกไว้ในไฟล์ image_ops.py

# ============================================================
#  IMAGE EDITING — ย้ายไปอยู่ที่ image_ops.py ทั้งหมด
#  (Point Operation / Auto Contrast / Linear Filter / Non-linear Filter)
# ============================================================


def media_url(relative_path):
    """แปลง path ที่เก็บใน DB (เช่น outputs/x.png) เป็น URL ที่ browser เรียกได้"""
    return "/media/" + relative_path.lstrip("/")


def _edit_json(row):
    """แปลง row ของตาราง edits ให้เป็น dict ที่ frontend ใช้ได้เลย"""
    d = dict(row)
    try:
        params = json.loads(d.get("params") or "{}")
    except (ValueError, TypeError):
        params = {}
    return {
        "id": d["id"],
        "operation": d["operation"],
        "operation_label": image_ops.operation_label(d["operation"], params),
        "params_summary": image_ops.params_summary(d["operation"], params),
        "source_label": d.get("source_label"),
        "image_url": media_url(d["result_image"]),
        "created_at": d.get("created_at"),
    }


def _generation_json(row):
    d = dict(row)
    return {
        "id": d["id"],
        "prompt": d["prompt"],
        "negative_prompt": d.get("negative_prompt"),
        "steps": d.get("steps"),
        "cfg_scale": d.get("cfg_scale"),
        "width": d.get("width"),
        "height": d.get("height"),
        "sampler": d.get("sampler"),
        "seed": d.get("seed"),
        "checkpoint": d.get("checkpoint"),
        "image_url": media_url(d["image_path"]),
        "created_at": d.get("created_at"),
        "username": d.get("username"),
    }


# ============================================================
#  APP SETUP
# ============================================================
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.unauthorized_handler
def unauthorized():
    """เดิม redirect ไปหน้า login — ตอนนี้เป็น API จึงต้องตอบ JSON 401
    ให้ฝั่ง JS ที่ PC1 พาผู้ใช้ไปหน้า login.html เอง"""
    return jsonify({"error": "กรุณาเข้าสู่ระบบก่อนใช้งาน", "code": "unauthorized"}), 401


# ------------------------------------------------------------
#  CORS — ปกติ browser ยิงผ่าน Nginx ที่ PC1 (same-origin) จึงไม่ได้ใช้
#  แต่เปิดไว้เผื่อเปิดหน้าเว็บตรง ๆ ตอนพัฒนา/ดีบัก
# ------------------------------------------------------------
@app.after_request
def add_cors_headers(resp):
    origin = request.headers.get("Origin")
    if origin and origin in config.ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Vary"] = "Origin"
    return resp


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    resp = app.make_default_options_response()
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


@app.errorhandler(DatabaseError)
def handle_db_error(e):
    """ถ้าเครื่อง PC4 ดับ/ต่อไม่ติด ให้ตอบข้อความที่อ่านเข้าใจแทน 500 เปล่า ๆ"""
    return jsonify({"error": str(e)}), 503


# ------------------------------------------------------------
#  Flask-Login user model
# ------------------------------------------------------------
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = bool(is_admin)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row:
        return User(row["id"], row["username"], row["is_admin"])
    return None


def user_json(user):
    return {"id": user.id, "username": user.username, "is_admin": user.is_admin}


# ============================================================
#  MEDIA — ไฟล์ภาพเก็บอยู่ที่ PC4
#  Nginx ที่ PC1 proxy /media/ มาที่ route นี้ แล้วเครื่องนี้ไปขอไฟล์จาก PC4 ส่งต่อให้
#  (browser ไม่ได้คุยกับ PC4 ตรง ๆ — PC4 รับ request จาก PC2 เท่านั้น)
# ============================================================
@app.route("/media/<path:filename>")
def media(filename):
    data = get_file(filename)
    if data is None:
        return jsonify({"error": "ไม่พบไฟล์ภาพ"}), 404
    mimetype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(data, mimetype=mimetype)


# ============================================================
#  AUTH API
# ============================================================
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""

    if not username or not password:
        return jsonify({"error": "กรุณากรอก username และ password ให้ครบ"}), 400
    if len(password) < 4:
        return jsonify({"error": "password ต้องยาวอย่างน้อย 4 ตัวอักษร"}), 400
    if password != confirm:
        return jsonify({"error": "รหัสผ่านทั้งสองช่องไม่ตรงกัน"}), 400

    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
        return jsonify({"error": "username นี้มีคนใช้แล้ว"}), 409

    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, 0, ?)",
        (username, generate_password_hash(password), datetime.utcnow().isoformat()),
        "none",
    )
    new_user_id = cursor.lastrowid

    # ถ้ายังไม่มี admin คนไหนในระบบเลย ให้คนที่เพิ่งสมัครเป็น admin คนแรกอัตโนมัติ
    has_admin = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE is_admin = 1"
    ).fetchone()["c"]
    if not has_admin:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (new_user_id,), "none")

    return jsonify({"message": "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ"}), 201


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if row and check_password_hash(row["password_hash"], password):
        user = User(row["id"], row["username"], row["is_admin"])
        login_user(user)
        return jsonify({"user": user_json(user)})

    return jsonify({"error": "username หรือ password ไม่ถูกต้อง"}), 401


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "ออกจากระบบแล้ว"})


@app.route("/api/me")
@login_required
def api_me():
    """หน้าเว็บ static ที่ PC1 เรียกตอนโหลดหน้า เพื่อเช็คว่าล็อกอินอยู่ไหม + เป็น admin ไหม"""
    return jsonify({"user": user_json(current_user)})


# ============================================================
#  HISTORY API — ประวัติของผู้ใช้ที่ล็อกอินอยู่
#  (เดิมข้อมูลนี้ถูก render ใส่ HTML โดย Jinja ตอนโหลดหน้า
#   ตอนนี้ HTML เป็น static แล้ว จึงต้องดึงผ่าน API แทน)
# ============================================================
@app.route("/api/history")
@login_required
def api_history():
    conn = get_db()
    generations = conn.execute(
        "SELECT * FROM generations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (current_user.id, config.HISTORY_LIMIT),
    ).fetchall()
    edits = conn.execute(
        "SELECT * FROM edits WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (current_user.id, config.HISTORY_LIMIT),
    ).fetchall()

    return jsonify({
        "generations": [_generation_json(r) for r in generations],
        "edits": [_edit_json(r) for r in edits],
    })


# ============================================================
#  ADMIN API — ดูภาพที่ทุก user สร้าง พร้อม prompt/ค่าตั้งค่า
# ============================================================
@app.route("/api/admin/records")
@login_required
def api_admin_records():
    if not current_user.is_admin:
        return jsonify({"error": "หน้านี้สำหรับ admin เท่านั้น"}), 403

    conn = get_db()
    records = conn.execute(
        """
        SELECT generations.*, users.username AS username
        FROM generations
        JOIN users ON generations.user_id = users.id
        ORDER BY generations.id DESC
        LIMIT ?
        """,
        (config.ADMIN_RECORD_LIMIT,),
    ).fetchall()
    total_count = conn.execute(
        "SELECT COUNT(*) AS c FROM generations"
    ).fetchone()["c"]

    return jsonify({
        "records": [_generation_json(r) for r in records],
        "total_count": total_count,
        "shown_count": len(records),
    })


@app.route("/api/admin/delete/<int:record_id>", methods=["POST"])
@login_required
def api_admin_delete(record_id):
    if not current_user.is_admin:
        return jsonify({"error": "หน้านี้สำหรับ admin เท่านั้น"}), 403

    conn = get_db()
    record = conn.execute(
        "SELECT * FROM generations WHERE id = ?", (record_id,)
    ).fetchone()
    if not record:
        return jsonify({"error": "ไม่พบรายการนี้ (อาจถูกลบไปแล้ว)"}), 404

    # ลบ record ที่ PC4 ก่อน — ถ้า DB ลบไม่สำเร็จจะได้ไม่เสียไฟล์ภาพไปฟรี ๆ
    result = conn.execute("DELETE FROM generations WHERE id = ?", (record_id,), "none")
    if result.rowcount < 1:
        return jsonify({"error": "ลบข้อมูลในฐานข้อมูล (PC4) ไม่สำเร็จ"}), 500

    # แล้วค่อยสั่ง PC4 ลบไฟล์ภาพ
    try:
        delete_file(record["image_path"])
    except DatabaseError:
        pass  # ลบไฟล์ไม่สำเร็จก็ไม่เป็นไร record ใน DB ลบไปแล้ว

    return jsonify({"message": "ลบรายการนี้แล้ว"})


@app.route("/api/edit/delete/<int:record_id>", methods=["POST"])
@login_required
def api_edit_delete(record_id):
    conn = get_db()
    record = conn.execute(
        "SELECT * FROM edits WHERE id = ? AND user_id = ?", (record_id, current_user.id)
    ).fetchone()
    if not record:
        return jsonify({"error": "ไม่พบรายการนี้ หรือไม่ใช่ของคุณ"}), 404

    # ลบ record ก่อน แล้วค่อยสั่งลบไฟล์ภาพ (ทั้งสองอย่างอยู่ที่ PC4)
    result = conn.execute("DELETE FROM edits WHERE id = ?", (record_id,), "none")
    if result.rowcount < 1:
        return jsonify({"error": "ลบข้อมูลในฐานข้อมูล (PC4) ไม่สำเร็จ"}), 500

    try:
        delete_file(record["result_image"])
    except DatabaseError:
        pass

    return jsonify({"message": "ลบรายการแก้ไขนี้แล้ว"})


# ============================================================
#  API: samplers (สำหรับทำ dropdown ให้เหมือนใน Forge)
#  -> ยิงไปที่เครื่อง PC3
# ============================================================
@app.route("/api/samplers")
@login_required
def api_samplers():
    try:
        resp = requests.get(
            f"{config.FORGE_API_URL}/sdapi/v1/samplers",
            auth=(config.FORGE_API_USER, config.FORGE_API_PASS),
            timeout=(5, 10),   # (เชื่อมต่อ, รอผล)
        )
        resp.raise_for_status()
        return jsonify([s["name"] for s in resp.json()])
    except requests.exceptions.RequestException:
        # เผื่อเครื่อง AI Server ต่อไม่ติดตอนโหลดหน้า ให้ fallback เป็นค่าที่พบบ่อย
        return jsonify(["Euler a", "Euler", "DPM++ 2M", "DPM++ SDE", "DPM++ 2M Karras"])


# ============================================================
#  API: checkpoints (รายชื่อโมเดลที่มีในเครื่อง PC3)
# ============================================================
@app.route("/api/checkpoints")
@login_required
def api_checkpoints():
    try:
        resp = requests.get(
            f"{config.FORGE_API_URL}/sdapi/v1/sd-models",
            auth=(config.FORGE_API_USER, config.FORGE_API_PASS),
            timeout=(5, 10),   # (เชื่อมต่อ, รอผล)
        )
        resp.raise_for_status()

        # กรองเหลือเฉพาะ checkpoint ที่อยู่ใน allow-list (config.ALLOWED_CHECKPOINTS)
        # แล้วแนบค่า preset ที่ควรใช้กับ checkpoint นั้นไปด้วย
        checkpoints = []
        for m in resp.json():
            title = m["title"]
            model_name = m.get("model_name", title)
            preset = next(
                (
                    p for p in config.ALLOWED_CHECKPOINTS
                    if p["match"].lower() in title.lower()
                    or p["match"].lower() in model_name.lower()
                ),
                None,
            )
            if preset:
                checkpoints.append({
                    "title": title,            # ค่าที่ใช้ตอนสั่งสลับ checkpoint ผ่าน API
                    "model_name": model_name,  # ชื่อที่อ่านง่ายกว่า เอาไว้โชว์ใน dropdown
                    "sampler": preset["sampler"],
                    "width": preset["width"],
                    "height": preset["height"],
                    "steps": preset.get("steps"),
                    "cfg_scale": preset.get("cfg_scale"),
                })

        return jsonify(checkpoints)
    except requests.exceptions.RequestException:
        return jsonify([])  # ให้ frontend รู้ว่าดึงไม่ได้


# ============================================================
#  API: generate (text-to-image)  -> PC3
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
    checkpoint = (data.get("checkpoint") or "").strip()  # ว่าง = ใช้ checkpoint ที่โหลดอยู่

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
        # ไม่ต้องให้ Forge เซฟไฟล์ซ้ำไว้ที่ PC3 เพราะ PC2 เซฟเอง + บันทึกลง PC4 อยู่แล้ว
        "do_not_save_samples": True,
        "do_not_save_grid": True,
    }

    if checkpoint:
        # สั่งสลับ checkpoint ก่อน generate — ถ้าเป็นตัวเดียวกับที่โหลดอยู่ Forge จะข้ามให้เอง
        payload["override_settings"] = {"sd_model_checkpoint": checkpoint}
        payload["override_settings_restore_afterwards"] = False

    try:
        resp = requests.post(
            f"{config.FORGE_API_URL}/sdapi/v1/txt2img",
            json=payload,
            auth=(config.FORGE_API_USER, config.FORGE_API_PASS),
            # (เชื่อมต่อ, รอผล) — แยกกันเพราะถ้าเครื่อง PC3 ดับ/ต่อไม่ติด ต้องรู้ผลใน 10 วิ
            # ไม่ใช่ค้างรอ 5 นาที แต่ถ้าต่อติดแล้วต้องรอนานได้ เพราะ generate ใช้เวลาจริง
            timeout=(10, 300),
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"เชื่อมต่อ AI Server ไม่ได้: {e}"}), 502

    result = resp.json()
    images = result.get("images") or []
    if not images:
        return jsonify({"error": "AI Server ไม่ได้ส่งภาพกลับมา"}), 502

    # ตอนขอ seed = -1 (สุ่ม) ค่า seed จริงจะอยู่ใน field "info" (JSON string) ต้อง parse เอา
    actual_seed = seed
    actual_checkpoint = checkpoint or None
    try:
        info = json.loads(result.get("info") or "{}")
        if info.get("seed") is not None:
            actual_seed = info["seed"]
        if not actual_checkpoint and info.get("sd_model_name"):
            actual_checkpoint = info["sd_model_name"]
    except (ValueError, TypeError):
        pass

    image_bytes = base64.b64decode(images[0])
    filename = f"{current_user.id}_{int(time.time() * 1000)}.png"
    relative_path = f"outputs/{filename}"
    # ส่งไฟล์ไปเก็บที่ PC4 ก่อน แล้วค่อยบันทึก record (ต่อ PC4 ไม่ติด → DatabaseError → ตอบ 503)
    put_file(relative_path, image_bytes)

    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO generations
           (user_id, prompt, negative_prompt, steps, cfg_scale, width, height,
            sampler, seed, checkpoint, image_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (current_user.id, prompt, negative_prompt, steps, cfg_scale, width, height,
         sampler, actual_seed, actual_checkpoint, relative_path,
         datetime.utcnow().isoformat()),
        "none",
    )

    return jsonify({
        "id": cursor.lastrowid,
        "image_url": media_url(relative_path),
        "prompt": prompt,
        "seed": actual_seed,
    })


# ============================================================
#  API: edit (Point Operation / Auto Contrast / Linear Filter / Non-linear Filter)
#  ทำบนเครื่องนี้ด้วย OpenCV — รับภาพได้ 2 ทาง:
#  อัปโหลดไฟล์เอง หรือเลือกจากภาพที่เคยสร้างไว้ (generation_id)
# ============================================================
@app.route("/api/edit", methods=["POST"])
@login_required
def api_edit():
    operation = request.form.get("operation", "")
    if operation not in image_ops.OPERATIONS:
        return jsonify({"error": "ไม่รู้จักฟังก์ชันแก้ไขภาพนี้"}), 400

    img = None
    source_label = None
    uploaded = request.files.get("image")
    generation_id = request.form.get("generation_id")

    if uploaded and uploaded.filename:
        raw_bytes = uploaded.read()
        if not raw_bytes:
            return jsonify({"error": "ไฟล์ภาพว่างเปล่าหรืออ่านไม่ได้"}), 400
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        source_label = f"อัปโหลด: {uploaded.filename}"
    elif generation_id:
        conn = get_db()
        gen_row = conn.execute(
            "SELECT * FROM generations WHERE id = ? AND user_id = ?",
            (generation_id, current_user.id),
        ).fetchone()
        if not gen_row:
            return jsonify({"error": "ไม่พบภาพที่เลือก หรือภาพนี้ไม่ใช่ของคุณ"}), 404
        raw_bytes = get_file(gen_row["image_path"])   # ภาพต้นฉบับอยู่ที่ PC4
        if raw_bytes:
            img = cv2.imdecode(np.frombuffer(raw_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        source_label = f"ภาพที่สร้างไว้: {gen_row['prompt'][:40]}"
    else:
        return jsonify({"error": "กรุณาเลือกภาพต้นฉบับ (อัปโหลด หรือ เลือกจากประวัติ)"}), 400

    if img is None:
        return jsonify({"error": "อ่านภาพไม่สำเร็จ ไฟล์อาจเสียหายหรือไม่ใช่ไฟล์รูปภาพ"}), 400

    # ประมวลผลภาพตามกลุ่ม/วิธีที่เลือก — รายละเอียดแต่ละอัลกอริทึมอยู่ใน image_ops.py
    try:
        result, params = image_ops.apply_operation(img, operation, request.form)
    except image_ops.EditParamError as e:
        return jsonify({"error": str(e)}), 400
    except cv2.error as e:
        return jsonify({"error": f"แก้ไขภาพไม่สำเร็จ: {e}"}), 400

    ok, png = cv2.imencode(".png", result)   # แปลงผลลัพธ์เป็นไฟล์ PNG ในหน่วยความจำ
    if not ok:
        return jsonify({"error": "แปลงผลลัพธ์เป็นไฟล์ PNG ไม่สำเร็จ"}), 500
    filename = f"edit_{current_user.id}_{uuid.uuid4().hex}.png"
    relative_path = f"outputs/edits/{filename}"
    put_file(relative_path, png.tobytes())   # เก็บผลลัพธ์ที่ PC4

    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO edits (user_id, source_label, operation, params, result_image, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (current_user.id, source_label, operation, json.dumps(params), relative_path,
         datetime.utcnow().isoformat()),
        "none",
    )

    return jsonify({
        "id": cursor.lastrowid,
        "image_url": media_url(relative_path),
        "operation": operation,
        "operation_label": image_ops.operation_label(operation, params),
        "params_summary": image_ops.params_summary(operation, params),
        "source_label": source_label,
    })


# ============================================================
#  API: health — เช็คว่าเครื่องนี้ต่อไปหา PC3 / PC4 ได้ไหม
#  เปิดหน้า http://172.20.56.128/api/health ดูได้เลยเวลาระบบมีปัญหา
# ============================================================
@app.route("/api/health")
def api_health():
    ai_status = {"status": "error"}
    try:
        r = requests.get(
            f"{config.FORGE_API_URL}/sdapi/v1/sd-models",
            auth=(config.FORGE_API_USER, config.FORGE_API_PASS),
            timeout=5,
        )
        r.raise_for_status()
        ai_status = {"status": "ok", "models": len(r.json())}
    except requests.exceptions.RequestException as e:
        ai_status = {"status": "error", "detail": str(e)}

    return jsonify({
        "backend": {"status": "ok", "role": "backend"},
        "database_pc4": db_health(),
        "ai_server_pc3": ai_status,
    })


if __name__ == "__main__":
    print(f"[BACKEND] Database Server : {config.DB_SERVER_URL}")
    print(f"[BACKEND] AI Server       : {config.FORGE_API_URL}")
    print(f"[BACKEND] เก็บไฟล์ภาพที่   : PC4 ({config.DB_SERVER_URL}/files/...)")
    # host="0.0.0.0" เพื่อให้เครื่อง Nginx (PC1) ยิงเข้ามาได้
    app.run(host="0.0.0.0", port=config.BACKEND_PORT, debug=True, threaded=True)
