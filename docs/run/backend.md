# วิธีรัน — Backend (Flask + SQLite)

**หน้าที่ของเครื่องนี้** IP ที่รู้อยู่ตอนนี้: `172.20.57.27`

รัน `webapp/app.py`: auth, API สำหรับ generate/edit/png-info, หน้า admin,
และ SQLite (`database.db`) ตอนนี้ยังทำหน้าที่ serve template/static ของ
frontend ด้วย เพราะยังไม่ได้แยกออกมาตาม `TODO.md` ข้อ 1 — ดู
[`frontend.md`](frontend.md) ว่ามันหมายความว่าอย่างไรสำหรับคนที่ดูแลฝั่ง
Frontend

## 1. สิ่งที่ต้องมีก่อน
- Python environment ที่มีแพ็กเกจตาม `webapp/requirements.txt` บนเครื่องนี้
  ใช้ conda env ชื่อ `img_proc` — มีครบทุกอย่างแล้ว:
  ```bash
  conda activate img_proc
  ```
- ตั้งค่า `webapp/.env` ให้ครบ (ถ้ายังไม่มีให้ copy จาก `webapp/.env.example`)
  อย่างน้อยต้องมี `SECRET_KEY` และค่า `FORGE_API_*` ที่ชี้ไปยังเครื่องที่รัน
  AI Server (ดู [`ai-server.md`](ai-server.md)) ตอนนี้ตั้งไว้เป็น
  `FORGE_API_URL=http://172.20.56.112:7860`

## 2. รันแอป

```bash
cd webapp
conda activate img_proc
python app.py
```

ฟังที่ `0.0.0.0:5000` (เครื่องอื่นในวง LAN เข้าถึงได้) รันครั้งแรกจะสร้าง
`database.db`, `static/outputs/`, และ `logs/` ให้อัตโนมัติ คนที่สมัคร
สมาชิกคนแรกจะได้เป็น admin อัตโนมัติ

## 3. ตรวจสอบว่าใช้งานได้

```bash
python tests/smoke_test.py
```

รันกับฐานข้อมูลชั่วคราว — รันตอนไหนก็ได้อย่างปลอดภัย ไม่แตะ `database.db`
ตัวจริง ครอบคลุม auth, การแก้ไขภาพ, และ route ของ admin **ไม่ครอบคลุม**
`/api/generate` หรือฝั่งที่ต้องต่อ AI Server ของ `/api/png-info` — สองอย่างนี้
ต้องให้ AI Server รันอยู่และเชื่อมต่อได้ก่อน (ดู [`ai-server.md`](ai-server.md))
แล้วค่อยเทสต์เองผ่านหน้าเว็บที่ `http://172.20.57.27:5000`

## 4. Log และการสำรองข้อมูล
- Log: `webapp/logs/app.log` (หมุนไฟล์อัตโนมัติ สร้างให้เองตอนรัน)
- สำรองข้อมูล: `powershell -File ..\scripts\backup.ps1` — ดู
  [`../backup.md`](../backup.md)

## สิ่งที่เครื่องนี้ยังไม่ได้ทำ
- ยังไม่ได้อยู่หลัง Nginx — ตอนนี้เข้าถึงตรงผ่านพอร์ต 5000 ไปก่อน (ดู
  [`nginx.md`](nginx.md) สำหรับแผน reverse proxy)
- ยังทำหน้าที่ serve HTML/CSS/JS ของ frontend เองอยู่ (ดู
  [`frontend.md`](frontend.md))
- ยังใช้ SQLite ไม่ใช่ PostgreSQL (ต้องเปลี่ยนก็ต่อเมื่อทีมเลือกใช้ layout
  แบบ 4 เครื่อง — ดู `TODO.md` ข้อ 0)
