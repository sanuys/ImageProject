# วิธีรัน — AI Server (Forge / Stability Matrix)

**IP ที่รู้อยู่ตอนนี้:** `172.20.56.112` พอร์ต `7860` (มาจาก `FORGE_API_URL`
ฝั่ง Backend) รายละเอียดพื้นฐานการติดตั้ง (requirements, checkpoint ที่ต้องมี):
[`../ai-server.md`](../ai-server.md) — ไฟล์นี้เอาแค่ขั้นตอน "เปิดยังไง"

## 1. สิ่งที่ต้องมีก่อน
- GPU ที่รัน Stable Diffusion ได้
- ติดตั้ง Stability Matrix แล้วเพิ่มแพ็กเกจ **Forge**
- มี checkpoint อย่างน้อย 1 ตัวที่ตรงกับรายการใน `ALLOWED_CHECKPOINTS` ใน
  `webapp/app.py` (ตอนนี้คือ checkpoint ที่ชื่อมีคำว่า `realSimpleAnime`
  หรือ `realismIllustriousBy`)

## 2. Launch Options

ใน Stability Matrix เปิด Launch Options ของแพ็กเกจ Forge แล้วตั้งเป็น:

```
--api --api-auth admin:cdti1234 --listen --port 7860
```

| Flag | ทำไมต้องมี |
|---|---|
| `--api` | เปิด endpoint `/sdapi/v1/...` — จำเป็น ไม่งั้น backend ใช้งานไม่ได้ |
| `--api-auth user:pass` | ต้องตรงกับ `FORGE_API_USER` / `FORGE_API_PASS` ใน `.env` ฝั่ง Backend |
| `--listen` | bind เป็น `0.0.0.0` แทน localhost — จำเป็นเพื่อให้ Backend (อยู่คนละเครื่อง) เข้าถึงได้ |
| `--port` | ต้องตรงกับพอร์ตใน `FORGE_API_URL` ฝั่ง Backend |

จากนั้นเปิดใช้งานแพ็กเกจตามปกติจาก Stability Matrix

## 3. ตรวจสอบว่าเชื่อมต่อได้

จากเครื่องนี้เอง:
```bash
curl -u admin:cdti1234 http://127.0.0.1:7860/sdapi/v1/sd-models
```

จากเครื่อง Backend (`172.20.57.27`):
```bash
curl -u admin:cdti1234 http://172.20.56.112:7860/sdapi/v1/sd-models
```

ทั้งสองคำสั่งควรได้ JSON รายชื่อ checkpoint กลับมา ถ้าคำสั่งที่สองล้มเหลว
แต่คำสั่งแรกทำงานปกติ แสดงว่าปัญหาอยู่ที่ firewall/เครือข่ายของเครื่องนี้
(เช็ก Windows Firewall ว่าอนุญาต inbound พอร์ต 7860 และเช็กว่าใส่
`--listen` จริงตอน launch)

## 4. ถ้าเครื่องนี้ไม่ได้เปิดอยู่จะเกิดอะไรขึ้น
ฝั่ง Backend จะ fallback แบบนุ่มนวล ไม่ crash:
- `/api/samplers` จะใช้รายชื่อ sampler ที่ hardcode ไว้แทน
- `/api/checkpoints` จะคืนค่า list ว่าง (dropdown จะโชว์ข้อความเตือน)
- `/api/generate` กับ `/api/png-info` จะตอบกลับ HTTP 502 พร้อมข้อความ
  แจ้งเตือนภาษาไทย

ดังนั้นคนอื่นในทีมยังทำงานส่วนอื่นต่อได้แม้เครื่องนี้จะยังไม่พร้อม —
แต่จะสร้างภาพหรืออ่าน PNG Info ไม่ได้จนกว่าเครื่องนี้จะกลับมาออนไลน์

## สิ่งที่ยังไม่ได้ทำ (ดู `TODO.md` ข้อ 4)
- ระบบคิว (Queue) สำหรับ `/api/generate` ที่ถูกยิงพร้อมกันจากหลาย user
- รองรับ LoRA
