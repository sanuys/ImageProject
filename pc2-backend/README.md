# PC2 — Backend / Flask API (172.20.56.107)

หน้าที่: **Logic Tier** — รับ request จาก Nginx (PC1), คุยกับ AI Server (PC3),
บันทึกข้อมูลและไฟล์ภาพลง Database Server (PC4), และส่งต่อไฟล์ภาพจาก PC4 ให้ browser

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

## ไฟล์ภาพไม่ได้อยู่เครื่องนี้

ภาพที่สร้างและภาพที่แก้ไขถูกส่งไปเก็บที่ PC4 (`pc4-database/storage/`) ผ่าน `db_client.put_file()`
เครื่องนี้ไม่ต้องมีโฟลเดอร์ `storage` แล้ว ถ้ามีภาพเก่าค้างอยู่ใน `pc2-backend/storage/outputs`
ให้ย้ายไปไว้ที่ `pc4-database/storage/outputs` บนเครื่อง PC4

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
| GET | `/media/<path>` | ขอไฟล์ภาพจาก PC4 แล้วส่งต่อให้ browser |

## สิ่งที่ต้องตั้งค่าเพิ่ม

1. **Firewall (Windows)** — เปิดพอร์ต 5000 ขาเข้า
   ```bat
   netsh advfirewall firewall add rule name="ImageProject Backend" dir=in action=allow protocol=TCP localport=5000
   ```
2. ตั้ง IP เครื่องนี้เป็น `172.20.56.107` แบบ Static
3. เวลาตรวจปัญหา ให้เปิด `http://172.20.56.107:5000/api/health` ดูก่อนเสมอ
