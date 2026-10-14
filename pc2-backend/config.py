"""
============================================================
 PC2 : BACKEND (Flask)  — config.py
 รวมค่าที่ต้องแก้เวลาย้ายเครื่อง / เปลี่ยน IP ไว้ที่เดียว
============================================================
"""
import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ------------------------------------------------------------
#  ค่าลับ (รหัสผ่าน / token / secret key) ไม่เขียนไว้ในโค้ดแล้ว
#  ให้ใส่ในไฟล์ .env ข้าง ๆ ไฟล์นี้ (คัดลอกจาก .env.example) — .env ถูก gitignore ไว้
#  ถ้าตั้ง environment variable ชื่อเดียวกันไว้ จะใช้ค่านั้นแทนค่าใน .env
# ------------------------------------------------------------
def _load_env_file(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_file(os.path.join(BASE_DIR, ".env"))

# ------------------------------------------------------------
#  เครื่อง AI Server (PC3) — Stability Matrix / Forge
# ------------------------------------------------------------
FORGE_API_URL = "http://172.20.56.108:7860"  # IP จริงของเครื่อง AI (laptop-8K067BK3) บนเน็ต CDTI_STUDENT
                                             # หมายเหตุ: เน็ตนี้แจก IP แบบ DHCP ถ้าต่อใหม่แล้ว IP เปลี่ยน ต้องแก้บรรทัดนี้ด้วย
FORGE_API_USER = os.environ.get("FORGE_API_USER", "")   # ต้องตรงกับ --api-auth ใน Launch Options
FORGE_API_PASS = os.environ.get("FORGE_API_PASS", "")
# ปล่อยว่างทั้งคู่ได้ ถ้า Forge เปิดไว้โดยไม่ตั้ง --api-auth
FORGE_AUTH = (FORGE_API_USER, FORGE_API_PASS) if FORGE_API_USER else None

# ------------------------------------------------------------
#  เครื่อง Database (PC4)
# ------------------------------------------------------------
DB_SERVER_URL = "http://172.20.56.113:5100"   # <— แก้เป็น IP จริงของเครื่อง DB
DB_TOKEN = os.environ.get("DB_TOKEN", "")     # ต้องตรงกับ DB_TOKEN ใน pc4-database/.env
if not DB_TOKEN:
    raise SystemExit(
        "[X] ยังไม่ได้ตั้งค่า DB_TOKEN — คัดลอก pc2-backend/.env.example เป็น .env แล้วใส่ค่าให้ครบ"
    )
DB_TIMEOUT = 15                              # วินาที

# ------------------------------------------------------------
#  เครื่อง Frontend / Nginx (PC1)
#  ปกติ browser จะยิงผ่าน Nginx ที่ 172.20.56.128 ทำให้เป็น same-origin
#  ไม่ต้องใช้ CORS เลย — รายการนี้เผื่อกรณีเปิดไฟล์ HTML ตรง ๆ ตอนพัฒนา
# ------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://172.20.56.117",
    "http://172.20.56.117:80",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

# ------------------------------------------------------------
#  Flask
# ------------------------------------------------------------
# ใช้เซ็น session cookie — ถ้าไม่ได้ตั้งไว้ใน .env จะสุ่มใหม่ทุกครั้งที่เปิดโปรแกรม
# (ใช้งานได้ แต่ผู้ใช้ทุกคนต้องล็อกอินใหม่หลัง restart)
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
BACKEND_PORT = 5000
# เปิด debugger/auto-reload ของ Flask เฉพาะตอนพัฒนา — ห้ามเปิดตอนใช้งานจริงบน LAN
DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")

# ไฟล์ log ของ Backend — logs/app.log (หมุนไฟล์เองเมื่อถึง ~1MB เก็บย้อนหลัง 3 ไฟล์)
LOG_DIR = os.path.join(BASE_DIR, "logs")

# กันสแปม /api/generate: ผู้ใช้แต่ละคนต้องรอกี่วินาทีก่อนสั่งสร้างภาพครั้งถัดไป (0 = ไม่จำกัด)
GENERATE_COOLDOWN_SECONDS = float(os.environ.get("GENERATE_COOLDOWN_SECONDS", "3"))

# ------------------------------------------------------------
#  ที่เก็บไฟล์ภาพ — ย้ายไปอยู่ที่ PC4 แล้ว (โฟลเดอร์ storage/ ข้าง database.db)
#  เครื่องนี้ส่ง/ขอ/ลบไฟล์ผ่าน db_client.put_file / get_file / delete_file
#  ใช้ DB_SERVER_URL และ DB_TOKEN ด้านบนตัวเดียวกัน ไม่ต้องตั้งค่าเพิ่ม
# ------------------------------------------------------------

# ------------------------------------------------------------
#  checkpoint ที่อนุญาตให้เลือกในหน้าเว็บ (เหมือนเดิม)
# ------------------------------------------------------------
ALLOWED_CHECKPOINTS = [
    {"match": "realSimpleAnime", "sampler": "Euler a", "width": 1024, "height": 1024,
     "steps": 20, "cfg_scale": 7},
    {"match": "realismIllustriousBy", "sampler": "Res Multistep", "width": 1024, "height": 1024,
     "steps": 27, "cfg_scale": 5},
]

ADMIN_RECORD_LIMIT = 300   # กันโหลดหนักถ้าข้อมูลเยอะมาก
HISTORY_LIMIT = 24         # จำนวนภาพในประวัติของผู้ใช้แต่ละคน
