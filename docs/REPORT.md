# รายงานโครงงาน LUMA — ระบบสร้างและแก้ไขภาพแบบ Distributed System

### สมาชิกกลุ่ม

| PC | ชื่อ - นามสกุล | รหัสนักศึกษา |
|:---:|---|:---:|
| PC-1 Front-end | คชา สวัสดิพิศาล | 6710301054 |
| PC-2 Back-end | มูฮัมหมัดฮาซัน อุเซ็ง | 6710301025 |
| PC-3 AI Server | ชนสรณ์ ควรสุวรรณ | 6710301004 |
| PC-4 Data Base | ปิ่นพงศ์ ชูสุวรรณ | 6710301023 |

---

### ข้อมูลรายวิชา

| รายการ | รายละเอียด |
|---|---|
| **รายวิชา** | 310-3311 การประมวลผลภาพ (Image Processing) 69/1 |
| **อาจารย์ผู้สอน** | กฤษฎา พรหมสุทธิรักษ์ |
| **วันที่จัดทำ** | 14 ตุลาคม 2569 (ค.ศ. 2026) |
---

## 1. บทนำ

### 1.1 ที่มาและโจทย์

โจทย์ของโครงงาน (`project.pdf`) กำหนดให้สร้างเว็บแอปพลิเคชันในรูปแบบ **Distributed System**
โดยสมาชิกแต่ละคนใช้คอมพิวเตอร์คนละเครื่อง แยก IP Address กัน แต่ละเครื่องทำหน้าที่ต่างกัน
และใช้ความรู้จากรายวิชา Network เชื่อมทุกเครื่องเข้าด้วยกัน โครงสร้างที่โจทย์กำหนดคือ

```
Browser → Nginx (Reverse Proxy) ─┬─ Frontend (HTML / CSS / JS)
                                  └─ Backend (Flask) ─┬─ AI Server
                                                      └─ Database
```

โจทย์ยกตัวอย่างการจัดเครื่องไว้ 2 แบบ คือ 3 เครื่อง (Frontend+Nginx / Forge AI / Flask+SQLite)
และ 4 เครื่อง (Frontend+Nginx / Forge AI / Flask / PostgreSQL)

### 1.2 วัตถุประสงค์

1. สร้างเว็บที่ผู้ใช้สั่ง **สร้างภาพจากข้อความ** (Text-to-Image) ด้วย Stable Diffusion ได้
2. ให้ผู้ใช้ **แก้ไขภาพ** ด้วยเทคนิค Digital Image Processing (อ้างอิงวิชา 310-3311) ได้
3. แยกระบบออกเป็นหลายเครื่องที่สื่อสารกันผ่านเครือข่าย LAN โดยมี Nginx เป็น Reverse Proxy
4. มีระบบสมาชิก สิทธิ์ผู้ดูแล การบันทึก log การทดสอบ และการสำรองข้อมูล ตามตารางหน้าที่ในโจทย์

### 1.3 ขอบเขต

- เลือกจัดเครื่องแบบ **4 เครื่อง** — PC1 Frontend+Nginx, PC2 Backend, PC3 AI Server, PC4 Database
- ใช้งานภายในวง LAN เดียวกัน (HTTP ไม่ได้เข้ารหัส) ไม่ได้ออกแบบให้เปิดสู่อินเทอร์เน็ต
- มีโหมด **Single-PC** สำหรับพัฒนา/สาธิตบนเครื่องเดียว โดยใช้โค้ดชุดเดียวกันทุกไฟล์

---

## 2. สถาปัตยกรรมระบบ

### 2.1 ภาพรวม

```
Browser ──> PC1  Nginx + หน้าเว็บ static (HTML/CSS/JS)        :80
              │   /api/  และ /media/  ส่งต่อให้ PC2
              ▼
            PC2  Backend — Flask JSON API + แก้ไขภาพ (OpenCV)  :5000
              ├──HTTP──> PC3  AI Server — Stable Diffusion Forge   :7860
              └──HTTP──> PC4  Database — SQLite + ไฟล์ภาพทั้งหมด    :5100
```

ผู้ใช้เปิดเว็บที่ PC1 เครื่องเดียว ไม่ต้องรู้ว่าข้างหลังมีอีก 3 เครื่อง
ส่วน PC3 และ PC4 รับ request จาก PC2 เท่านั้น browser ไม่ได้คุยด้วยโดยตรง

| เครื่อง | ชั้น (Tier) | หน้าที่ | เทคโนโลยี | พอร์ต |
|---|---|---|---|---|
| PC1 | Presentation | เสิร์ฟหน้าเว็บ และเป็นประตูทางเข้าเดียวของระบบ | Nginx, HTML/CSS/JavaScript | 80 |
| PC2 | Logic | ระบบสมาชิก, API, แก้ไขภาพ, log | Python, Flask, Flask-Login, OpenCV, NumPy | 5000 |
| PC3 | AI | รันโมเดล Stable Diffusion | Stability Matrix + Forge (REST API) | 7860 |
| PC4 | Data | เก็บฐานข้อมูลและไฟล์ภาพ | SQLite ครอบด้วย Flask เป็น HTTP service | 5100 |

ที่อยู่ที่ตั้งไว้ในโค้ดปัจจุบัน (เครือข่ายแจก IP แบบ DHCP จึงต้องแก้เมื่อ IP เปลี่ยน):
PC1 `172.20.56.117`, PC2 `172.20.56.107`, PC3 `172.20.56.108`, PC4 `172.20.56.113`

### 2.2 เทคโนโลยีที่ใช้ (Tech Stack)

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

### 2.3 เหตุผลของการออกแบบ

**ทำไมต้องมี Nginx อยู่หน้าสุด** — browser เห็นทุกอย่างเป็น origin เดียว (`http://<PC1>`)
จึงไม่ต้องตั้งค่า CORS และ session cookie ทำงานได้ตามปกติ ทั้งที่หน้าเว็บกับ API อยู่คนละเครื่อง
Nginx แยกเส้นทางดังนี้

| เส้นทาง | ส่งไปที่ |
|---|---|
| `/` | ไฟล์ static บน PC1 เอง |
| `/api/` | Flask ที่ PC2 (ตั้ง timeout 600 วินาที เพราะการสร้างภาพใช้เวลานาน) |
| `/media/` | Flask ที่ PC2 ซึ่งไปขอไฟล์ภาพจาก PC4 มาส่งต่อ |

**ทำไม Frontend เป็น static ล้วน** — เดิมหน้าเว็บ render ด้วย Jinja ในโปรเซสเดียวกับ Flask
เมื่อแยกเครื่องจึงเปลี่ยนเป็น HTML static ที่ดึงข้อมูลทุกอย่างผ่าน `fetch()` ไปยัง JSON API
ทำให้ PC1 ไม่ต้องมี Python เลย

**ทำไมฐานข้อมูลเป็น SQLite ที่ครอบด้วย HTTP** — โจทย์ต้องการให้ฐานข้อมูลอยู่คนละเครื่องกับ Backend
แต่ SQLite เป็น "ไฟล์" ไม่มีโปรโตคอลเครือข่าย และการแชร์ไฟล์ `.db` ผ่าน network drive
เสี่ยงไฟล์เสียหายเพราะ file locking ข้ามเครือข่ายไม่น่าเชื่อถือ
จึงเขียนบริการเล็ก ๆ (`db_server.py`) ให้ PC4 เป็นเจ้าของไฟล์ `.db` แต่ผู้เดียว
แล้วให้ PC2 ส่งคำสั่ง SQL มาทาง HTTP ฝั่ง PC2 มี `db_client.py` ที่ทำหน้าตาเหมือนโมดูล `sqlite3`
เดิม (`conn.execute(...).fetchone()`) โค้ดส่วน API จึงแทบไม่ต้องแก้
แนวทางนี้ต่างจากตัวอย่าง 4 เครื่องในโจทย์ที่ใช้ PostgreSQL — ข้อดีคือไม่ต้องติดตั้งระบบฐานข้อมูลเพิ่ม
ข้อเสียอยู่ในหัวข้อ 9

**ทำไมไฟล์ภาพอยู่ที่ PC4** — ภาพกับ record ในฐานข้อมูลต้องไปด้วยกันเสมอ
เก็บไว้เครื่องเดียวกันทำให้สำรองข้อมูลครั้งเดียวได้ครบ และ PC2 ไม่มี state ค้างอยู่ในเครื่อง

**ทำไมแก้ไขภาพที่ PC2 ไม่ใช่ PC3** — การแก้ไขภาพด้วย OpenCV เป็นงาน CPU เบา ๆ ไม่ต้องใช้ GPU
และยังใช้งานได้แม้ AI Server ปิดอยู่

### 2.4 ลำดับการทำงาน: สร้างภาพ

1. ผู้ใช้กรอก prompt และค่าต่าง ๆ แล้วกด "สร้างภาพ" — browser ส่ง `POST /api/generate` ไปที่ PC1
2. Nginx ส่งต่อให้ PC2
3. PC2 ตรวจการล็อกอิน ตรวจและจำกัดช่วงค่าพารามิเตอร์ แล้วตรวจการจำกัดความถี่ (cooldown)
4. PC2 ส่ง `POST /sdapi/v1/txt2img` ไป PC3 และรอผล (สูงสุด 300 วินาที)
5. PC3 สร้างภาพ ส่งกลับเป็น base64 พร้อม seed ที่ใช้จริง
6. PC2 ส่งไฟล์ภาพไปเก็บที่ PC4 (`PUT /files/outputs/...`) แล้วบันทึก record (`POST /sql`)
7. PC2 ตอบ URL ของภาพ (`/media/outputs/...`) กลับไปให้ browser
8. browser ขอภาพผ่าน PC1 → PC2 → PC4

### 2.5 ลำดับการทำงาน: แก้ไขภาพ

1. ผู้ใช้เลือกภาพต้นฉบับ (อัปโหลดเอง หรือเลือกจากภาพที่เคยสร้าง) และเลือกฟังก์ชัน
2. browser ส่ง `POST /api/edit` แบบ multipart ผ่าน PC1 ไป PC2
3. PC2 อ่านภาพ (ถ้าเลือกจากประวัติ จะขอไฟล์จาก PC4) แล้วประมวลผลด้วย OpenCV บนเครื่องตัวเอง
4. PC2 เก็บผลลัพธ์เป็น PNG ที่ PC4 และบันทึก record ลงตาราง `edits`

---

## 3. รายละเอียดแต่ละส่วน

### 3.1 PC1 — Frontend และ Nginx

หน้าเว็บมี 4 หน้า เขียนด้วย HTML/CSS/JavaScript ล้วน (ไม่ใช้ framework และไม่ได้ใช้ Bootstrap
— ใช้ CSS ที่เขียนเองใน `css/style.css`)

| หน้า | หน้าที่ |
|---|---|
| `login.html`, `register.html` | เข้าสู่ระบบ / สมัครสมาชิก |
| `index.html` | แท็บ "สร้างภาพ" และแท็บ "แก้ไขภาพ" พร้อมประวัติของผู้ใช้ |
| `admin.html` | ผู้ดูแลดูภาพของผู้ใช้ทุกคน ค้นหาตาม username/prompt และลบรายการ |

JavaScript แบ่งเป็น `config.js` (ที่อยู่ API), `common.js` (เรียก API, ตรวจการล็อกอิน, แถบเมนู),
`auth.js`, `main.js`, `admin.js` เนื่องจากหน้าเว็บเป็น static การตรวจสิทธิ์จึงทำโดยเรียก
`GET /api/me` ตอนโหลดหน้า ถ้าได้ 401 จะพาไปหน้า login

ในแท็บสร้างภาพ เมื่อผู้ใช้เลือก checkpoint ระบบจะตั้ง sampler, ขนาดภาพ, steps และ CFG scale
ให้ตาม preset ของ checkpoint นั้นโดยอัตโนมัติ

### 3.2 PC2 — Backend (Flask)

เป็น JSON API ล้วน ไม่ render HTML

| Method | Path | หน้าที่ | สิทธิ์ |
|---|---|---|---|
| POST | `/api/register` | สมัครสมาชิก (คนแรกของระบบได้เป็น admin) | ทุกคน |
| POST | `/api/login` | เข้าสู่ระบบ ได้ session cookie | ทุกคน |
| POST | `/api/logout` | ออกจากระบบ | ล็อกอิน |
| GET | `/api/me` | ข้อมูลผู้ใช้ปัจจุบัน | ล็อกอิน |
| GET | `/api/history` | ประวัติสร้างภาพและแก้ไขภาพของตัวเอง | ล็อกอิน |
| GET | `/api/samplers` | รายชื่อ sampler จาก PC3 | ล็อกอิน |
| GET | `/api/checkpoints` | รายชื่อโมเดลจาก PC3 กรองตาม allow-list | ล็อกอิน |
| POST | `/api/generate` | สร้างภาพ | ล็อกอิน |
| POST | `/api/edit` | แก้ไขภาพ | ล็อกอิน |
| POST | `/api/edit/delete/<id>` | ลบรายการแก้ไขของตัวเอง | เจ้าของ |
| GET | `/api/admin/records` | ดูภาพของผู้ใช้ทุกคน | admin |
| POST | `/api/admin/delete/<id>` | ลบรายการสร้างภาพ | admin |
| GET | `/api/health` | สถานะการเชื่อมต่อ PC3 / PC4 | ทุกคน |
| GET | `/media/<path>` | ส่งต่อไฟล์ภาพจาก PC4 | ล็อกอิน |

**ระบบสมาชิก** — ใช้ Flask-Login เก็บ session ใน cookie ที่เซ็นด้วย `SECRET_KEY`
รหัสผ่านเก็บเป็น hash (`werkzeug.security.generate_password_hash`) ไม่เก็บรหัสผ่านจริง

**การตรวจค่าพารามิเตอร์** — `/api/generate` จำกัด steps 1–50, CFG 1–30, ขนาดภาพ 64–1024
เพื่อกันค่าที่ทำให้ AI Server ค้างนาน

**การทนต่อความผิดพลาด** — ถ้าต่อ PC3 ไม่ได้ `/api/samplers` จะใช้รายชื่อสำรอง,
`/api/checkpoints` คืนรายการว่าง, `/api/generate` ตอบ 502 พร้อมข้อความ
ถ้าต่อ PC4 ไม่ได้จะตอบ 503 พร้อมข้อความที่อ่านเข้าใจ แท็บแก้ไขภาพยังใช้ได้แม้ PC3 ปิดอยู่

**การจำกัดความถี่** — ผู้ใช้แต่ละคนสั่งสร้างภาพได้ 1 ครั้งต่อ `GENERATE_COOLDOWN_SECONDS`
(ค่าเริ่มต้น 3 วินาที) เกินจะได้ HTTP 429

**Logging** — เขียนลง `pc2-backend/logs/app.log` แบบหมุนไฟล์ (ไฟล์ละประมาณ 1 MB เก็บย้อนหลัง 3 ไฟล์)
บันทึกการสมัครสมาชิก, ล็อกอินสำเร็จ/ไม่สำเร็จ, ออกจากระบบ, การสร้างภาพ (พร้อมเวลาที่ใช้),
การถูกจำกัดความถี่, การแก้ไขภาพ, การลบ และความผิดพลาดในการต่อ PC3/PC4
ไม่บันทึกรหัสผ่านและ prompt ตัวอย่าง:

```
2026-10-12 23:03:42 [INFO] New user registered: smoke (id=1) — first user, promoted to admin
2026-10-12 23:03:42 [WARNING] Login failed for username: smoke
2026-10-12 23:03:42 [INFO] Generation created: id=1 user=smoke checkpoint=fake-model seed=1234 size=512x512 steps=20 took=0.0s
2026-10-12 23:03:42 [WARNING] Generate rate-limited: user=smoke
```

### 3.3 PC3 — AI Server

ไม่มีโค้ดของโครงงานบนเครื่องนี้ ใช้ Stable Diffusion Forge (ผ่าน Stability Matrix)
เปิดด้วย Launch Options 3 ตัว

| Flag | เหตุผล |
|---|---|
| `--api` | เปิด REST API (`/sdapi/v1/...`) |
| `--api-auth user:pass` | ต้องมีรหัสผ่านจึงเรียก API ได้ |
| `--listen` | ให้เครื่องอื่นในวง LAN เข้าถึงได้ (ไม่ใส่ = รับเฉพาะ 127.0.0.1) |

Backend เรียกใช้ 3 endpoint: `GET /sdapi/v1/samplers`, `GET /sdapi/v1/sd-models`,
`POST /sdapi/v1/txt2img` และอนุญาตเฉพาะ checkpoint ใน allow-list (`ALLOWED_CHECKPOINTS`)
ซึ่งปัจจุบันมี 2 โมเดล คือ `realSimpleAnime` และ `realismIllustriousBy`
การสลับโมเดลทำผ่าน `override_settings` ในคำขอสร้างภาพ

### 3.4 PC4 — Database Server

| Method | Path | หน้าที่ |
|---|---|---|
| POST | `/sql` | รัน SQL หนึ่งคำสั่ง (commit อัตโนมัติ) |
| POST | `/sql/batch` | รันหลายคำสั่งใน transaction เดียว |
| PUT / GET / DELETE | `/files/outputs/...` | เก็บ / ขอ / ลบไฟล์ภาพ |
| GET | `/health` | ตรวจสถานะ |

การป้องกัน: ทุก request (ยกเว้น `/health`) ต้องมาจาก IP ของ PC2 และมี header `X-DB-Token` ที่ถูกต้อง
ไฟล์ภาพรับเฉพาะ path ใต้ `outputs/` และใช้ `safe_join` กันการหลุดออกนอกโฟลเดอร์
การเขียนฐานข้อมูลถูกจัดคิวด้วย lock เพราะ SQLite เขียนพร้อมกันหลาย thread ไม่ได้

โครงสร้างฐานข้อมูล:

| ตาราง | คอลัมน์สำคัญ |
|---|---|
| `users` | `id`, `username` (ไม่ซ้ำ), `password_hash`, `is_admin`, `created_at` |
| `generations` | `id`, `user_id`, `prompt`, `negative_prompt`, `steps`, `cfg_scale`, `width`, `height`, `sampler`, `seed`, `checkpoint`, `image_path`, `created_at` |
| `edits` | `id`, `user_id`, `source_label`, `operation`, `params` (JSON), `result_image`, `created_at` |

`generations.user_id` และ `edits.user_id` อ้างถึง `users.id` และมี index ตาม `(user_id, id)`
สำหรับการดึงประวัติ

---

## 4. ฟังก์ชันแก้ไขภาพ (Digital Image Processing)

อยู่ในไฟล์ `pc2-backend/image_ops.py` แบ่งเป็น 4 กลุ่ม รวม 12 วิธี
โดยให้ *r* เป็นค่าความเข้มเดิมของพิกเซล (0–255) และ *s* เป็นค่าใหม่

### 4.1 Point Operation — ค่าใหม่ขึ้นกับค่าเดิมของพิกเซลนั้นเท่านั้น

คำนวณตาราง mapping (LUT) ของค่า 0–255 ไว้ครั้งเดียว แล้วใช้กับทั้ง 3 ช่องสี

| วิธี | สูตร | ผล |
|---|---|---|
| Negative | s = 255 − r | กลับสี ขาว↔ดำ |
| Log | s = c · log(1 + r), c = 255 / log(256) | ยืดช่วงมืด บีบช่วงสว่าง |
| Contrast stretching | เส้นตรงหลายช่วงผ่าน (0,0) → (r1,s1) → (r2,s2) → (255,255) | ยืด contrast ของช่วงที่เลือก |

### 4.2 Auto Contrast — ปรับจาก histogram

ทำบนช่องความสว่าง Y ของระบบสี YCrCb แล้วใส่สีเดิมกลับ
เพราะถ้าทำแยกทีละช่อง B, G, R สัดส่วนสีจะเปลี่ยนและภาพสีเพี้ยน

| วิธี | หลักการ |
|---|---|
| Automatic contrast adjustment | หาค่าต่ำสุด a_low และสูงสุด a_high แล้วยืดให้เต็ม 0–255: s = (r − a_low) × 255 / (a_high − a_low) โดยตัดหัวท้าย histogram ทิ้งฝั่งละ *clip* % (0–10) เพื่อกันจุด noise |
| Histogram Equalization | s = ⌊CDF(r) × 255 / จำนวนพิกเซล⌋ ทำให้ histogram กระจายเต็มช่วง |

### 4.3 Linear Filter — คูณน้ำหนัก kernel แล้วบวกรวม

| วิธี | kernel | ผล |
|---|---|---|
| Mean (Box) | ทุกช่องเท่ากับ 1/(k×k) | เบลอ ลด noise (low-pass) |
| Gaussian | น้ำหนักตามระยะจากกลาง กำหนดด้วย σ | เบลอนุ่มกว่า Mean |
| Laplacian | 4 ทิศ `[0 1 0 / 1 −4 1 / 0 1 0]` หรือ 8 ทิศ `[1 1 1 / 1 −8 1 / 1 1 1]` | หาขอบ (high-pass) แสดงผลเป็นค่าสัมบูรณ์บนภาพเทา |

### 4.4 Non-linear Filter — เลือกค่าจากหน้าต่าง k×k

| วิธี | เลือก | ผล |
|---|---|---|
| Median | ค่ากลาง | ลบ salt & pepper noise ได้ดี |
| Mean | ค่าเฉลี่ย (ใส่ไว้เพื่อเทียบกับ Median) | noise กลายเป็นรอยจาง ภาพเบลอ |
| Min | ค่าน้อยสุด | ลบจุดขาว ส่วนมืดขยาย |
| Max | ค่ามากสุด | ลบจุดดำ ส่วนสว่างขยาย |

ขนาด kernel เป็นเลขคี่ 3–31 และขอบภาพเติมด้วยการคัดลอกพิกเซลขอบ (replicate)
ค่าที่ผู้ใช้ส่งมานอกช่วงจะถูกปรับเข้าช่วง ส่วนค่าที่ไม่ใช่ตัวเลขหรือไม่สมเหตุผล
(เช่น r1 ≥ r2) จะตอบ HTTP 400 พร้อมข้อความ

---

## 5. ความปลอดภัย

| ประเด็น | สิ่งที่ทำ |
|---|---|
| รหัสผ่านผู้ใช้ | เก็บเป็น hash |
| ค่าลับของระบบ | `SECRET_KEY`, รหัสผ่าน Forge, `DB_TOKEN` อ่านจากไฟล์ `.env` ซึ่งไม่อยู่ใน git — PC2 และ PC4 ไม่ยอมเปิดถ้าไม่ได้ตั้ง `DB_TOKEN` |
| Debug mode | ปิดเป็นค่าเริ่มต้น เปิดได้ด้วย `FLASK_DEBUG=true` เฉพาะตอนพัฒนา |
| XSS | ข้อความจากผู้ใช้ (เช่น prompt) ผ่าน `escapeHtml()` ซึ่งแปลง `& < > " '` ก่อนแสดงผลทุกจุด |
| การเข้าถึงภาพ | `/media/` ต้องล็อกอิน |
| สิทธิ์ admin | ตรวจที่ Backend ทุกครั้ง ไม่ได้อาศัยการซ่อนปุ่มในหน้าเว็บ |
| การแก้ไข/ลบข้ามผู้ใช้ | ตรวจ `user_id` ของเจ้าของก่อนเสมอ |
| ฐานข้อมูล | รับเฉพาะ IP ของ PC2 และต้องมี token |
| SQL Injection | ทุกคำสั่งใช้ parameter (`?`) ไม่ต่อ string |
| CSRF | session cookie ตั้ง `SameSite=Lax` |

ระหว่างการพัฒนาได้ตรวจทานโค้ด (code review) หลังแยกระบบเป็น 4 เครื่อง และแก้ช่องโหว่ที่พบ ได้แก่
ค่าลับที่เขียนไว้ในโค้ด, debug mode ที่เปิดค้างบน LAN, `escapeHtml()` ที่ไม่แปลงเครื่องหมายคำพูด
(ทำให้ฝัง script ผ่าน prompt ไปยังหน้า admin ได้) และ `/media/` ที่เปิดดูได้โดยไม่ล็อกอิน
ข้อที่ยังเหลืออยู่ในหัวข้อ 9

---

## 6. การทดสอบ

### 6.1 Smoke test อัตโนมัติ

`tests/smoke_test.py` เปิด Database Server ตัวจริงบนพอร์ตว่างพร้อมฐานข้อมูลชั่วคราว
แล้วเรียก Backend ตัวจริงผ่าน test client โดย **จำลอง AI Server** (ทั้งกรณีทำงานปกติและกรณีต่อไม่ได้)
จึงรันได้ทุกเครื่องโดยไม่ต้องมี GPU และไม่แตะข้อมูลจริง

```bat
pc2-backend\venv\Scripts\python.exe tests\smoke_test.py
```

ผลการรันล่าสุด (14 ต.ค. 2569): **ผ่านทั้ง 70 รายการ**

| กลุ่ม | สิ่งที่ตรวจ |
|---|---|
| Database Server | `/health`, ปฏิเสธ token ที่ผิด (401) |
| ระบบสมาชิก | สมัคร, username ซ้ำ (409), รหัสผ่านผิด (401), คนแรกเป็น admin, ออกจากระบบ |
| AI Server ต่อไม่ได้ | sampler สำรอง, checkpoint ว่าง, generate ตอบ 502, `/api/health` รายงานถูก |
| สร้างภาพ | ตรวจค่าที่ผิด (400), ได้ seed จริง, ไฟล์ถูกเก็บที่ Database Server, ประวัติถูกต้อง |
| จำกัดความถี่ | ครั้งที่ 2 ได้ 429, ผู้ใช้อื่นไม่ถูกกระทบ, คำขอที่ถูกปฏิเสธไม่ถึง AI Server |
| แก้ไขภาพ | 10 วิธีใน 4 กลุ่มตอบ 200, ค่าผิดตอบ 400, Negative ของภาพค่า 90 ได้ค่า 165 |
| สิทธิ์ | ใช้ภาพ/ลบรายการของผู้อื่นไม่ได้ (404), ผู้ใช้ทั่วไปเข้า API admin ไม่ได้ (403), ไม่ล็อกอินดูภาพไม่ได้ (401) |
| การลบ | ลบแล้วไฟล์ภาพหายจริง |
| Log | มีบรรทัดของทุกเหตุการณ์ และไม่มีรหัสผ่านใน log |

**ข้อจำกัดของการทดสอบนี้:** ไม่ครอบคลุมการสร้างภาพจริง (PC2 → PC3) และชั้น Nginx (PC1)

### 6.2 การทดสอบข้ามเครื่อง

| เครื่องมือ | ใช้ตรวจ |
|---|---|
| `pc2-backend/check-ai.bat` | PC2 ต่อไป PC3 ได้หรือไม่ และมี checkpoint อะไรบ้าง |
| `http://<PC1>/api/health` | สถานะ PC2, PC3, PC4 ในหน้าเดียว |
| `curl http://<PC4>:5100/health` | Database Server ทำงานอยู่หรือไม่ |

_(บันทึกผลการทดสอบบนเครื่องจริง 4 เครื่อง และภาพหน้าจอ ลงในส่วนนี้)_

| รายการ | ผล | หมายเหตุ |
|---|---|---|
| เปิดเว็บผ่าน Nginx จากเครื่องอื่นในวง LAN | | |
| สมัครสมาชิก / เข้าสู่ระบบ | | |
| สร้างภาพ (เวลาที่ใช้ต่อภาพ) | | |
| แก้ไขภาพครบ 4 กลุ่ม | | |
| หน้า admin | | |
| ปิด PC3 แล้วระบบยังแก้ไขภาพได้ | | |

---

## 7. การติดตั้ง การใช้งาน และการสำรองข้อมูล

**การติดตั้ง** — แต่ละเครื่องมี `setup.bat` (สร้าง virtual environment และติดตั้ง library ครั้งเดียว)
และ `start.bat` ในโฟลเดอร์ของตัวเอง เปิดตามลำดับ PC4 → PC3 → PC2 → PC1
รายละเอียดอยู่ใน `README.md` ของแต่ละโฟลเดอร์ สิ่งที่ต้องตั้งค่าเพิ่มในแต่ละเครื่องคือ
เปิดพอร์ตใน Windows Firewall, แก้ IP ในไฟล์ config และสร้างไฟล์ `.env`

**โหมด Single-PC** — `single-pc/start.bat` รันทั้งระบบบนเครื่องเดียว
Database Server ทำงานเป็น thread และ Flask เสิร์ฟหน้าเว็บแทน Nginx
Backend ยังคุยกับ Database ผ่าน HTTP เหมือนตอนแยกเครื่อง ข้อมูลแยกเก็บที่ `single-pc/data/`

**การสำรองข้อมูล** — `scripts/backup.ps1` รวม `database.db` และโฟลเดอร์ `storage/` ของ PC4
เป็นไฟล์ zip ที่มีวันเวลาในชื่อ การกู้คืนคือแตก zip กลับลงโฟลเดอร์ข้อมูล
สคริปต์จะแจ้ง error แทนการสร้าง zip เปล่าถ้าไม่พบฐานข้อมูล (รายละเอียดใน `docs/backup.md`)

**Dashboard** — หน้า `admin.html` แสดงภาพของผู้ใช้ทุกคนพร้อม prompt และค่าที่ใช้
ส่วน `/api/health` แสดงสถานะของแต่ละเครื่อง

---

## 8. การแบ่งหน้าที่

| หน้าที่ | สิ่งที่ส่งมอบตามโจทย์ | สิ่งที่ทำในโครงงาน | ผู้รับผิดชอบ |
|---|---|---|---|
| UX/UI Frontend | หน้าเว็บ, Bootstrap, JavaScript | หน้าเว็บ static 4 หน้า, JavaScript เรียก API (ใช้ CSS เขียนเองแทน Bootstrap) | PC-1 |
| Flask Backend | Authentication, API, Database, Logging | ระบบสมาชิก, JSON API 14 เส้นทาง, `db_client`, log แบบหมุนไฟล์ | PC-2, PC-4 |
| AI Engineer | Image Generation, Image Editing, Model/LoRA, ทดสอบ API, Queue | สร้างภาพผ่าน Forge, แก้ไขภาพ 12 วิธี, เลือกโมเดลได้ 2 ตัว, `check-ai` (ยังไม่มี LoRA และ Queue) | PC-3|
| QA / DevOps | ทดสอบระบบ, เขียนคู่มือ, Deployment, Dashboard, Backup | smoke test, README ทุกเครื่อง, `setup.bat`/`start.bat`, หน้า admin + health, สคริปต์ backup | PC-2 |
| Reverse Proxy, Routing | — | config ของ Nginx, Database Server บน PC4 | PC-1, PC-4 |

---

## 9. ข้อจำกัดและงานที่ยังไม่ได้ทำ

| ประเด็น | รายละเอียด |
|---|---|
| ไม่มี Queue | คำขอสร้างภาพพร้อมกันหลายคนจะจอง thread ของ Flask คนละตัวและรอ Forge ทำทีละงาน ถ้าใช้ checkpoint ต่างกัน Forge จะสลับโมเดลไปมา การจำกัดความถี่ช่วยได้เพียงบางส่วน |
| ไม่มี LoRA | รองรับเฉพาะการเลือก checkpoint |
| ภาพของผู้ใช้อื่น | ผู้ใช้ที่ล็อกอินแล้วยังเปิดภาพของคนอื่นได้ถ้าเดาชื่อไฟล์ถูก ยังไม่มีการตรวจความเป็นเจ้าของที่ `/media/` |
| Allow-list ของ checkpoint | บังคับเฉพาะใน dropdown ฝั่ง Backend ยังไม่ตรวจค่า `checkpoint` ที่ส่งมา |
| Database Server | `/sql` รันคำสั่ง SQL ใดก็ได้จากผู้ที่มี token ความปลอดภัยของ PC4 จึงขึ้นกับ token และรายการ IP เท่านั้น |
| ไม่มี HTTPS | ข้อมูลระหว่างเครื่อง (รวมรหัสผ่านตอนล็อกอินและ token) ส่งเป็นข้อความธรรมดาในวง LAN |
| ค่าลับเดิมใน git | รหัสผ่าน Forge และ token ชุดเดิมยังอยู่ในประวัติ git ต้องเปลี่ยนเป็นค่าใหม่ |
| การล็อกอิน | ยังไม่จำกัดจำนวนครั้งที่ลองรหัสผ่าน และรหัสผ่านสั้นสุด 4 ตัวอักษร |
| ความสอดคล้องของข้อมูล | ไฟล์ภาพถูกเก็บก่อนบันทึก record ถ้าบันทึกไม่สำเร็จไฟล์จะค้าง และการสมัคร username เดียวกันพร้อมกันจะได้ 503 แทน 409 |
| IP แบบ DHCP | IP เปลี่ยนต้องแก้ไฟล์ config หลายจุด |
| การสำรองข้อมูล | ยังต้องสั่งเอง ไม่มีการตั้งเวลา และไฟล์สำรองอยู่บนดิสก์เดียวกับข้อมูล |
| การทดสอบ | ยังไม่มีการทดสอบอัตโนมัติของหน้าเว็บ, Nginx และการสร้างภาพจริง |

---

## 10. สรุป

โครงงานนี้สร้างเว็บสร้างและแก้ไขภาพที่ทำงานเป็น Distributed System 4 เครื่องตามโจทย์
โดย Nginx เป็นทางเข้าเดียว Frontend เป็น static แยกจาก Backend อย่างสมบูรณ์
Backend เป็น JSON API ที่ไม่เก็บ state ไว้ในเครื่อง AI Server และ Database อยู่หลัง Backend
และไม่เปิดให้ browser เข้าถึงโดยตรง ทุกเครื่องสื่อสารกันด้วย HTTP บน LAN

สิ่งที่ได้เรียนรู้ที่สำคัญ ได้แก่ การใช้ Reverse Proxy เพื่อรวมหลายบริการให้เป็น origin เดียว,
การแยกฐานข้อมูลแบบไฟล์ออกไปอีกเครื่องโดยครอบด้วยบริการ HTTP, การออกแบบให้ระบบยังทำงานบางส่วนได้
เมื่อเครื่องใดเครื่องหนึ่งล่ม และการจัดการค่าลับกับการตรวจสิทธิ์เมื่อบริการกระจายอยู่หลายเครื่อง

งานที่ควรทำต่อเป็นลำดับแรกคือ ระบบ Queue สำหรับการสร้างภาพ, การตรวจความเป็นเจ้าของภาพ,
การตรวจ checkpoint ฝั่ง Backend และการเปลี่ยนค่าลับชุดเดิม

---

## ภาคผนวก — โครงสร้างโฟลเดอร์

```
ImageProject/
├─ pc1-frontend/      หน้าเว็บ static + config ของ Nginx + start/stop-nginx.bat
├─ pc2-backend/       app.py (API), image_ops.py (แก้ไขภาพ), db_client.py, config.py
├─ pc3-ai/            README วิธีตั้งค่า Forge
├─ pc4-database/      db_server.py, schema.py
├─ single-pc/         run_single_pc.py — รันทั้งระบบบนเครื่องเดียว
├─ tests/             smoke_test.py
├─ scripts/           backup.ps1, backup.sh
└─ docs/              REPORT.md (ไฟล์นี้), backup.md, PROGRESS.md
```
