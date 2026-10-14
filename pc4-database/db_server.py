"""
============================================================
 PC4 : DATABASE SERVER   (172.20.56.108 : 5100)
------------------------------------------------------------
 โจทย์คือ "แยกฐานข้อมูลออกไปอยู่คนละเครื่องกับ Backend"
 แต่ SQLite เป็นไฟล์ local ไม่มีโปรโตคอลเครือข่ายในตัว
 (แชร์ไฟล์ .db ผ่าน SMB/network drive = ไฟล์พังง่ายมาก ห้ามทำ)

 วิธีที่ถูกต้องคือ ครอบ SQLite ด้วย "บริการเล็ก ๆ" ตัวนี้
 แล้วให้เครื่อง Backend (172.20.56.107) คุยผ่าน HTTP บน LAN แทน
 -> ได้ Distributed System จริง: Backend ไม่แตะไฟล์ .db โดยตรงเลย

 เครื่องนี้เป็นเจ้าของไฟล์ database.db เพียงเครื่องเดียว
 และเป็นที่เก็บไฟล์ภาพทั้งหมดของระบบด้วย (โฟลเดอร์ storage/ ข้าง ๆ database.db)
 PC2 ส่งภาพมาเก็บ / ขอภาพไปแสดง / สั่งลบ ผ่าน /files/<path>
============================================================
"""
# ^ ข้อความข้างบนคือ docstring (คำอธิบายหัวไฟล์) Python ไม่รันมัน มีไว้ให้คนอ่านเข้าใจภาพรวม


# ------------------------------------------------------------
#  ส่วนที่ 1: IMPORT  (เรียกเครื่องมือที่ต้องใช้มาไว้ก่อน)
# ------------------------------------------------------------
import os
# os = เครื่องมือคุยกับระบบปฏิบัติการ ใช้จัดการไฟล์ โฟลเดอร์ และอ่าน environment variable

import sqlite3
# sqlite3 = เครื่องมือคุยกับฐานข้อมูล SQLite (มากับ Python อยู่แล้ว ไม่ต้องติดตั้งเพิ่ม)

import threading
# threading = เครื่องมือจัดการงานหลายสายพร้อมกัน ที่นี่ใช้สร้าง "กุญแจ" (Lock) กันเขียนฐานข้อมูลชนกัน

from flask import Flask, request, jsonify, send_file
# Flask     = ตัวสร้างเว็บเซิร์ฟเวอร์
# request   = ข้อมูลที่ผู้เรียกส่งมา เช่น header, body, IP ต้นทาง
# jsonify   = แปลงข้อมูล (dict) เป็นคำตอบแบบ JSON ส่งกลับ
# send_file = ส่งไฟล์ (เช่นรูปภาพ) กลับไปให้ผู้เรียก

from werkzeug.utils import safe_join
# safe_join = ต่อ path แบบปลอดภัย ถ้าพยายามใช้ ../ หลุดออกนอกโฟลเดอร์ จะคืนค่า None

from schema import init_db
# เอาฟังก์ชัน init_db จากไฟล์ schema.py (ไฟล์ของเราเอง) มาใช้ ทำหน้าที่สร้างตารางในฐานข้อมูล


# ------------------------------------------------------------
#  ส่วนที่ 2: ฟังก์ชันอ่านไฟล์ .env  (ของใหม่)
# ------------------------------------------------------------
def _load_env_file(path):#โหลดรหัสลับและค่าตั้งต้นจากไฟล์ .env ข้าง ๆ ไฟล์นี้
    # ประกาศฟังก์ชัน รับ path = ที่อยู่ของไฟล์ .env
    # ขึ้นต้นด้วย _ แปลว่า "ใช้ภายในไฟล์นี้เท่านั้น"
    """อ่านค่าจากไฟล์ .env ข้าง ๆ ไฟล์นี้ (environment variable ที่ตั้งไว้แล้วมาก่อนเสมอ)"""
    # ^ docstring อธิบายหน้าที่ของฟังก์ชัน
    if not os.path.isfile(path):
        # เช็กว่า "มีไฟล์ .env อยู่จริงไหม" ถ้าไม่มี...
        return
        # ...ก็จบฟังก์ชันเลย ไม่ error (ไม่มี .env จะไม่มามารถอ่านค่าตั้งต้นได้ แต่ก็ยังรันต่อไปได้)
    with open(path, encoding="utf-8-sig") as f: #"utf-8-sig" = อ่านภาษาไทยได้ และข้ามเครื่องหมายแปลก (BOM) ที่ Notepad ชอบใส่ต้นไฟล์
        # เปิดไฟล์ .env เพื่ออ่าน (as f = ตั้งชื่อเล่นให้ไฟล์ว่า f)
        # utf-8-sig = อ่านภาษาไทยได้ และข้ามเครื่องหมายแปลก (BOM) ที่ Notepad ชอบใส่ต้นไฟล์
        # with = พออ่านเสร็จจะปิดไฟล์ให้เองอัตโนมัติ
        for line in f: 
            # วนอ่านไฟล์ทีละบรรทัด แต่ละรอบเก็บบรรทัดไว้ในตัวแปร line
            line = line.strip()
            # ตัดช่องว่างและขึ้นบรรทัดใหม่ที่หัว-ท้ายบรรทัดทิ้ง
            if not line or line.startswith("#") or "=" not in line:
                # ถ้าบรรทัดว่าง / ขึ้นต้นด้วย # (คอมเมนต์) = ไม่มีเครื่องหมาย = อยู่เลย...
                continue
                # ...ข้ามบรรทัดนี้ไปอ่านบรรทัดถัดไป
            key, value = line.split("=", 1)
            # ("=", 1)=ใช้สำหรับ แบ่งข้อความออกเป็น 2 ส่วน โดยใช้เครื่องหมาย = เป็นตัวแบ่ง และแบ่งแค่ครั้งแรกครั้งเดียว
            # เช่น DB_TOKEN=abc  ->  key="DB_TOKEN", value="abc"
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
            # ใส่ค่าลงใน environment variable โดย:
            #   .strip()      ตัดช่องว่างรอบชื่อและค่า
            #   .strip("\"'") ตัดเครื่องหมายคำพูด " หรือ ' ที่ครอบค่าอยู่ออก
            #   setdefault    ใส่ให้เฉพาะตอนที่ "ยังไม่มีตัวแปรนี้" เท่านั้น
            #                 ดังนั้นค่าที่ตั้งไว้ใน PowerShell ($env:...) จะชนะค่าในไฟล์ .env เสมอ


# ============================================================
#  CONFIG  — แก้ได้ที่นี่ หรือ override ผ่าน environment variable
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 3: CONFIG  (ค่าตั้งต้นของระบบ)
# ------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# os.path = เครื่องมือจัดการ path ของไฟล์และโฟลเดอร์
# os.path.dirname = ตัดชื่อไฟล์ทิ้ง เหลือแค่โฟลเดอร์
# os.path.abspath = แปลงเป็น path เต็ม (เช่น D:\work_im\...\pc4-database)
# BASE_DIR = โฟลเดอร์ที่ไฟล์ db_server.py วางอยู่ (เช่น D:\work_im\...\pc4-database)
# หาโฟลเดอร์ที่ไฟล์ db_server.py วางอยู่ แล้วแปลงเป็น path เต็ม
#   __file__  = ที่อยู่ของไฟล์นี้
#   dirname   = ตัดชื่อไฟล์ทิ้ง เหลือแค่โฟลเดอร์
#   abspath   = ทำให้เป็น path เต็ม (เช่น D:\work_im\...\pc4-database)
# ใช้เป็น "จุดอ้างอิง" ให้ไฟล์อื่นๆ ย้ายโปรเจกต์ไปไหนก็ยังหาเจอ

_load_env_file(os.path.join(BASE_DIR, ".env"))
#(os.path.join = ต่อ path แบบปลอดภัย) เรียกฟังก์ชันอ่านไฟล์ .env ที่อยู่ข้าง ๆ ไฟล์นี้
# เรียกฟังก์ชันอ่านไฟล์ .env ที่อยู่ในโฟลเดอร์เดียวกับไฟล์นี้
# ต้องเรียกตรงนี้ "ก่อน" บรรทัด os.environ.get ข้างล่างทั้งหมด ไม่งั้นค่าจาก .env จะไม่ถูกใช้

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database.db"))
#  os.environ.get = อ่าน environment variable (ค่าที่ตั้งไว้แล้วมาก่อน)
# ที่อยู่ไฟล์ฐานข้อมูล
# ถ้ามีตัวแปร DB_PATH ตั้งไว้ -> ใช้ค่านั้น  ถ้าไม่มี -> ใช้ database.db ข้างๆ ไฟล์นี้

DB_PORT = int(os.environ.get("DB_PORT", "5100"))
# DB_PORT = int(...) แปลงข้อความเป็นตัวเลข เพราะ environment variable เป็นข้อความเสมอ
# พอร์ตที่เซิร์ฟเวอร์เปิดรับ ค่าเริ่มต้น 5100
# int(...) แปลงข้อความเป็นตัวเลข เพราะ environment variable เป็นข้อความเสมอ

# ที่เก็บไฟล์ภาพ (ภาพที่สร้าง outputs/ และภาพที่แก้ไข outputs/edits/)
# path ในฐานข้อมูลเป็นแบบ outputs/xxx.png ซึ่งนับจากโฟลเดอร์นี้
STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "storage"))
# STORAGE_DIR = os.environ.get= อ่านค่าตัวแปร STORAGE_DIR จาก environment variable ถ้าไม่มีให้ใช้ค่า default ข้างหลัง
# โฟลเดอร์เก็บรูปภาพจริง ค่าเริ่มต้นคือโฟลเดอร์ storage ข้างๆ ไฟล์นี้

# โทเคนลับ ต้องตรงกับค่า DB_TOKEN ใน pc2-backend/.env — ไม่มีค่า default ต้องตั้งเองใน .env
DB_TOKEN = os.environ.get("DB_TOKEN", "")
# DB_TOKEN = os.environ.get = อ่านค่าตัวแปร DB_TOKEN จาก environment variable ถ้าไม่มีให้เป็นข้อความว่าง
# รหัสลับที่ PC2 ต้องแนบมาทุกครั้ง ค่าสำรองเป็นข้อความว่าง (ไม่มีรหัสฝังในโค้ดแล้ว)
if not DB_TOKEN:
    # ถ้าไม่ได้ตั้ง DB_TOKEN เลย (ว่างเปล่า)...
    raise SystemExit(
        # raise SystemExit = สั่งปิดโปรแกรมทันที (exit) พร้อมแสดงข้อความด้านล่าง
        # เหตุผล: ไม่มีรหัส = ใครก็เข้าได้ จึงไม่ยอมให้เซิร์ฟเวอร์ขึ้น
        "[X] ยังไม่ได้ตั้งค่า DB_TOKEN — คัดลอก pc4-database/.env.example เป็น .env แล้วใส่ค่าให้ครบ"
    )

# อนุญาตเฉพาะ IP ของเครื่อง Backend (และตัวเอง) — ใส่ set() ว่างเพื่อปิดการตรวจ IP
ALLOWED_CLIENT_IPS = {"10.192.0.195", "127.0.0.1", "::1"}
# รายชื่อ IP ที่ให้เข้าได้:
#   10.192.0.195 = เครื่อง PC2 (Backend)
#   127.0.0.1    = ตัวเครื่องนี้เอง (IPv4)
#   ::1          = ตัวเครื่องนี้เอง (IPv6)

app = Flask(__name__)
# สร้างแอป Flask ตัวหลัก (เว็บเซิร์ฟเวอร์ของเรา) ทุก @app.route ข้างล่างจะผูกกับตัวนี้

# SQLite เขียนพร้อมกันหลาย thread ไม่ได้ ใช้ lock กันไว้ชั้นหนึ่ง
_write_lock = threading.Lock()
# สร้าง "กุญแจ" 1 ดอก ใครจะเขียนฐานข้อมูลต้องถือกุญแจก่อน คนอื่นต้องรอจนกว่าจะคืน
# ป้องกันสองคำขอเขียนชนกันจนฐานข้อมูลล็อกหรือพัง


# ------------------------------------------------------------
#  ส่วนที่ 4: get_conn()  (เปิดการเชื่อมต่อฐานข้อมูล)
# ------------------------------------------------------------
def get_conn():
    # ฟังก์ชันนี้ถูกเรียกทุกครั้งที่ต้องการคุยกับฐานข้อมูล (เปิดใหม่ทุก request)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    # sqlite3.connect = เปิดการเชื่อมต่อฐานข้อมูล SQLite
    # เปิดไฟล์ฐานข้อมูล (ถ้ายังไม่มีไฟล์ SQLite สร้างให้เอง)
    # timeout=30 = ถ้าไฟล์ถูกล็อกอยู่ ให้รอสูงสุด 30 วินาทีก่อนขึ้น error
    conn.row_factory = sqlite3.Row
    # conn.row_factory = ให้แถวผลลัพธ์เรียกด้วยชื่อคอลัมน์ได้ (row["name"]) และแปลงเป็น dict ได้ (dict(row))
    # ใช้ทั้งใน schema.py และตอนส่ง JSON กลับ
    # ใช้โหมด DELETE (ค่าปกติของ SQLite) แทน WAL
    # เดิมใช้ WAL -> การลบ/เพิ่มข้อมูลจะไปค้างอยู่ในไฟล์ database.db-wal ก่อน
    # ถ้าเปิด database.db ดูด้วยโปรแกรมอื่นค้างไว้ ไฟล์หลักจะยังเห็นข้อมูลเก่า (เหมือนลบไม่ออก)
    # โหมด DELETE เขียนลง database.db ตรง ๆ ทุกครั้งที่ commit — เห็นผลทันที
    conn.execute("PRAGMA journal_mode=DELETE")
    # conn.execute = ส่งคำสั่ง SQL ไปให้ SQLite ทำงาน
    # ("PRAGMA journal_mode=DELETE") = สั่ง SQLite ให้ใช้โหมด DELETE แทน WAL
    # ตั้งวิธีกันข้อมูลพัง: เขียนลงไฟล์หลักตรงๆ ตอน commit เปิดดูด้วย DB Browser เห็นข้อมูลล่าสุดทันที
    conn.execute("PRAGMA foreign_keys=ON")
    # ("PRAGMA foreign_keys=ON") = เปิดระบบตรวจสอบความถูกต้องของข้อมูลอ้างอิง (foreign key)
    # เช่น ห้ามเพิ่มภาพของผู้ใช้ที่ไม่มีอยู่จริง
    # SQLite ปิดระบบนี้ไว้เป็นค่าเริ่มต้น จึงต้องสั่งเปิดทุกครั้งที่เชื่อมต่อ
    return conn
    # ส่งการเชื่อมต่อกลับไปให้ผู้เรียกใช้งานต่อ


# ============================================================
#  AUTH: ตรวจโทเคน + IP ต้นทาง ก่อนทุก request
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 5: ด่านตรวจสิทธิ์ (ยามหน้าประตู)
# ------------------------------------------------------------
@app.before_request
# ตัวตกแต่ง: บอก Flask ว่า "ให้รันฟังก์ชันข้างล่างนี้ก่อนทุก request" ก่อนจะไปถึง route จริง
def check_client(): #check_client = ฟังก์ชันตรวจสอบสิทธิ์ผู้เรียก (IP + token)
    if request.path == "/health":
        # ถ้าผู้เรียกมาที่ /health...
        return None
        # ...ปล่อยผ่านเลยไม่ต้องตรวจอะไร (None = ให้ทำงานต่อได้)

    if ALLOWED_CLIENT_IPS and request.remote_addr not in ALLOWED_CLIENT_IPS:
        # ถ้ามีรายชื่อ IP ที่อนุญาตไว้ และ IP ของคนเรียกไม่อยู่ในรายชื่อนั้น...
        # (ถ้ารายชื่อเป็น set() ว่าง ถือว่าปิดการตรวจ IP เงื่อนไขนี้จะไม่ทำงาน)
        return jsonify({"error": f"IP {request.remote_addr} ไม่ได้รับอนุญาตให้เข้าถึงฐานข้อมูล"}), 403
        # ...ตอบ error พร้อมรหัส 403 (Forbidden = ห้ามเข้า) แล้วหยุดทันที

    if request.headers.get("X-DB-Token") != DB_TOKEN:
        # ถ้า header ชื่อ X-DB-Token ไม่มี หรือค่าไม่ตรงกับรหัสลับของเรา...
        return jsonify({"error": "DB token ไม่ถูกต้อง"}), 401
        # ...ตอบ error รหัส 401 (Unauthorized = ยังไม่ยืนยันตัวตน) แล้วหยุดทันที

    return None
    # ผ่านทั้งสองด่านแล้ว ปล่อยให้ request ไปทำงานต่อที่ route ที่ขอ


# ============================================================
#  API: /sql  — รัน SQL หนึ่งคำสั่ง
#  body: {"sql": "...", "params": [...], "fetch": "all" | "one" | "none"}
#  resp: {"rows": [...], "lastrowid": int, "rowcount": int}
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 6: POST /sql  (รัน SQL ทีละ 1 คำสั่ง)
# ------------------------------------------------------------
@app.route("/sql", methods=["POST"])
# ผูกฟังก์ชันข้างล่างกับที่อยู่ /sql และรับเฉพาะวิธี POST (วิธีส่งข้อมูลเข้ามา)
def run_sql():
    data = request.get_json(force=True, silent=True) or {}
    # อ่านข้อมูลที่ส่งมาเป็น JSON
    #   force=True  = ไม่สนว่าผู้ส่งบอกชนิดข้อมูลว่าอะไร ลองอ่านเป็น JSON เลย
    #   silent=True = ถ้าอ่านไม่ได้ ไม่ต้อง error
    #   or {}       = ถ้าได้ค่าว่าง ให้ใช้ dict ว่างแทน
    sql = (data.get("sql") or "").strip()
    # ดึงข้อความคำสั่ง SQL ออกมา ตัดช่องว่างหัวท้าย ถ้าไม่มีให้เป็นข้อความว่าง
    params = data.get("params") or []
    # ดึงค่าที่จะไปแทนที่เครื่องหมาย ? ใน SQL (วิธีนี้กัน SQL injection) ถ้าไม่มีให้เป็น list ว่าง
    fetch = data.get("fetch", "all")
    # โหมดดึงผลลัพธ์: "all" = ทุกแถว, "one" = แถวเดียว, "none" = ไม่ดึง ค่าเริ่มต้นคือ all

    if not sql:
        # ถ้าไม่มีคำสั่ง SQL ส่งมาเลย...
        return jsonify({"error": "ไม่ได้ส่งคำสั่ง SQL มา"}), 400
        # ให้ตอบ 400 (Bad Request = คำขอไม่ถูกต้อง) แล้วจบ

    try:
        # เริ่มบล็อกดักจับ error ของ SQLite (เช่น SQL ผิด ชื่อซ้ำ ตารางไม่มี)
        with _write_lock:
            # ขอกุญแจก่อน ถ้ามีคนถืออยู่ต้องรอ พอออกจากบล็อกนี้จะคืนกุญแจให้เองอัตโนมัติ
            conn = get_conn()
            # เปิดการเชื่อมต่อฐานข้อมูลใหม่
            try:
                # try ชั้นใน: เพื่อให้แน่ใจว่าปิดการเชื่อมต่อเสมอ (ดู finally ด้านล่าง)
                cur = conn.execute(sql, tuple(params))
                # สั่งรัน SQL พร้อมแทนค่า params (แปลง list เป็น tuple ตามที่ SQLite ต้องการ)
                # cur (cursor) = ตัวถือผลลัพธ์ของคำสั่งนี้

                rows = []
                # เตรียมที่เก็บผลลัพธ์ ค่าเริ่มต้นว่างเปล่า
                if fetch == "all":
                    # ถ้าขอทุกแถว...
                    rows = [dict(r) for r in cur.fetchall()]
                    # ...ดึงทุกแถว แล้วแปลงแต่ละแถวเป็น dict เพื่อส่งเป็น JSON ได้
                elif fetch == "one":
                    # ถ้าขอแถวเดียว...
                    row = cur.fetchone()
                    # ...ดึงแถวแรกแถวเดียว (ไม่มีก็ได้ None)
                    rows = [dict(row)] if row else []
                    # ถ้ามีแถว ใส่ลง list; ถ้าไม่มีให้ list ว่าง

                conn.commit()   # autocommit ทุกคำสั่ง — ฝั่ง Backend จึงไม่ต้อง commit เอง
                # ยืนยันการเปลี่ยนแปลงลงไฟล์จริง (ถ้าไม่ commit ข้อมูลที่แก้จะหายตอนปิดการเชื่อมต่อ)

                # แสดง log คำสั่งที่แก้ข้อมูลบนหน้าต่างของเครื่องนี้ ไว้ยืนยันว่าลบ/เพิ่มสำเร็จจริง
                verb = sql.split(None, 1)[0].upper()
                # เอาคำแรกของ SQL มาทำเป็นตัวพิมพ์ใหญ่ เช่น "insert ..." -> "INSERT"
                if verb in ("INSERT", "UPDATE", "DELETE"):
                    # ถ้าเป็นคำสั่งที่แก้ข้อมูล (เพิ่ม/แก้/ลบ) ถึงจะพิมพ์ log
                    # แสดง params เฉพาะคำสั่ง DELETE (กันรหัสผ่านที่ hash แล้วโผล่บนจอตอนสมัครสมาชิก)
                    extra = f"  params={params}" if verb == "DELETE" else ""
                    # extra = ข้อความต่อท้าย log ถ้าเป็น DELETE ให้ต่อท้ายด้วยค่า params ถ้าไม่ใช่ปล่อยว่าง
                    
                    print(f"[DB] {' '.join(sql.split())}{extra}  -> {cur.rowcount} แถว", flush=True)
                    # พิมพ์ log บนหน้าจอเซิร์ฟเวอร์: SQL (ยุบช่องว่างให้อยู่บรรทัดเดียว) + จำนวนแถวที่ถูกแก้
                    # flush=True = ให้ข้อความขึ้นจอทันที ไม่รอ
                result = {
                    # ประกอบคำตอบที่จะส่งกลับไปให้ PC2
                    "rows": rows,
                    # ข้อมูลที่ดึงมา (ของ SELECT)
                    "lastrowid": cur.lastrowid,
                    # เลข id ของแถวที่เพิ่ง INSERT ล่าสุด
                    "rowcount": cur.rowcount,
                    # จำนวนแถวที่ถูกแก้/ลบ (ของ SELECT จะเป็น -1)
                }
            finally:
                # finally = ทำเสมอ ไม่ว่าข้างบนสำเร็จหรือพัง
                conn.close()
                # ปิดการเชื่อมต่อ คืนทรัพยากร
    except sqlite3.Error as e:
        # as e = เก็บ error ของ SQLite ไว้ในตัวแปร e
        # ถ้ามี error ของ SQLite เกิดขึ้นที่ไหนใน try ด้านบน จะมาที่นี่ (e = ตัว error นั้น)
        return jsonify({"error": f"SQL error: {e}"}), 400
        # ตอบ 400 พร้อมข้อความ error ให้ PC2 รู้สาเหตุ เช่น "UNIQUE constraint failed: users.username"

    return jsonify(result)
    # ทุกอย่างสำเร็จ ส่งผลลัพธ์กลับเป็น JSON


# ============================================================
#  API: /sql/batch — รันหลายคำสั่งใน transaction เดียว (atomic)
#  body: {"statements": [{"sql": "...", "params": [...]}, ...]}
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 7: POST /sql/batch  (หลายคำสั่ง ทำสำเร็จทั้งหมดหรือไม่ทำเลย)
# ------------------------------------------------------------
@app.route("/sql/batch", methods=["POST"])
# ผูกกับที่อยู่ /sql/batch รับเฉพาะ POST
def run_batch(): #run_batch = ฟังก์ชันรันหลายคำสั่ง SQL ใน transaction เดียว
    data = request.get_json(force=True, silent=True) or {}
    # อ่านข้อมูล JSON ที่ส่งมา (เหมือนด้านบน)
    statements = data.get("statements") or []
    # statements เป็น list ว่าง = ไม่มีคำสั่ง SQL ส่งมาเลย...
    # ดึงรายการคำสั่งทั้งหมด แต่ละอันหน้าตา {"sql": "...", "params": [...]}
    if not statements:
        # statements เป็น list ว่าง = ไม่มีคำสั่ง SQL ส่งมาเลย...
        # ถ้าไม่มีคำสั่งสักอัน...
        return jsonify({"error": "ไม่ได้ส่งคำสั่ง SQL มา"}), 400
        # ...ตอบ 400 แล้วจบ

    lastrowids = [] #lastrowids = เตรียม list เก็บเลข id ล่าสุดของแต่ละคำสั่ง
    
    try:
        # try ชั้นนอก: ดัก error แล้วแปลงเป็นคำตอบ JSON
        with _write_lock:
            # ขอกุญแจกันเขียนชนกัน
            conn = get_conn()
            # เปิดการเชื่อมต่อ
            try:
                # try ชั้นใน: จัดการเรื่องข้อมูล (rollback) และปิดการเชื่อมต่อ
                for st in statements:
                    # วนทีละคำสั่ง (st ย่อมาจาก statement)
                    cur = conn.execute(st.get("sql", ""), tuple(st.get("params") or []))
                    # รันคำสั่งนั้น พร้อมแทนค่า params (ตอนนี้ยังไม่ commit)
                    lastrowids.append(cur.lastrowid)
                    # เก็บเลข id ล่าสุดของคำสั่งนี้ไว้ก่อนที่ cur จะถูกทับในรอบถัดไป
                conn.commit()
                # รันครบทุกคำสั่งแล้วค่อย commit ทีเดียว = ทั้งหมดสำเร็จพร้อมกัน
            except sqlite3.Error as e:
                # ถ้าคำสั่งใดคำสั่งหนึ่งพัง...
                conn.rollback()
                # ...ย้อนทุกอย่างที่ทำมากลับเหมือนไม่เคยทำ (ข้อมูลไม่ค้างครึ่งๆ กลางๆ)
                raise
                # โยน error ตัวเดิมออกไปต่อ ให้ except ชั้นนอกจับไปตอบ PC2
            finally:
                conn.close()
                # ปิดการเชื่อมต่อเสมอ ไม่ว่าสำเร็จหรือพัง
    except sqlite3.Error as e:
        # except ชั้นนอก: รับ error ที่ถูกโยนต่อมา
        return jsonify({"error": f"SQL error: {e}"}), 400
        # ตอบ 400 พร้อมข้อความ error

    return jsonify({"lastrowids": lastrowids})
    # สำเร็จทั้งหมด ส่ง list เลข id กลับไป


# ============================================================
#  API: /files/<path> — ที่เก็บไฟล์ภาพ (อยู่บนเครื่องนี้ ข้างไฟล์ database.db)
#    PUT    = PC2 ส่งไฟล์มาเก็บ (body เป็น byte ของไฟล์)
#    GET    = PC2 ขอไฟล์ไปส่งต่อให้ browser
#    DELETE = PC2 สั่งลบไฟล์
#  ผ่าน check_client() เหมือน /sql (ต้องมาจาก IP ของ PC2 + มี token)
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 8: /files/...  (ที่เก็บไฟล์ภาพ)
# ------------------------------------------------------------
def _file_path(rel_path):
    # ฟังก์ชันช่วยแปลง path จาก URL (เช่น "outputs/a.png") เป็น path จริงบนดิสก์
    """แปลง path จาก URL เป็น path จริงใต้ STORAGE_DIR
    รับเฉพาะใต้ outputs/ และกัน ../ ไม่ให้หลุดออกนอกโฟลเดอร์ (เช่นไปทับ database.db)"""
    if not rel_path.startswith("outputs/"):
        # ถ้า path ไม่ได้ขึ้นต้นด้วย "outputs/"...
        return None
        # ...ปฏิเสธ (คืน None) เช่น พยายามเข้าถึง database.db จะไม่ผ่านตรงนี้
    return safe_join(STORAGE_DIR, rel_path)
    # ต่อ STORAGE_DIR กับ rel_path แบบปลอดภัย ถ้ามี ../ พยายามหลุดออกนอกโฟลเดอร์ จะได้ None


@app.route("/files/<path:rel_path>", methods=["PUT"])
# ที่อยู่ /files/อะไรก็ได้ (รวมเครื่องหมาย / ได้) วิธี PUT = อัปโหลดไฟล์
# ค่าที่อยู่หลัง /files/ จะถูกส่งเข้าฟังก์ชันในชื่อ rel_path
def put_file(rel_path): #put_file(rel_path) = ฟังก์ชันรับไฟล์ภาพจาก PC2 แล้วเก็บลงโฟลเดอร์ storage/ ข้างๆ database.db
    full = _file_path(rel_path)
    # แปลงเป็น path จริงบนดิสก์ (ผ่านด่านความปลอดภัยด้วย)
    if full is None:
        # ถ้า path ไม่ปลอดภัยหรือไม่อยู่ในที่ที่อนุญาต...
        return jsonify({"error": "path ของไฟล์ไม่ถูกต้อง"}), 400
        # ...ตอบ 400 แล้วจบ ไม่แตะไฟล์ใดๆ
    data = request.get_data()
    # อ่านข้อมูลที่ส่งมาทั้งก้อนเป็น bytes (ก็คือตัวไฟล์ภาพ)
    if not data:
        # ถ้าไม่มีข้อมูลส่งมาเลย...
        return jsonify({"error": "ไม่ได้ส่งไฟล์มา"}), 400
        # ...ตอบ 400

    os.makedirs(os.path.dirname(full), exist_ok=True)
    # os.path.dirname(full) = path ของโฟลเดอร์แม่ของไฟล์ที่จะเก็บ (เช่น storage/outputs/2024/06)
    # makedirs = สร้างโฟลเดอร์หลายชั้นพร้อมกัน (เช่น storage/outputs/2024/06)
    # exist_ok=True = ถ้ามีอยู่แล้วไม่ต้อง error
    with open(full, "wb") as f:
        # เปิดไฟล์ปลายทางเพื่อ "เขียน" แบบ binary
        #   w = เขียน (ถ้ามีไฟล์ชื่อเดิมอยู่จะถูกทับ)
        #   b = binary เพราะรูปภาพไม่ใช่ตัวอักษร
        #   as f = ตั้งชื่อเล่นให้ไฟล์ที่เปิดว่า f
        f.write(data)
        # เขียนข้อมูลภาพลงไฟล์ ออกจาก with แล้วไฟล์ถูกปิดให้เอง
    print(f"[FILE] เก็บ {rel_path}  ({len(data) // 1024} KB)", flush=True)
    # พิมพ์ log ว่าเก็บไฟล์ไหน ขนาดกี่ KB (len(data) คือจำนวน byte หาร 1024 ปัดลง)
    return jsonify({"path": rel_path, "size": len(data)})
    # ตอบกลับ path และขนาดไฟล์ (เป็น byte) ให้ PC2 รู้ว่าเก็บสำเร็จ


@app.route("/files/<path:rel_path>", methods=["GET"])
# วิธี GET = ขอดาวน์โหลดไฟล์
def get_file(rel_path):
    full = _file_path(rel_path)
    # แปลงเป็น path จริงบนดิสก์
    if full is None or not os.path.isfile(full):
        # ถ้า path ไม่ปลอดภัย หรือ "ไม่มีไฟล์นี้อยู่จริง"...
        return jsonify({"error": "ไม่พบไฟล์"}), 404
        # ...ตอบ 404 (Not Found = ไม่พบ)
    return send_file(full)
    # ส่งไฟล์กลับไปให้ผู้เรียก (Flask เดาชนิดไฟล์จากนามสกุลให้เอง เช่น .png)


@app.route("/files/<path:rel_path>", methods=["DELETE"])
# วิธี DELETE = สั่งลบไฟล์
def delete_file(rel_path): #delete_file(rel_path) = ฟังก์ชันลบไฟล์ภาพที่ PC2 สั่ง
    full = _file_path(rel_path)
    # แปลงเป็น path จริงบนดิสก์
    if full is None:
        # ถ้า path ไม่ปลอดภัย...
        return jsonify({"error": "path ของไฟล์ไม่ถูกต้อง"}), 400
        # ...ตอบ 400 ไม่ลบอะไร (กันการสั่งลบไฟล์สำคัญ เช่น database.db)
    if not os.path.isfile(full):
        # ถ้าไม่มีไฟล์ให้ลบอยู่แล้ว...
        return jsonify({"deleted": False})
        # ...ตอบ deleted: False (ไม่ถือเป็น error เพราะผลที่ต้องการคือ "ไฟล์หาย" ซึ่งเป็นจริงอยู่แล้ว)
    os.remove(full)
    # ลบไฟล์จริงออกจากดิสก์ถาวร (ไม่ผ่านถังขยะ กู้คืนไม่ได้)
    print(f"[FILE] ลบ {rel_path}", flush=True)
    # พิมพ์ log ว่าลบไฟล์ไหนไป
    return jsonify({"deleted": True})
    # ตอบ deleted: True ให้ PC2 รู้ว่าลบสำเร็จ


# ============================================================
#  API: /health — ให้เครื่องอื่นเช็คว่า DB Server ยังมีชีวิต
# ============================================================
# ------------------------------------------------------------
#  ส่วนที่ 9: GET /health  (เช็กสถานะเซิร์ฟเวอร์)
# ------------------------------------------------------------
@app.route("/health")
# ที่อยู่ /health ไม่ระบุ methods = รับ GET อย่างเดียว
# และข้ามการตรวจ IP/token (ดูในส่วนที่ 5) ใครก็เปิดเช็กได้
def health():
    try:
        # ดัก error ของ SQLite เช่น ไม่มีตาราง ไฟล์เสีย
        conn = get_conn()
        # เปิดการเชื่อมต่อ
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        # นับจำนวนแถวในตาราง users (AS c = ตั้งชื่อคอลัมน์ผลลัพธ์ว่า c แล้วดึงด้วย ["c"])
        gens = conn.execute("SELECT COUNT(*) AS c FROM generations").fetchone()["c"]
        # นับจำนวนภาพที่เจน
        edits = conn.execute("SELECT COUNT(*) AS c FROM edits").fetchone()["c"]
        # นับจำนวนภาพที่แก้ไข
        conn.close()
        # ปิดการเชื่อมต่อ
    except sqlite3.Error as e:
        # ถ้านับไม่ได้เพราะ SQLite มีปัญหา...
        return jsonify({"status": "error", "detail": str(e)}), 500
        # ...ตอบ 500 (Server Error = ความผิดพลาดฝั่งเซิร์ฟเวอร์) พร้อมรายละเอียด

    return jsonify({
        # ถ้าไม่มี error ส่งสถานะกลับเป็น JSON
        "status": "ok",
        # บอกว่าทุกอย่างปกติ
        "role": "database",
        # บอกบทบาทของเครื่องนี้ว่าเป็นเครื่องฐานข้อมูล
        "db_path": DB_PATH,
        # ที่อยู่ไฟล์ฐานข้อมูลที่ใช้จริง (ไว้เช็กว่าเปิดถูกไฟล์)
        "storage": STORAGE_DIR,
        # ที่อยู่โฟลเดอร์เก็บภาพ
        "users": users,
        # จำนวนผู้ใช้
        "generations": gens,
        # จำนวนภาพที่เจน
        "edits": edits,
        # จำนวนภาพที่แก้ไข
    })


# ------------------------------------------------------------
#  ส่วนที่ 10: จุดเริ่มรันโปรแกรม
# ------------------------------------------------------------
if __name__ == "__main__":
    # เงื่อนไขนี้จริงเฉพาะตอนสั่งรันไฟล์นี้ตรงๆ (python db_server.py)
    # ถ้าไฟล์นี้ถูก import จากไฟล์อื่น โค้ดข้างล่างจะไม่ทำงาน
    conn = get_conn()
    # เปิดการเชื่อมต่อฐานข้อมูล
    init_db(conn)
    # เรียกฟังก์ชันจาก schema.py เพื่อสร้างตารางและ migrate ถ้ายังไม่มี (ข้อมูลเดิมไม่หาย)
    conn.close()
    # ปิดการเชื่อมต่อ ใช้เสร็จแล้ว (request ต่อไปจะเปิดใหม่เอง)
    os.makedirs(os.path.join(STORAGE_DIR, "outputs", "edits"), exist_ok=True)
    # makedirs = สร้างโฟลเดอร์หลายชั้นพร้อมกัน (เช่น storage/outputs/edits)
    # สร้างโฟลเดอร์ storage/outputs/edits ไว้ล่วงหน้า (สร้างโฟลเดอร์แม่ให้ทุกชั้น ถ้ามีอยู่แล้วไม่ error)
    print(f"[DB SERVER] ไฟล์ฐานข้อมูล : {DB_PATH}")
    # แสดง path ฐานข้อมูลที่ใช้จริง
    print(f"[DB SERVER] ที่เก็บไฟล์ภาพ : {STORAGE_DIR}")
    # แสดง path โฟลเดอร์เก็บภาพ
    print(f"[DB SERVER] เปิดรับ       : http://0.0.0.0:{DB_PORT}")
    # แสดงที่อยู่ที่เปิดรับ (0.0.0.0 = รับจากทุกการ์ดเครือข่าย ไม่ใช่แค่เครื่องตัวเอง)
    print(f"[DB SERVER] อนุญาต IP     : {ALLOWED_CLIENT_IPS or 'ทุก IP'}")
    # แสดงรายการ IP ที่อนุญาต ถ้าเป็น set() ว่างจะแสดงว่า 'ทุก IP'
    # threaded=True เพื่อรับหลาย request พร้อมกันได้ (มี _write_lock กันชนกันอยู่แล้ว)
    app.run(host="0.0.0.0", port=DB_PORT, threaded=True)
    # สตาร์ทเว็บเซิร์ฟเวอร์ Flask แล้วรอรับ request ค้างไว้จนกด Ctrl+C
    #   host="0.0.0.0" = รับการเชื่อมต่อจากทุกเครื่องในเครือข่าย
    #   port=DB_PORT   = ใช้พอร์ตที่ตั้งไว้ (ค่าเริ่มต้น 5100)
    #   threaded=True  = ให้แต่ละ request ทำงานคนละ thread รับหลายคนพร้อมกันได้