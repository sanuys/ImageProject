# Single PC — รันทั้งระบบบนเครื่องเดียว

ใช้ลองระบบโดยไม่ต้องมี 4 เครื่อง — Frontend, Backend, Database และ AI อยู่บนเครื่องนี้ทั้งหมด

```
Browser ──> http://127.0.0.1:5000
              ├─ หน้าเว็บ (pc1-frontend/html)   ┐
              ├─ /api/  และ /media/  (Backend)   ┘ Flask ตัวเดียว แทน Nginx
              ├──HTTP──> Database  127.0.0.1:5100  (pc4-database/db_server.py)
              └──HTTP──> Forge     127.0.0.1:7860  (เปิดเองใน Stability Matrix)
```

- **ใช้โค้ดชุดเดียวกับ 4 เครื่อง** ไม่ได้ก๊อปโค้ดมา — `run_single_pc.py` แค่เปลี่ยนที่อยู่ให้ชี้ 127.0.0.1
  แก้โค้ดใน `pc2-backend` / `pc4-database` / `pc1-frontend` แล้วโหมดนี้ได้ผลด้วยทันที
- **ไม่ต้องแก้ `config.py`** ของ 4 เครื่อง และไม่ต้องติดตั้ง Nginx
- **ข้อมูลแยกไว้ที่ `single-pc/data/`** (ฐานข้อมูล + ไฟล์ภาพ) ไม่ปนกับไฟล์ที่ใช้บน PC2 / PC4

## ติดตั้ง (ครั้งเดียว)

ดับเบิลคลิก **`setup.bat`** — สร้าง venv แล้วลง library จาก `pc2-backend/requirements.txt`

## รัน

1. เปิด Stability Matrix แล้ว Launch Forge (ต้องมี `--api` และ `--api-auth admin:cdti1234` ส่วน `--listen` ไม่จำเป็น)
2. ดับเบิลคลิก **`start.bat`** — เบราว์เซอร์จะเปิด `http://127.0.0.1:5000` ให้เอง
3. สมัครสมาชิกคนแรก จะได้เป็น admin อัตโนมัติ

ปิดระบบด้วย Ctrl+C หรือปิดหน้าต่าง · เช็คสถานะที่ `http://127.0.0.1:5000/api/health`

ถ้ายังไม่เปิด Forge ระบบก็รันได้ แค่สร้างภาพไม่ได้ (แท็บแก้ไขภาพใช้ได้ปกติ)

## ตั้งค่าเพิ่ม

แก้ด้านบนของ `run_single_pc.py`:

| ค่า | ใช้ทำอะไร |
|---|---|
| `HOST` | `"127.0.0.1"` = เปิดได้แค่เครื่องนี้ · `"0.0.0.0"` = ให้เครื่องอื่นในวง LAN เปิดได้ (ต้องเปิด Firewall พอร์ต 5000) |
| `WEB_PORT` / `DB_PORT` | เปลี่ยนพอร์ต ถ้าชนกับโปรแกรมอื่น |
| `FORGE_URL` | ถ้า Forge ไม่ได้อยู่พอร์ต 7860 |

## อยากใช้ข้อมูลเดิม

ปิดระบบก่อน แล้วก๊อป:

| ของเดิม | วางที่ |
|---|---|
| `database.db` (จาก PC4) | `single-pc/data/database.db` |
| โฟลเดอร์ `outputs` (จาก PC2 `pc2-backend/storage/outputs`) | `single-pc/data/storage/outputs` |

## ปัญหาที่เจอบ่อย

| อาการ | สาเหตุ |
|---|---|
| `เปิด Database ที่พอร์ต 5100 ไม่ได้` | เปิด `pc4-database/start.bat` ค้างไว้ หรือรัน start.bat ซ้ำ 2 หน้าต่าง |
| `Address already in use` พอร์ต 5000 | เปิด `pc2-backend/start.bat` ค้างไว้ — ปิดก่อน |
| หน้าเว็บขึ้นแต่ dropdown checkpoint ว่าง | Forge ยังไม่เปิด หรือ `--api-auth` ไม่ตรงกับ `config.py` |
