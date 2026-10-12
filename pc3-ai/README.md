# PC3 — AI Server / Stable Diffusion Forge (10.187.226.10)

หน้าที่: รันโมเดล Stable Diffusion และเปิด API ให้เครื่อง Backend (PC2) เรียกใช้

เครื่องนี้ **ไม่ต้องติดตั้งโค้ดของโปรเจกต์เลย** — แค่เปิด Forge พร้อม API
และให้เครื่องอื่นในวง LAN เข้าถึงได้

> โฟลเดอร์นี้จึงมีแค่ไฟล์ README นี้ไฟล์เดียว ไว้บันทึกว่าต้องตั้งค่าอะไรบ้าง
> ส่วนสคริปต์ตรวจสอบย้ายไปอยู่ที่ `pc2-backend/check-ai.bat` แล้ว
> เพราะเส้นทางที่ต้องพิสูจน์จริงคือ PC2 → PC3 ไม่ใช่ PC3 → ตัวเอง

## 1. Launch Options ใน Stability Matrix / Forge

ต้องมีครบ 3 ตัวนี้:

```
--api
--api-auth admin:cdti1234
--listen
```

| Flag | ทำไมต้องมี |
|---|---|
| `--api` | เปิด REST API (`/sdapi/v1/...`) ที่ PC2 เรียกใช้ |
| `--api-auth user:pass` | ตั้งรหัสผ่าน API — ต้องตรงกับ `FORGE_API_USER/PASS` ใน `pc2-backend/config.py` |
| `--listen` | **สำคัญที่สุดตอนแยกเครื่อง** ถ้าไม่ใส่ Forge จะ bind แค่ 127.0.0.1 เครื่องอื่นยิงเข้าไม่ได้เลย |

> ตอนระบบรันเครื่องเดียว ไม่ใส่ `--listen` ก็ยังใช้ได้เพราะ Flask อยู่เครื่องเดียวกัน
> แต่พอแยกเป็น 4 เครื่องแล้ว **ไม่ใส่ = ใช้ไม่ได้**

## 2. Firewall

```bat
netsh advfirewall firewall add rule name="ImageProject Forge" dir=in action=allow protocol=TCP localport=7860
```

## 3. ตั้ง IP เครื่องนี้เป็น 10.187.226.10 แบบ Static

## 4. โมเดลที่ต้องมี

ไฟล์ checkpoint ต้องอยู่ในโฟลเดอร์ models ของ Forge และชื่อไฟล์ต้องมีคำเหล่านี้อยู่
(ตรงกับ `ALLOWED_CHECKPOINTS` ใน `pc2-backend/config.py`):

- `realSimpleAnime`
- `realismIllustriousBy`

ถ้าเปลี่ยนโมเดล ให้แก้ `match` ใน `config.py` ของ PC2 ตามด้วย

## 5. ทดสอบ

**จากเครื่องนี้เอง:**

```bat
curl -u admin:cdti1234 http://127.0.0.1:7860/sdapi/v1/sd-models
```

**จากเครื่อง Backend (PC2) — สำคัญกว่า เพราะนี่คือเส้นทางจริง:**

ไปที่เครื่อง PC2 แล้วดับเบิลคลิก `pc2-backend\check-ai.bat`

ต้องเห็นรายชื่อ checkpoint ขึ้นมา ถ้าไม่ขึ้น แปลว่า `--listen` หรือ Firewall ยังไม่ถูก

## ทำไม AI Server ต้องแยกเครื่อง

การสร้างภาพใช้ GPU/VRAM หนักและกินเวลานาน (หลายสิบวินาทีต่อภาพ)
ถ้ารันรวมกับ Flask เครื่องเดียว เว็บทั้งระบบจะหน่วงตามไปด้วย
แยกออกมาแล้ว PC2 แค่รอผลผ่าน HTTP ยังรับ request อื่นได้ตามปกติ
