"""
============================================================
 check_ai.py — ทดสอบว่าเครื่อง PC2 นี้ ยิงไปหา AI Server (PC3) ได้จริงไหม
 วางไว้ที่ PC2 เพราะ "เส้นทางจริง" ที่ต้องพิสูจน์คือ PC2 -> PC3
 (ถ้าไปรันบน PC3 เองแล้วเทสต์ 127.0.0.1 จะผ่านเสมอ ไม่ได้บอกอะไร)

 วิธีใช้:
     python check_ai.py                      # เช็ค 10.187.226.10
     python check_ai.py 10.187.226.10 7860    # ระบุ IP/พอร์ตเอง
============================================================
"""
import sys

import requests

HOST = sys.argv[1] if len(sys.argv) > 1 else "10.187.226.10"
PORT = sys.argv[2] if len(sys.argv) > 2 else "7860"
USER = "admin"
PASS = "cdti1234"

BASE = f"http://{HOST}:{PORT}"


def check(path, label):
    try:
        r = requests.get(f"{BASE}{path}", auth=(USER, PASS), timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"  [X] {label}: ต่อไม่ได้ -> {e}")
        return None

    if r.status_code == 401:
        print(f"  [X] {label}: user/pass ไม่ถูก (เทียบกับ --api-auth ใน Launch Options)")
        return None
    if r.status_code != 200:
        print(f"  [X] {label}: HTTP {r.status_code}")
        return None

    print(f"  [OK] {label}")
    return r.json()


print(f"กำลังตรวจสอบ AI Server ที่ {BASE} ...\n")

models = check("/sdapi/v1/sd-models", "รายชื่อ checkpoint")
samplers = check("/sdapi/v1/samplers", "รายชื่อ sampler")

if models is not None:
    print(f"\nพบ checkpoint ทั้งหมด {len(models)} ตัว:")
    for m in models:
        print(f"   - {m.get('model_name')}   (title: {m.get('title')})")
    print("\nชื่อที่เห็นข้างบนต้องมี substring ตรงกับ 'match' ใน")
    print("pc2-backend/config.py -> ALLOWED_CHECKPOINTS ไม่งั้น dropdown จะว่าง")

if samplers is not None:
    print(f"\nพบ sampler ทั้งหมด {len(samplers)} ตัว")

if models is None and samplers is None:
    print("\nเช็ครายการนี้:")
    print("  1. Forge เปิดอยู่ไหม และตั้ง --api ใน Launch Options แล้วหรือยัง")
    print("  2. ตั้ง --listen เพื่อให้เครื่องอื่นเข้าถึงได้แล้วหรือยัง")
    print("  3. Firewall เปิดพอร์ต 7860 ขาเข้าแล้วหรือยัง")
    print("  4. IP ของเครื่อง AI ถูกต้องไหม (ipconfig)")
