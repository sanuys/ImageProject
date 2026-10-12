# PC4 — Database Server (10.187.226.35)

หน้าที่: เก็บไฟล์ `database.db` (SQLite) และเปิดบริการให้เครื่อง Backend เรียกใช้ผ่าน LAN

## ทำไมต้องมี db_server.py

SQLite เป็น "ไฟล์" ไม่ใช่ "เซิร์ฟเวอร์" — ไม่มีพอร์ตให้เครื่องอื่นต่อเข้ามา
ถ้าเอาไฟล์ .db ไปแชร์ผ่าน network drive แล้วให้ Flask เขียนข้ามเครื่อง
ไฟล์จะพัง (file locking ข้ามเครือข่ายไม่น่าเชื่อถือ)

ไฟล์ `db_server.py` จึงทำหน้าที่เป็น **Data Tier** — ครอบ SQLite ไว้แล้วเปิดเป็น HTTP API
เครื่อง Backend คุยผ่าน `POST /sql` เท่านั้น ไม่แตะไฟล์ .db โดยตรง

```
Backend (10.187.226.226)  --HTTP + X-DB-Token-->  DB Server (10.187.226.35:5100)  --> database.db
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

## ตรวจสอบ

จากเครื่องนี้เอง:  `curl http://127.0.0.1:5100/health`
จากเครื่อง Backend: `curl http://10.187.226.35:5100/health`

## สิ่งที่ต้องตั้งค่าเพิ่ม

1. **Firewall (Windows)** — เปิดพอร์ต 5100 ขาเข้า
   ```bat
   netsh advfirewall firewall add rule name="ImageProject DB" dir=in action=allow protocol=TCP localport=5100
   ```
2. **ตั้ง IP เครื่องนี้เป็น 10.187.226.35 แบบ Static**
3. **`DB_TOKEN` ใน db_server.py ต้องตรงกับใน `pc2-backend/config.py`**
4. ถ้า IP เครื่อง Backend ไม่ใช่ 10.187.226.226 ให้แก้ `ALLOWED_CLIENT_IPS` ด้วย
