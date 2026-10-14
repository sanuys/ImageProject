# ImageProject (LUMA)

ระบบสร้างและแก้ไขภาพแบบ Distributed System 4 เครื่อง
วิชา 310-3311 การประมวลผลภาพ (Digital Image Processing) — สถาบันเทคโนโลยีจิตรลดา (CDTI)
โครงงานตามข้อกำหนดใน [`project.pdf`](project.pdf)

---

## สมาชิกกลุ่มและการแบ่งหน้าที่

| เครื่อง (PC) | ผู้รับผิดชอบ | รหัสนักศึกษา | บทบาทและหน้าที่หลัก |
|:---:|---|:---:|---|
| **PC-1** | คชา สวัสดิพิศาล | 6710301054 | **Frontend & Reverse Proxy** — Nginx, Static Web UI (HTML/CSS/JS) |
| **PC-2** | มูฮัมหมัดฮาซัน อุเซ็ง | 6710301025 | **Backend & Image Processing** — Flask REST API, OpenCV, Auth, Logging |
| **PC-3** | ชนสรณ์ ควรสุวรรณ | 6710301004 | **AI Server** — Stable Diffusion WebUI Forge (Stability Matrix) |
| **PC-4** | ปิ่นพงศ์ ชูสุวรรณ | 6710301023 | **Database & Storage** — SQLite HTTP Service, Image Storage, Backup |

---

## ภาพรวมสถาปัตยกรรม (Architecture)

ระบบแบ่งออกเป็น 4 Tier ตามหลักการของระบบกระจาย (Distributed System):

```
ผู้ใช้งาน (Browser)
       │ HTTP :80
       ▼
┌────────────────────────────────────────────────────────┐
│ PC1 : Frontend & Reverse Proxy (Nginx)                 │
│   • เสิร์ฟไฟล์ Static Web (HTML5 / CSS3 / Vanilla JS)     │
│   • ส่งต่อ /api/ และ /media/ ไปยัง PC2                    │
└───────────────────────┬────────────────────────────────┘
                        │ HTTP :5000
                        ▼
┌────────────────────────────────────────────────────────┐
│ PC2 : Logic Tier (Flask Backend)                       │
│   • ระบบสมาชิก (Session Auth), สิทธิ์ผู้ดูแล (Admin)         │
│   • Image Processing ด้วย OpenCV (4 กลุ่ม 12 ฟังก์ชัน)      │
│   • Cooldown Rate Limiting, Audit Logging              │
└───────────────┬────────────────────────┬───────────────┘
                │ HTTP :7860             │ HTTP :5100
                │ (Basic Auth)           │ (Header Token + IP Whitelist)
                ▼                        ▼
┌──────────────────────────────┐ ┌──────────────────────────────────────┐
│ PC3 : AI Server              │ │ PC4 : Data Tier                      │
│   • Stable Diffusion Forge   │ │   • SQLite Database via HTTP API     │
│   • โมเดล Text-to-Image      │ │   • ที่เก็บไฟล์ภาพทั้งหมด (storage/)      │
└──────────────────────────────┘ └──────────────────────────────────────┘
```

> **หมายเหตุ:** Browser ติดต่อผ่าน PC1 เพียงจุดเดียว ส่วน PC3 และ PC4 รับคำสั่งจาก PC2 ผ่านเครือข่ายภายในเท่านั้น

---

## ฟีเจอร์หลักของระบบ

### 1. การสร้างภาพด้วย AI (Text-to-Image) — PC3
- เชื่อมต่อกับ **Stable Diffusion WebUI Forge** ผ่าน REST API (`/sdapi/v1/txt2img`)
- รองรับ Checkpoint ที่ผ่านการคัดสรร:
  - `realSimpleAnime_v10` (สไตล์อนิเมะ)
  - `realismIllustriousBy_v55BF16` (สไตล์สมจริง/อิลลัสต์)
- ปรับแต่งพารามิเตอร์ได้: Prompt, Negative Prompt, Sampler (เช่น Euler a, Res Multistep), Steps, CFG Scale, Seed, ขนาดภาพ (1024×1024)
- มีระบบ Cooldown Rate Limiting ป้องกันการส่งคำขอสร้างภาพซ้ำซ้อน

### 2. การแก้ไขภาพด้วย OpenCV (Digital Image Processing) — PC2
ครอบคลุมเทคนิคประมวลผลภาพ 4 กลุ่ม รวม 12 วิธี ตามเนื้อหารายวิชา:
1. **Point Operation (การประมวลผลระดับจุด)**
   - **Negative**: กลับค่าความสว่างของพิกเซล ($s = 255 - r$)
   - **Log Transformation**: ขยายรายละเอียดในส่วนมืด ($s = c \cdot \log(1 + r)$)
   - **Contrast Stretching**: ปรับยืดช่วงความคมชัดตามจุดควบคุม ($r_1, s_1, r_2, s_2$)
2. **Auto Contrast (การปรับคอนทราสต์อัตโนมัติ)**
   - **Automatic Contrast Adjustment**: ปรับขยายฮิสโตแกรมให้เต็มช่วง 0–255 อัตโนมัติ
   - **Histogram Equalization**: ปรับการกระจายความถี่ของระดับสีเทาให้สม่ำเสมอ
3. **Linear Spatial Filtering (การกรองเชิงเส้นในระนาบพิกเซล)**
   - **Mean Filter**: เบลอภาพแบบเฉลี่ยลดสัญญาณรบกวน (Kernel $3\times3, 5\times5, 7\times7, 9\times9$)
   - **Gaussian Filter**: เบลอภาพแบบถ่วงน้ำหนักเกาส์เซียน (Kernel ขนาดคี่ พร้อมคำนวณ $\sigma$)
   - **Laplacian Filter**: ตรวจจับขอบภาพและเพิ่มความคมชัด (Sharpening)
4. **Non-linear Spatial Filtering (การกรองไม่เชิงเส้น)**
   - **Median Filter**: กำจัดสัญญาณรบกวนแบบเกลือพริกไทย (Salt & Pepper Noise)
   - **Min Filter**: กรองเอาค่าต่ำสุดในหน้าต่าง (Morphological Erosion)
   - **Max Filter**: กรองเอาค่าสูงสุดในหน้าต่าง (Morphological Dilation)

### 3. ระบบความปลอดภัยและสิทธิ์ผู้ใช้
- สมัครสมาชิกและเข้าสู่ระบบด้วย Session Cookie เข้ารหัส
- แฮชรหัสผ่านด้วย `werkzeug.security` (PBKDF2-HMAC-SHA256) ป้องกันรหัสผ่านรั่วไหล
- ผู้ใช้ที่ลงทะเบียนคนแรกของระบบจะได้รับการแต่งตั้งเป็น **Admin** โดยอัตโนมัติ
- หน้า **Admin Dashboard** สำหรับตรวจสอบประวัติการสร้างภาพและสิทธิ์ลบภาพ/บันทึกทั้งหมด
- ไฟล์ภาพใน `/media/` บังคับตรวจสอบสถานะการล็อกอิน

### 4. ระบบฐานข้อมูลและพื้นที่จัดเก็บแบบแยกเครื่อง — PC4
- ครอบ SQLite เป็น HTTP Data Service (`db_server.py`) ป้องกันปัญหา Database Lock ข้ามเครือข่าย
- จัดเก็บทั้งข้อมูลตาราง (`users`, `generations`, `edits`) และไฟล์ภาพจริง (`storage/outputs/`)
- ป้องกันการเข้าถึงด้วย Header Token (`X-DB-Token`) และจำกัด Client IP ที่อนุญาต

---

## Tech Stack

| ส่วนประกอบ | เทคโนโลยี | รายละเอียดและหน้าที่ |
|---|---|---|
| **Frontend** (PC1) | HTML5, CSS3, JavaScript (Vanilla ES2017+) | เว็บ static 4 หน้า (`index`, `login`, `register`, `admin`) เรียก API ด้วย `fetch()` |
| **Reverse Proxy** (PC1) | Nginx (Windows) | จัดการ Reverse Proxy รับพอร์ต 80 และส่งต่อ `/api/`, `/media/` ไปยัง PC2 |
| **Backend** (PC2) | Python 3.10+, Flask 3.0.3 | Logic Tier, REST API, ตรวจสอบสิทธิ์, บริหารจัดการคิว |
| | Flask-Login 0.6.3, Werkzeug | ระบบจัดการ Session และการยืนยันตัวตนผู้ใช้ |
| | OpenCV 4.10 (`opencv-python-headless`), NumPy | ประมวลผลภาพดิจิทัล 4 กลุ่ม 12 ฟังก์ชัน |
| | Python standard `logging` (RotatingFileHandler) | บันทึกประวัติการทำงานและข้อผิดพลาดลงไฟล์ `logs/app.log` |
| **AI Server** (PC3) | Stable Diffusion Forge via Stability Matrix | ให้บริการ Text-to-Image Generation ผ่าน REST API พอร์ต 7860 |
| **Database** (PC4) | SQLite 3 (`sqlite3`), Flask 3.0.3 | Data Tier ให้บริการฐานข้อมูลและจัดเก็บไฟล์ภาพผ่าน HTTP API พอร์ต 5100 |
| **การเชื่อมต่อ** | HTTP/JSON บน LAN | เชื่อมโยง 4 เครื่องเข้าด้วยกันผ่านเครือข่ายวงแลน |
| **DevOps / Scripts** | PowerShell, Batch Scripts, Python `venv` | สคริปต์สำหรับการติดตั้ง, รันระบบ, ทดสอบ และสำรองข้อมูล |

---

## โครงสร้างโฟลเดอร์

```
ImageProject/
├── pc1-frontend/         # PC1: Nginx config, หน้าเว็บ static (HTML, CSS, JS)
│   ├── html/             # หน้าเว็บ index.html, login.html, register.html, admin.html
│   ├── nginx/            # imageproject.conf สำหรับตั้งค่า Nginx
│   └── start-nginx.bat   # สคริปต์เริ่มทำงาน Nginx
├── pc2-backend/          # PC2: Flask REST API, OpenCV Image Operations
│   ├── app.py            # API Server หลัก
│   ├── image_ops.py      # ฟังก์ชันประมวลผลภาพ 12 วิธี
│   ├── db_client.py      # ตัวเชื่อมต่อไปยัง PC4 Database
│   ├── config.py         # ค่าคอนฟิก IP และพารามิเตอร์
│   └── check-ai.bat      # สคริปต์ตรวจเช็คการเชื่อมต่อไปยัง PC3
├── pc3-ai/               # PC3: เอกสารและข้อกำหนดการเปิด Forge API
│   └── README.md         # คำแนะนำการตั้งค่า Launch Options (--api, --listen)
├── pc4-database/         # PC4: HTTP Data Server และพื้นที่จัดเก็บไฟล์ภาพ
│   ├── db_server.py      # HTTP Service ครอบ SQLite และจัดการไฟล์
│   ├── schema.py         # โครงสร้างตารางฐานข้อมูลและการ Migrate
│   └── storage/          # โฟลเดอร์เก็บรูปภาพจริง (outputs/, edits/)
├── single-pc/            # สำหรับทดสอบระบบทั้งหมดบนเครื่องคอมพิวเตอร์เครื่องเดียว
│   ├── run_single_pc.py  # รันทั้ง Frontend, Backend และ Database ในเครื่องเดียว
│   ├── setup.bat         # ติดตั้ง Dependencies สำหรับ Single-PC
│   └── start.bat         # รันระบบ Single-PC
├── tests/                # สคริปต์ทดสอบระบบอัตโนมัติ
│   └── smoke_test.py     # Smoke Test ครอบคลุม 70 รายการทดสอบ
├── scripts/              # สคริปต์ยูทิลิตี้
│   ├── backup.ps1        # สำรองข้อมูลฐานข้อมูลและรูปภาพ (PowerShell)
│   └── backup.sh         # สำรองข้อมูลฐานข้อมูลและรูปภาพ (Bash)
└── docs/                 # รายงานและเอกสารทางเทคนิค
    ├── REPORT.md         # รายงานโครงงานฉบับสมบูรณ์ (ภาษาไทย)
    ├── PROGRESS.md       # บันทึกประวัติและขั้นตอนการพัฒนาระบบ
    └── backup.md         # คู่มือการสำรองและกู้คืนข้อมูล
```

---

## ที่อยู่เครื่องและพอร์ต (Network Configuration)

เครือข่ายห้องเรียนแจก IP แบบ DHCP ค่า IP อาจเปลี่ยนแปลงได้ตามรอบการเชื่อมต่อ ค่าคอนฟิกปัจจุบันที่ใช้งานจริงในระบบ:

| เครื่อง | หน้าที่ | IP และพอร์ต ปัจจุบัน | ไฟล์คอนฟิกที่ต้องแก้ไขเมื่อ IP เปลี่ยน |
|---|---|---|---|
| **PC1** | Frontend / Nginx | `172.20.56.117:80` | `ALLOWED_ORIGINS` ใน `pc2-backend/config.py` |
| **PC2** | Backend API | `172.20.56.107:5000` | `upstream` ใน `pc1-frontend/nginx/imageproject.conf`<br>`ALLOWED_CLIENT_IPS` ใน `pc4-database/db_server.py` |
| **PC3** | AI Server (Forge) | `172.20.56.108:7860` | `FORGE_API_URL` ใน `pc2-backend/config.py` |
| **PC4** | Database Server | `172.20.56.113:5100` | `DB_SERVER_URL` ใน `pc2-backend/config.py` |

---

## การตั้งค่าความปลอดภัย (.env)

ระบบใช้ไฟล์ `.env` สำหรับเก็บความลับและ token โดยแยกออกจากโค้ดและถูกละเว้นจาก Git (`.gitignore`):

| ที่อยู่ไฟล์ | ตัวแปรที่ต้องกำหนด | คำอธิบาย |
|---|---|---|
| `pc2-backend/.env` | `DB_TOKEN` | โทเคนสำหรับยืนยันตัวตนกับ PC4 (ต้องตรงกัน) |
| | `FORGE_API_USER` | ชื่อผู้ใช้ API ของ Forge (ตรงกับ `--api-auth`) |
| | `FORGE_API_PASS` | รหัสผ่าน API ของ Forge |
| | `SECRET_KEY` | คีย์ลับสำหรับเซ็น Session Cookie |
| | `GENERATE_COOLDOWN_SECONDS` | เวลารอขั้นต่ำระหว่างการสร้างภาพ (ค่าเริ่มต้น: 3) |
| `pc4-database/.env` | `DB_TOKEN` | โทเคนความปลอดภัย (ต้องตรงกับของ PC2) |

> **คำเตือน:** PC2 และ PC4 จะปฏิเสธการเริ่มทำงานทันทีหากยังไม่ได้กำหนดค่า `DB_TOKEN`

---

## วิธีการเริ่มใช้งาน (Getting Started)

### วิธีที่ 1: รันบนเครื่องเดียว (Single-PC Mode)
เหมาะสำหรับการพัฒนา ทดสอบฟังก์ชัน หรือเปิดสาธิตโดยไม่ต้องใช้เครื่องหลายเครื่อง:

1. เปิด **Stability Matrix** แล้วกด Launch **Forge** (ต้องระบุ `--api` และ `--api-auth user:pass` ให้ตรงกับใน `.env`)
2. เข้าโฟลเดอร์ `single-pc/` แล้วดับเบิลคลิก **`setup.bat`** (ทำครั้งแรกครั้งเดียว)
3. ดับเบิลคลิก **`start.bat`**
4. เบราว์เซอร์จะเปิดไปที่ `http://127.0.0.1:5000/` อัตโนมัติ

ดูรายละเอียดเพิ่มเติมที่ [`single-pc/README.md`](single-pc/README.md)

---

### วิธีที่ 2: รันแบบแยก 4 เครื่องจริง (Distributed Mode)
ต้องเปิดบริการตามลำดับจากหลังมาหน้า เพื่อให้เครื่องที่ต้องเชื่อมต่อสามารถติดต่อบริการปลายทางได้:

1. **เปิด PC4 (Database)**
   - เข้าโฟลเดอร์ `pc4-database/`
   - รันคำสั่ง `python db_server.py` (หรือใช้ `start.bat`)
   - ตรวจสอบว่าหน้าต่างขึ้น `เปิดรับ : http://0.0.0.0:5100`
2. **เปิด PC3 (AI Server)**
   - เปิด Stability Matrix แล้วเปิด Forge พร้อม Launch Options: `--api --listen --api-auth user:pass`
3. **เปิด PC2 (Backend)**
   - เข้าโฟลเดอร์ `pc2-backend/`
   - ทดสอบการเชื่อมต่อ PC3 ด้วยการดับเบิลคลิก `check-ai.bat`
   - รัน `python app.py` (หรือใช้ `start.bat`)
4. **เปิด PC1 (Frontend & Nginx)**
   - ตรวจสอบ path และ IP ปลายทางใน `pc1-frontend/nginx/imageproject.conf`
   - รัน `pc1-frontend/start-nginx.bat`

เปิดเบราว์เซอร์เข้าใช้งานที่:
```
http://<IP ของ PC1>/
เช่น http://172.20.56.117/
```

- ผู้ใช้งานที่สมัครสมาชิกคนแรกจะได้รับสิทธิ์ **Admin** โดยอัตโนมัติ
- สามารถตรวจสอบสถานะการเชื่อมต่อระหว่างเครื่องได้ที่: `http://<IP ของ PC1>/api/health`

---

## การทดสอบระบบ (Testing)

ระบบมีชุดทดสอบอัตโนมัติ (Smoke Test) ที่จำลองการทำงานของ Backend และ Database ร่วมกันอย่างสมบูรณ์:

```bat
python tests\smoke_test.py
```

- **ครอบคลุมการทดสอบ 70 รายการ**: การสมัครสมาชิก, การเข้าสู่ระบบ, การเลื่อนขั้นสิทธิ์ Admin, การจำกัดอัตราคำขอ (Rate Limit), การสร้างภาพ (จำลอง AI), การตัดสิทธิ์เมื่อ Token ผิด, ฟังก์ชันการแต่งภาพครบทั้ง 12 ฟังก์ชัน, การลบข้อมูล, การทำงานของ Log ฯลฯ
- ผ่านการทดสอบครบถ้วน 70/70 รายการ

---

## การสำรองข้อมูล (Backup)

สคริปต์สำหรับสำรองไฟล์ฐานข้อมูล `database.db` และไฟล์รูปภาพทั้งหมดใน `storage/`:

```powershell
# บนเครื่อง PC4
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1

# หรือสำหรับโหมด Single-PC
powershell -ExecutionPolicy Bypass -File scripts\backup.ps1 -SinglePc
```

ไฟล์สำรองจะถูกบีบอัดเป็น `.zip` และเก็บไว้ในโฟลเดอร์ `backups/` พร้อมระบุวันเวลาในชื่อไฟล์
ดูรายละเอียดและขั้นตอนการกู้คืนข้อมูลได้ที่ [`docs/backup.md`](docs/backup.md)

---

## เอกสารเพิ่มเติมในโครงการ

- [`docs/REPORT.md`](docs/REPORT.md) — รายงานโครงงานฉบับสมบูรณ์ (ทฤษฎีการประมวลผลภาพ, สถาปัตยกรรม, ผลการทดสอบ)
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — บันทึกประวัติและขั้นตอนการพัฒนาระบบ
- [`docs/backup.md`](docs/backup.md) — คู่มือการสำรองและกู้คืนข้อมูล
- [`docs/TODO.md`](docs/TODO.md) — รายการงานที่เสร็จสิ้นและสิ่งที่ต้องดำเนินการต่อ
- [`docs/project.pdf`](docs/project.pdf) — เอกสารข้อกำหนดโจทย์โครงงาน
- [`docs/ImageProject_Slide.pdf`](docs/ImageProject_Slide.pdf) — สไลด์นำเสนอโปรเจค
- [`docs/Guide.html`](docs/Guide.html`) — ไกด์แสดงกระบวนการทำงานทีละขั้นตอน
