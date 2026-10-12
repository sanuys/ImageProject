# ImageProject — Distributed System (4 เครื่อง)

ระบบสร้างภาพด้วย AI + แก้ไขภาพ (Image Processing) แยกการทำงานออกเป็น 4 เครื่อง
ตามหลัก Distributed System — แต่ละเครื่องทำหน้าที่ต่างกัน เชื่อมกันผ่าน LAN

## ผังระบบ

```
                        Browser (User)
                              |
                              v
        ┌─────────────────────────────────────────┐
        │  PC1  10.187.226.36   Nginx + Frontend   │   Presentation Tier
        │  เสิร์ฟ HTML/CSS/JS + Reverse Proxy      │
        └───────┬───────────────────────┬─────────┘
                │ /api/                 │ /media/
                v                       v
        ┌─────────────────────────────────────────┐
        │  PC2  10.187.226.226   Backend (Flask)    │   Logic Tier
        │  JSON API + OpenCV + เก็บไฟล์ภาพ         │
        └───────┬───────────────────────┬─────────┘
                │ HTTP                  │ HTTP
                v                       v
   ┌──────────────────────┐   ┌──────────────────────────┐
   │ PC3  10.187.226.10    │   │ PC4  10.187.226.35        │
   │ AI Server (Forge)    │   │ Database (SQLite)        │   Data Tier
   │ :7860                │   │ :5100                    │
   └──────────────────────┘   └──────────────────────────┘
```

## หน้าที่ของแต่ละเครื่อง

| เครื่อง | IP | พอร์ต | หน้าที่ | โฟลเดอร์ |
|---|---|---|---|---|
| PC1 | 10.187.226.36 | 80 | Nginx เสิร์ฟหน้าเว็บ + เป็นประตูทางเข้าเดียวของระบบ | `pc1-frontend/` |
| PC2 | 10.187.226.226 | 5000 | Flask API, แก้ไขภาพด้วย OpenCV, เก็บไฟล์ภาพ | `pc2-backend/` |
| PC3 | 10.187.226.10 | 7860 | Stable Diffusion Forge (ใช้ GPU สร้างภาพ) | `pc3-ai/` |
| PC4 | 10.187.226.35 | 5100 | ฐานข้อมูล SQLite เปิดเป็น service ให้ PC2 เรียก | `pc4-database/` |

> **⚠️ IP ชุดนี้ได้มาจาก DHCP ของเน็ต CDTI_STUDENT** ไม่ใช่ Static IP
> ถ้าเครื่องไหนปิด-เปิดใหม่ หรือหลุดจาก Wi-Fi แล้วต่อกลับมา IP อาจเปลี่ยน แล้วระบบจะพังทันที
> เช็ค IP ปัจจุบันได้ด้วย `ipconfig` ในแต่ละเครื่อง แล้วแก้ 3 จุดนี้ให้ตรง:
> `pc1-frontend/nginx/imageproject.conf` (upstream) · `pc2-backend/config.py` (2 บรรทัด) · `pc4-database/db_server.py` (ALLOWED_CLIENT_IPS)
>
> ถ้าทำได้ แนะนำให้จอง IP ที่เราเตอร์ (DHCP Reservation) หรือใช้เราเตอร์ส่วนตัวแล้วตั้ง Static IP เอง

> โฟลเดอร์ `webapp/` คือโค้ดเวอร์ชันเดิมที่รันเครื่องเดียว — เก็บไว้เป็นต้นฉบับอ้างอิง ไม่ได้ใช้แล้ว

> **อยากลองรันทั้งระบบบนเครื่องเดียว** ใช้โฟลเดอร์ `single-pc/` — ดับเบิลคลิก `setup.bat` แล้ว `start.bat`
> ใช้โค้ดชุดเดียวกับ 4 เครื่อง แค่ชี้ทุกส่วนมาที่ 127.0.0.1 (รายละเอียดใน `single-pc/README.md`)

## เส้นทางของ 1 request (ตัวอย่าง: กดปุ่ม "สร้างภาพ")

1. Browser ยิง `POST http://10.187.226.36/api/generate`
2. **PC1** Nginx เห็นว่าขึ้นต้นด้วย `/api/` จึง proxy ต่อไป `10.187.226.226:5000`
3. **PC2** เช็ค session ว่าล็อกอินอยู่ไหม → ยิง `POST /sdapi/v1/txt2img` ไปที่ **PC3**
4. **PC3** ใช้ GPU สร้างภาพ แล้วส่ง base64 กลับมา
5. **PC2** เซฟไฟล์ PNG ลงดิสก์ตัวเอง แล้วยิง `INSERT` ไปเก็บ record ที่ **PC4**
6. **PC2** ตอบ JSON `{image_url: "/media/outputs/xxx.png"}` กลับไป
7. Browser โหลดภาพจาก `http://10.187.226.36/media/outputs/xxx.png`
   → **PC1** proxy ไปดึงไฟล์จริงจาก **PC2**

## สิ่งที่เปลี่ยนจากเวอร์ชันเครื่องเดียว

| เดิม (1 เครื่อง) | ใหม่ (4 เครื่อง) |
|---|---|
| Flask render Jinja template | HTML/CSS/JS เป็น static อยู่ที่ PC1, Flask ตอบ JSON อย่างเดียว |
| `@login_required` แล้ว redirect ไปหน้า login | ตอบ JSON 401, ฝั่ง JS เด้งไป `login.html` เอง |
| ประวัติภาพถูกใส่มากับ HTML ตอน render | ดึงผ่าน `GET /api/history` |
| `flash()` ของ Flask | `showFlash()` / `sessionStorage` ใน `common.js` |
| `sqlite3.connect("database.db")` ในเครื่องเดียวกัน | `db_client.py` ยิง HTTP ไปหา DB Server ที่ PC4 |
| ภาพอยู่ใต้ `static/outputs/` | อยู่ที่ `pc2-backend/storage/outputs/` เสิร์ฟผ่าน `/media/` |
| form POST ธรรมดา (สมัคร/เข้าสู่ระบบ/ลบ) | fetch + JSON ทั้งหมด |

**หมายเหตุเรื่อง SQLite:** SQLite เป็นไฟล์ ไม่มีโปรโตคอลเครือข่ายในตัว จะแชร์ไฟล์ `.db`
ผ่าน network drive ไม่ได้ (ไฟล์พัง) จึงต้องครอบด้วย `db_server.py` เปิดเป็น HTTP service
ที่ PC4 แทน — PC2 ไม่เคยแตะไฟล์ `.db` โดยตรงเลย

## ติดตั้ง library (ทำครั้งเดียวต่อเครื่อง)

แต่ละเครื่องก๊อปเฉพาะโฟลเดอร์ของตัวเองไป แล้ว**ดับเบิลคลิก `setup.bat`** ในโฟลเดอร์นั้น
สคริปต์จะสร้าง virtual environment และลง library ให้เอง ไม่ต้องพิมพ์ pip เอง

| เครื่อง | ไฟล์ติดตั้ง | ลงอะไร |
|---|---|---|
| PC1 | ไม่มี | ไม่ใช้ Python — ติดตั้งแค่ Nginx |
| PC2 | `pc2-backend/setup.bat` | Flask, Flask-Login, requests, opencv, numpy |
| PC3 | ไม่มี | ไม่ต้องลงอะไร — Forge จัดการ Python ของตัวเอง |
| PC4 | `pc4-database/setup.bat` | Flask (sqlite3 มากับ Python อยู่แล้ว) |

แต่ละ `requirements.txt` มีคอมเมนต์บอกไว้ว่า library แต่ละตัวใช้ทำอะไร

## ลำดับการสตาร์ทระบบ (สำคัญ — ต้องเรียงตามนี้)

| ลำดับ | เครื่อง | ดับเบิลคลิกไฟล์นี้ |
|---|---|---|
| 1 | PC4 Database | `pc4-database/start.bat` |
| 2 | PC3 AI Server | เปิด Stability Matrix แล้วกด Launch ที่ Forge |
| 3 | PC2 Backend | `pc2-backend/start.bat` |
| 4 | PC1 Nginx | `pc1-frontend/start-nginx.bat` |

ปิด Nginx ด้วย `pc1-frontend/stop-nginx.bat` ส่วนเซิร์ฟเวอร์ Python ปิดด้วย Ctrl+C ในหน้าต่างนั้น
ตรวจว่า PC2 ยิงไปหา PC3 ได้ไหมด้วย `pc2-backend/check-ai.bat`

จากนั้นเปิด `http://10.187.226.36` ในเบราว์เซอร์

## ตรวจสอบว่าทุกเครื่องเชื่อมกันแล้ว

เปิด **`http://10.187.226.36/api/health`** — ถ้าทุกอย่างถูกต้องจะได้ประมาณนี้:

```json
{
  "backend":       { "status": "ok" },
  "database_pc4":  { "status": "ok", "users": 3, "generations": 12 },
  "ai_server_pc3": { "status": "ok", "models": 2 }
}
```

หน้านี้คือจุดแรกที่ควรดูทุกครั้งที่ระบบมีปัญหา — จะบอกทันทีว่าเครื่องไหนหลุด

## Checklist ก่อนรันจริง

- [ ] ตั้ง **Static IP** ทั้ง 4 เครื่อง ให้อยู่วง subnet เดียวกัน
- [ ] `ping` หากันได้ครบทุกเครื่อง
- [ ] เปิด Firewall ขาเข้า: PC1 พอร์ต 80, PC2 พอร์ต 5000, PC3 พอร์ต 7860, PC4 พอร์ต 5100
- [ ] `DB_TOKEN` ใน `pc2-backend/config.py` = ใน `pc4-database/db_server.py`
- [ ] `FORGE_API_USER/PASS` ใน `pc2-backend/config.py` = `--api-auth` ของ Forge
- [ ] Forge ตั้ง `--listen` แล้ว (ไม่งั้น PC2 ยิงเข้าไม่ได้)
- [ ] แก้ `root` ใน `imageproject.conf` ให้ตรง path จริงบน PC1 (2 จุด)
- [ ] เปลี่ยน `SECRET_KEY` ใน `pc2-backend/config.py`

## ย้ายข้อมูลเดิม (ถ้าจะเก็บของเก่าไว้)

| ของเดิม | ย้ายไปที่ |
|---|---|
| `webapp/database.db` | `pc4-database/database.db` (เครื่อง PC4) |
| `webapp/static/outputs/` | `pc2-backend/storage/outputs/` (เครื่อง PC2) |

path ที่เก็บใน DB เป็นรูปแบบ `outputs/xxx.png` เหมือนเดิม จึงใช้ต่อได้ทันทีไม่ต้องแก้

## แก้ปัญหาที่เจอบ่อย

| อาการ | สาเหตุที่เป็นไปได้ |
|---|---|
| เปิดเว็บแล้วเด้งกลับหน้า login ตลอด | Nginx ไม่ได้ proxy `/api/` หรือ cookie ไม่ถูกส่ง — เช็คว่าเข้าผ่าน `http://10.187.226.36` ไม่ใช่เปิดไฟล์ HTML ตรง ๆ |
| dropdown checkpoint ว่าง | PC3 ไม่ได้ใส่ `--listen` / Firewall ปิด / ชื่อโมเดลไม่ตรง `ALLOWED_CHECKPOINTS` |
| ทุก API ตอบ 503 | PC4 ไม่ได้รัน หรือ `DB_TOKEN` ไม่ตรงกัน |
| กดสร้างภาพแล้ว 504 Gateway Timeout | `proxy_read_timeout` ใน Nginx สั้นเกินไป (ตั้งไว้ 600s แล้ว) |
| ภาพขึ้นเป็นกากบาท | `/media/` ไม่ได้ proxy หรือยังไม่ได้ย้ายโฟลเดอร์ `outputs` ไปที่ PC2 |
| `403 IP ไม่ได้รับอนุญาต` จาก PC4 | IP ของ PC2 ไม่ตรงกับ `ALLOWED_CLIENT_IPS` ใน `db_server.py` |
