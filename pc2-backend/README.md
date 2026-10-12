# PC2 — Backend / Flask API (10.187.226.226)

หน้าที่: **Logic Tier** — รับ request จาก Nginx (PC1), คุยกับ AI Server (PC3),
บันทึกข้อมูลลง Database Server (PC4), และเก็บ/เสิร์ฟไฟล์ภาพ

เครื่องนี้ **ไม่มี HTML/Jinja template แล้ว** ตอบเป็น JSON อย่างเดียว

## ติดตั้ง

```bat
cd pc2-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## ก่อนรัน — แก้ config.py

| ค่า | ความหมาย |
|---|---|
| `FORGE_API_URL` | IP:พอร์ต ของเครื่อง AI Server (PC3) |
| `FORGE_API_USER/PASS` | ต้องตรงกับ `--api-auth` ใน Launch Options ของ Forge |
| `DB_SERVER_URL` | IP:พอร์ต ของเครื่อง Database (PC4) |
| `DB_TOKEN` | ต้องตรงกับใน `pc4-database/db_server.py` |
| `SECRET_KEY` | เปลี่ยนเป็นข้อความสุ่มยาว ๆ ก่อนใช้งานจริง |

## รัน

```bat
python app.py
```

## ย้ายไฟล์ภาพเดิมมา (ถ้ามี)

ก๊อปทั้งโฟลเดอร์ `webapp/static/outputs` เดิม มาวางเป็น `pc2-backend/storage/outputs`
(path ที่เก็บใน DB เป็นรูปแบบ `outputs/xxx.png` เหมือนเดิม จึงใช้ต่อได้ทันที)

## API ที่เปิดให้

| Method | Path | ใช้ทำอะไร |
|---|---|---|
| POST | `/api/register` | สมัครสมาชิก |
| POST | `/api/login` | เข้าสู่ระบบ (ได้ session cookie) |
| POST | `/api/logout` | ออกจากระบบ |
| GET | `/api/me` | เช็คว่าล็อกอินอยู่ไหม + เป็น admin ไหม |
| GET | `/api/history` | ประวัติสร้างภาพ + แก้ไขภาพของตัวเอง |
| GET | `/api/samplers` | รายชื่อ sampler จาก PC3 |
| GET | `/api/checkpoints` | รายชื่อ checkpoint (กรองตาม allow-list) จาก PC3 |
| POST | `/api/generate` | สร้างภาพ (ส่งต่อไป PC3) |
| POST | `/api/edit` | แก้ไขภาพด้วย OpenCV (ทำบนเครื่องนี้) |
| POST | `/api/edit/delete/<id>` | ลบรายการแก้ไขของตัวเอง |
| GET | `/api/admin/records` | (admin) ดูภาพของทุก user |
| POST | `/api/admin/delete/<id>` | (admin) ลบรายการ |
| GET | `/api/health` | เช็คสถานะการเชื่อมต่อ PC3 / PC4 |
| GET | `/media/<path>` | เสิร์ฟไฟล์ภาพที่เก็บบนเครื่องนี้ |

## สิ่งที่ต้องตั้งค่าเพิ่ม

1. **Firewall (Windows)** — เปิดพอร์ต 5000 ขาเข้า
   ```bat
   netsh advfirewall firewall add rule name="ImageProject Backend" dir=in action=allow protocol=TCP localport=5000
   ```
2. ตั้ง IP เครื่องนี้เป็น `10.187.226.226` แบบ Static
3. เวลาตรวจปัญหา ให้เปิด `http://10.187.226.226:5000/api/health` ดูก่อนเสมอ
