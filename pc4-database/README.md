# PC4 — Database Server (172.20.56.108)

หน้าที่: เก็บไฟล์ `database.db` (SQLite) **และไฟล์ภาพทั้งหมด** (`storage/`) แล้วเปิดบริการให้เครื่อง Backend เรียกใช้ผ่าน LAN

## ทำไมต้องมี db_server.py

SQLite เป็น "ไฟล์" ไม่ใช่ "เซิร์ฟเวอร์" — ไม่มีพอร์ตให้เครื่องอื่นต่อเข้ามา
ถ้าเอาไฟล์ .db ไปแชร์ผ่าน network drive แล้วให้ Flask เขียนข้ามเครื่อง
ไฟล์จะพัง (file locking ข้ามเครือข่ายไม่น่าเชื่อถือ)

ไฟล์ `db_server.py` จึงทำหน้าที่เป็น **Data Tier** — ครอบ SQLite ไว้แล้วเปิดเป็น HTTP API
เครื่อง Backend คุยผ่าน `POST /sql` เท่านั้น ไม่แตะไฟล์ .db โดยตรง

```
Backend (172.20.56.107)  --HTTP + X-DB-Token-->  DB Server (172.20.56.108:5100)  --> database.db
```

## ติดตั้ง

```bat
cd pc4-database
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## ย้ายข้อมูลเดิมมา (ถ้ามี)

ก๊อปไฟล์ `webapp/database.db` ของเดิมมาวางไว้ในโฟลเดอร์นี้ ตั้งชื่อว่า `database.db`
ตารางจะถูก migrate ให้อัตโนมัติตอนสตาร์ท ถ้าไม่มีไฟล์ ระบบจะสร้างใหม่ให้เอง

## รัน

```bat
python db_server.py
```

ต้องเห็นข้อความ `เปิดรับ : http://0.0.0.0:5100`

## ที่เก็บไฟล์ภาพ

ภาพที่สร้าง (`storage/outputs/`) และภาพที่แก้ไข (`storage/outputs/edits/`) เก็บอยู่ที่เครื่องนี้
PC2 คุยผ่าน `/files/<path>` ด้วย token และ IP แบบเดียวกับ `/sql`

| Method | Path | ใช้ทำอะไร |
|---|---|---|
| PUT | `/files/outputs/xxx.png` | PC2 ส่งไฟล์มาเก็บ (body = byte ของไฟล์) |
| GET | `/files/outputs/xxx.png` | PC2 ขอไฟล์ไปส่งต่อให้ browser |
| DELETE | `/files/outputs/xxx.png` | PC2 สั่งลบไฟล์ |

รับเฉพาะ path ที่ขึ้นต้นด้วย `outputs/` (กันไม่ให้เขียนทับ `database.db`) และหน้าต่างของเครื่องนี้
จะแสดงบรรทัด `[FILE] เก็บ ...` / `[FILE] ลบ ...` ทุกครั้ง

ถ้ามีภาพเก่าอยู่ที่ PC2 (`pc2-backend/storage/outputs`) ให้ก๊อปมาไว้ที่ `pc4-database/storage/outputs`
path ในฐานข้อมูลเป็น `outputs/xxx.png` เหมือนเดิม จึงใช้ต่อได้ทันที

## ตรวจสอบ

จากเครื่องนี้เอง:  `curl http://127.0.0.1:5100/health`
จากเครื่อง Backend: `curl http://172.20.56.108:5100/health`

## สิ่งที่ต้องตั้งค่าเพิ่ม

1. **Firewall (Windows)** — เปิดพอร์ต 5100 ขาเข้า
   ```bat
   netsh advfirewall firewall add rule name="ImageProject DB" dir=in action=allow protocol=TCP localport=5100
   ```
2. **ตั้ง IP เครื่องนี้เป็น 172.20.56.108 แบบ Static**
3. **คัดลอก `.env.example` เป็น `.env` แล้วตั้ง `DB_TOKEN` ให้ตรงกับใน `pc2-backend/.env`** (ไม่ตั้ง = โปรแกรมไม่ยอมเปิด)
4. ถ้า IP เครื่อง Backend ไม่ใช่ 172.20.56.107 ให้แก้ `ALLOWED_CLIENT_IPS` ด้วย
