"""
============================================================
 SINGLE-PC : รันทั้งระบบบนเครื่องเดียว — run_single_pc.py
------------------------------------------------------------
 ใช้โค้ดชุดเดียวกับตอนแยก 4 เครื่องทุกไฟล์ (ไม่ได้ก๊อปโค้ดมา)
 แค่เปลี่ยนที่อยู่ของทุกส่วนให้ชี้มาที่เครื่องนี้ (127.0.0.1)

   PC4 Database  -> pc4-database/db_server.py  ที่ 127.0.0.1:5100 (รันในโปรแกรมนี้)
   PC3 AI        -> Forge ที่เปิดเองใน Stability Matrix  127.0.0.1:7860
   PC2 Backend   -> pc2-backend/app.py         ที่ http://127.0.0.1:5000
   PC1 Frontend  -> pc1-frontend/html          เสิร์ฟจาก Flask ตัวเดียวกัน (แทน Nginx)

 Backend ยังคุยกับ Database และ Forge ผ่าน HTTP เหมือนตอนแยกเครื่องทุกอย่าง
 ข้อมูลของโหมดนี้ (ฐานข้อมูล + ไฟล์ภาพ) แยกไว้ที่ single-pc/data/
 ไม่ปนกับไฟล์ที่ใช้บน PC2 / PC4 และไม่ต้องแก้ config.py ของ 4 เครื่อง
============================================================
"""
import os
import sys
import threading
import webbrowser

# ------------------------------------------------------------
#  ตั้งค่าของโหมดเครื่องเดียว — แก้ได้ที่นี่ที่เดียว
# ------------------------------------------------------------
HOST = "127.0.0.1"        # เปลี่ยนเป็น "0.0.0.0" ถ้าอยากให้เครื่องอื่นในวง LAN เปิดเว็บนี้ได้
WEB_PORT = 5000           # เปิดเว็บที่ http://127.0.0.1:5000
DB_PORT = 5100            # Database Server (เปิดให้เฉพาะเครื่องนี้เรียก)
FORGE_URL = "http://127.0.0.1:7860"
OPEN_BROWSER = True       # เปิดเบราว์เซอร์ให้อัตโนมัติเมื่อระบบพร้อม

# ------------------------------------------------------------
#  ที่อยู่ของโฟลเดอร์ต่าง ๆ ในโปรเจกต์
# ------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKEND_DIR = os.path.join(ROOT, "pc2-backend")
DATABASE_DIR = os.path.join(ROOT, "pc4-database")
HTML_DIR = os.path.join(ROOT, "pc1-frontend", "html")

DATA_DIR = os.path.join(HERE, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")
STORAGE_DIR = os.path.join(DATA_DIR, "storage")
os.makedirs(DATA_DIR, exist_ok=True)

# ให้ Python หาโมดูลของ PC2 (app, config, db_client, image_ops) และ PC4 (db_server, schema) เจอ
sys.path.insert(0, DATABASE_DIR)
sys.path.insert(0, BACKEND_DIR)

# ------------------------------------------------------------
#  1) แก้ค่าใน config ของ PC2 ให้ชี้มาที่เครื่องนี้ (ต้องทำก่อน import app)
# ------------------------------------------------------------
import config  # noqa: E402  (pc2-backend/config.py)

config.FORGE_API_URL = FORGE_URL
config.DB_SERVER_URL = f"http://127.0.0.1:{DB_PORT}"
config.STORAGE_DIR = STORAGE_DIR
config.OUTPUT_DIR = os.path.join(STORAGE_DIR, "outputs")
config.EDIT_OUTPUT_DIR = os.path.join(config.OUTPUT_DIR, "edits")

# ค่าที่ db_server.py อ่านจาก environment variable
os.environ["DB_PATH"] = DB_PATH
os.environ["DB_PORT"] = str(DB_PORT)
os.environ["DB_TOKEN"] = config.DB_TOKEN

# ------------------------------------------------------------
#  2) เปิด Database Server (PC4) เป็น thread อยู่เบื้องหลัง
# ------------------------------------------------------------
from werkzeug.serving import make_server, WSGIRequestHandler  # noqa: E402

import db_server  # noqa: E402  (pc4-database/db_server.py)
from schema import init_db  # noqa: E402


class _QuietHandler(WSGIRequestHandler):
    """ไม่ต้องพิมพ์ log ทุก request ของ DB (ยังเห็นบรรทัด [DB] ตอนเพิ่ม/ลบข้อมูลอยู่)"""

    def log_request(self, *args, **kwargs):
        pass


def start_database():
    conn = db_server.get_conn()
    init_db(conn)
    conn.close()
    try:
        server = make_server("127.0.0.1", DB_PORT, db_server.app,
                             threaded=True, request_handler=_QuietHandler)
    except OSError:
        print(f"[X] เปิด Database ที่พอร์ต {DB_PORT} ไม่ได้ — มีโปรแกรมอื่นใช้พอร์ตนี้อยู่")
        print("    (เช่นเปิด pc4-database/start.bat ค้างไว้) ให้ปิดก่อนแล้วลองใหม่")
        sys.exit(1)
    threading.Thread(target=server.serve_forever, daemon=True).start()


# ------------------------------------------------------------
#  3) Backend (PC2) + ให้ Flask ตัวเดียวกันเสิร์ฟหน้าเว็บ (PC1) แทน Nginx
#     หน้าเว็บกับ API อยู่ origin เดียวกัน (http://127.0.0.1:5000) เหมือนตอนผ่าน Nginx
#     จึงไม่ต้องแก้ config.js (API_BASE = "")
# ------------------------------------------------------------
def build_backend():
    import app as backend  # (pc2-backend/app.py)
    from flask import send_from_directory

    def frontend_index():
        return send_from_directory(HTML_DIR, "index.html")

    def frontend_file(filename):
        return send_from_directory(HTML_DIR, filename)

    # route ของ /api/... และ /media/... เจาะจงกว่า จึงยังถูกเลือกก่อน route นี้เสมอ
    backend.app.add_url_rule("/", "single_pc_index", frontend_index)
    backend.app.add_url_rule("/<path:filename>", "single_pc_frontend", frontend_file)
    return backend.app


def check_forge():
    import requests
    try:
        r = requests.get(f"{FORGE_URL}/sdapi/v1/sd-models",
                         auth=(config.FORGE_API_USER, config.FORGE_API_PASS), timeout=3)
        r.raise_for_status()
        return f"พบ Forge แล้ว ({len(r.json())} โมเดล)"
    except Exception:
        return ("ยังไม่พบ Forge — สร้างภาพไม่ได้จนกว่าจะเปิด Forge "
                "(แท็บแก้ไขภาพใช้ได้ตามปกติ)")


if __name__ == "__main__":
    start_database()
    web_app = build_backend()
    url = f"http://127.0.0.1:{WEB_PORT}"

    print("============================================================")
    print("  ImageProject — Single PC (ทุกส่วนอยู่บนเครื่องนี้)")
    print("============================================================")
    print(f"  หน้าเว็บ + Backend : {url}")
    print(f"  Database          : 127.0.0.1:{DB_PORT}  ->  {DB_PATH}")
    print(f"  ไฟล์ภาพ            : {STORAGE_DIR}")
    print(f"  AI (Forge)        : {FORGE_URL}  ->  {check_forge()}")
    print(f"  เช็คสถานะ          : {url}/api/health")
    print("  ปิดระบบ: กด Ctrl+C หรือปิดหน้าต่างนี้")
    print("============================================================")

    if OPEN_BROWSER:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    web_app.run(host=HOST, port=WEB_PORT, threaded=True, debug=False)
