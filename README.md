# ImageProject (LUMA)

เว็บสร้างภาพด้วย Stable Diffusion (Forge) และแก้ไขภาพด้วย OpenCV
ทำเป็น Distributed System 4 เครื่องตามโจทย์ใน [`project.pdf`](project.pdf)

```
Browser ──> PC1  Nginx + หน้าเว็บ static (HTML/CSS/JS)        :80
              │   /api/  และ /media/  ส่งต่อให้ PC2
              ▼
            PC2  Backend — Flask JSON API + แก้ไขภาพ (OpenCV)  :5000
              ├──HTTP──> PC3  AI Server — Stable Diffusion Forge   :7860
              └──HTTP──> PC4  Database — SQLite + ไฟล์ภาพทั้งหมด    :5100
```

Browser คุยกับ PC1 เครื่องเดียว · PC3 และ PC4 รับ request จาก PC2 เท่านั้น

## Tech Stack

| ส่วน | เทคโนโลยี | ใช้ทำอะไร |
|---|---|---|
| **Frontend** (PC1) | HTML5, CSS3, JavaScript (ES2017+, ไม่ใช้ framework) | หน้าเว็บ static 4 หน้า เรียก API ด้วย `fetch()` |
| **Reverse Proxy** (PC1) | Nginx (Windows) | เสิร์ฟไฟล์ static และส่งต่อ `/api/`, `/media/` ไป PC2 |
| **Backend** (PC2) | Python 3, Flask 3.0.3 | JSON API |
| | Flask-Login 0.6.3, Werkzeug | session / สิทธิ์ผู้ใช้, hash รหัสผ่าน |
| | requests 2.32.3 | เรียก PC3 และ PC4 ผ่าน HTTP |
| | OpenCV 4.10 (`opencv-python-headless`), NumPy 1.26.4 | แก้ไขภาพ 4 กลุ่ม 12 วิธี |
| | `logging` (RotatingFileHandler) | log แบบหมุนไฟล์ |
| **AI Server** (PC3) | Stable Diffusion WebUI Forge ผ่าน Stability Matrix | สร้างภาพ (REST API `/sdapi/v1/...`) |
| | Checkpoint: `realSimpleAnime`, `realismIllustriousBy` | โมเดลที่อนุญาตให้เลือก |
| **Database** (PC4) | SQLite 3 (โมดูล `sqlite3` ของ Python) | ตาราง `users`, `generations`, `edits` |
| | Flask 3.0.3 | ครอบ SQLite เป็น HTTP service + เก็บไฟล์ภาพ |
| **การสื่อสาร** | HTTP/JSON บน LAN, Basic Auth (PC2→PC3), token ใน header (PC2→PC4) | เชื่อม 4 เครื่อง |
| **เครื่องมือ** | Windows batch (`setup.bat` / `start.bat`), PowerShell, `venv` | ติดตั้ง รัน และสำรองข้อมูล |
| | Git / GitHub | จัดการโค้ด (แยก branch ตามเครื่อง) |

เวอร์ชันของ library ฝั่ง Python กำหนดไว้ใน `pc2-backend/requirements.txt` และ `pc4-database/requirements.txt`

## โฟลเดอร์

| โฟลเดอร์ | เครื่อง | มีอะไร | วิธีติดตั้ง/รัน |
|---|---|---|---|
| [`pc1-frontend/`](pc1-frontend/) | PC1 | หน้าเว็บ static + config ของ Nginx | [README](pc1-frontend/README.md) |
| [`pc2-backend/`](pc2-backend/) | PC2 | Flask API, แก้ไขภาพ, log | [README](pc2-backend/README.md) |
| [`pc3-ai/`](pc3-ai/) | PC3 | ไม่มีโค้ด — บันทึกวิธีตั้งค่า Forge | [README](pc3-ai/README.md) |
| [`pc4-database/`](pc4-database/) | PC4 | ครอบ SQLite เป็น HTTP service + เก็บไฟล์ภาพ | [README](pc4-database/README.md) |
| [`single-pc/`](single-pc/) | เครื่องเดียว | รันทั้งระบบบนเครื่องเดียว (ใช้โค้ดชุดเดียวกัน) | [README](single-pc/README.md) |
| [`tests/`](tests/) | — | smoke test ของ API | ดูหัวข้อ "ทดสอบ" |
| [`scripts/`](scripts/) | PC4 | สคริปต์สำรองข้อมูล | [docs/backup.md](docs/backup.md) |

## เริ่มใช้งาน

**ลองบนเครื่องเดียว** (ไม่ต้องมี Nginx): ทำตาม [`single-pc/README.md`](single-pc/README.md)
— ดับเบิลคลิก `setup.bat` ครั้งเดียว แล้ว `start.bat`

**รันจริง 4 เครื่อง** — แต่ละเครื่องมี `setup.bat` (ครั้งเดียว) และ `start.bat` ในโฟลเดอร์ของตัวเอง
เปิดตามลำดับนี้ เพราะเครื่องหลังต้องต่อหาเครื่องก่อนหน้า:

1. **PC4** Database — `pc4-database/`
2. **PC3** AI Server — เปิด Forge ตาม [`pc3-ai/README.md`](pc3-ai/README.md)
3. **PC2** Backend — `pc2-backend/` (เช็คการต่อไป PC3 ด้วย `check-ai.bat`)
4. **PC1** Nginx — `pc1-frontend/start-nginx.bat`

เปิดเว็บที่ `http://<IP ของ PC1>/` · คนที่สมัครสมาชิกคนแรกจะได้เป็น admin อัตโนมัติ
มีปัญหาให้เปิด `http://<IP ของ PC1>/api/health` ดูก่อน — บอกสถานะ PC2 / PC3 / PC4

## ที่อยู่เครื่อง

ตารางนี้คือค่าที่ **โค้ดใช้อยู่ตอนนี้** — เน็ตแจก IP แบบ DHCP ถ้า IP เปลี่ยนต้องแก้ไฟล์ในคอลัมน์ขวา

| เครื่อง | ที่อยู่ในโค้ด | ถ้า IP เปลี่ยน แก้ที่ |
|---|---|---|
| PC1 Nginx | `172.20.56.128:80` | `ALLOWED_ORIGINS` ใน `pc2-backend/config.py` (ตัว Nginx รับทุก IP อยู่แล้ว) |
| PC2 Backend | `172.20.56.107:5000` | `upstream` ใน `pc1-frontend/nginx/imageproject.conf` และ `ALLOWED_CLIENT_IPS` ใน `pc4-database/db_server.py` |
| PC3 AI Server | `172.20.56.170:7860` | `FORGE_API_URL` ใน `pc2-backend/config.py` |
| PC4 Database | `172.20.56.108:5100` | `DB_SERVER_URL` ใน `pc2-backend/config.py` |

## ค่าลับ (.env)

รหัสผ่านและ token ไม่อยู่ในโค้ด — คัดลอก `.env.example` เป็น `.env` ในโฟลเดอร์เดียวกันแล้วใส่ค่า
(`.env` ถูก gitignore ไว้ ห้าม commit)

| ไฟล์ | ต้องมี |
|---|---|
| `pc2-backend/.env` | `DB_TOKEN`, `FORGE_API_USER`, `FORGE_API_PASS`, `SECRET_KEY` |
| `pc4-database/.env` | `DB_TOKEN` (ค่าเดียวกับของ PC2) |

PC2 และ PC4 จะไม่ยอมเปิดถ้ายังไม่ได้ตั้ง `DB_TOKEN`

## ทดสอบ

```bat
pc2-backend\venv\Scripts\python.exe tests\smoke_test.py
```

รัน Backend กับ Database Server จริงในโปรแกรมเดียว ใช้ฐานข้อมูลชั่วคราว (ไม่แตะข้อมูลจริง)
และจำลอง AI Server จึงรันได้ทุกเครื่องโดยไม่ต้องมี Forge — ครอบคลุม สมัคร/ล็อกอิน, สิทธิ์ admin,
สร้างภาพ, จำกัดความถี่, แก้ไขภาพทุกฟังก์ชัน, ลบรายการ, ไฟล์ภาพ และ log
ไม่ครอบคลุม: การสร้างภาพจริง (PC2 → PC3) และชั้น Nginx (PC1)

## เอกสารอื่น

- [`docs/REPORT.md`](docs/REPORT.md) — รายงานโครงงาน
- [`docs/backup.md`](docs/backup.md) — สำรอง/กู้คืนข้อมูล
- [`TODO.md`](TODO.md) — งานที่เหลือ
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — บันทึกสิ่งที่ทำไปแล้ว
