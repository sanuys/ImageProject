# วิธีรัน — Frontend

**สถานะ: ยังไม่ใช่ฝั่งที่แยกรันต่างหาก** `TODO.md` ข้อ 1 (แยก frontend
ออกจาก Flask ไปเป็นเครื่องของตัวเอง) ยังไม่ได้ทำ อ่านไฟล์นี้ก่อนคิดว่ามี
อะไรตกหล่น — ไฟล์นี้อธิบายว่าตอนนี้เป็นยังไง และจะเปลี่ยนเป็นยังไงเมื่อแยก
เสร็จ

## สิ่งที่เป็นจริงตอนนี้
`webapp/templates/*.html` และ `webapp/static/` (CSS/JS/รูปภาพ) ถูก serve
โดย Flask process เดียวกับ Backend API — ยังไม่มี process หรือเครื่องแยก
สำหรับ frontend ถ้าคุณดูแลฝั่ง Frontend **งานของคุณตอนนี้อยู่ที่
`webapp/templates/` และ `webapp/static/`** และถ้าอยากเห็นผลลัพธ์ ให้ทำตาม
[`backend.md`](backend.md) (`python app.py`) แล้วเปิด
`http://172.20.57.27:5000` — ทั้งแอป รวมถึง frontend จะขึ้นมาจากคำสั่งเดียว
นั้นเลย

ไฟล์ที่คุณจะแก้จริงๆ:
- `webapp/templates/base.html`, `generate.html`, `login.html`,
  `register.html`, `admin.html` — Jinja template
- `webapp/static/css/style.css`
- `webapp/static/js/main.js` — ควบคุม 3 แท็บ (สร้างภาพ/แก้ไขภาพ/PNG Info)
  เรียก backend ผ่าน `fetch()` ด้วย relative path เช่น `/api/generate`
  อยู่แล้ว

## สิ่งที่จะเปลี่ยนเมื่อแยกเสร็จ (ยังไม่ได้ทำ)
ตามแผนใน `TODO.md` ข้อ 1:
1. แยก `templates/` + `static/` ออกมาเป็นโฟลเดอร์ `frontend/` ต่างหาก
   รันแยกได้เอง (conda env / process / เครื่องของตัวเอง)
2. เปลี่ยนจาก Jinja templating (`{{ }}`, `{% %}`) เป็น client-side rendering
   เพราะ Flask จะไม่ได้ render หน้าพวกนี้อีกต่อไป
3. เปลี่ยน `fetch()` ใน `main.js` ให้ชี้ไปที่ IP เต็มของ Backend
   (`http://172.20.57.27:5000/api/...`) แทน relative path
4. ตัวแปร `ALLOWED_ORIGINS` ฝั่ง Backend ต้องเพิ่ม IP ของเครื่องนี้เข้าไป
   ตอนนั้น (CORS ต่อสายไว้แล้วฝั่ง backend แค่ยังไม่ได้เปิดใช้ — ดู
   `webapp/app.py`)

พอแยกเสร็จแล้ว ไฟล์นี้จะมีขั้นตอน "วิธีรัน" จริงๆ (ติดตั้ง static file
server ชี้ไปที่ `frontend/` ฯลฯ) — ตอนนี้ยังไม่มีอะไรให้ติดตั้งหรือรันแยก

## ถ้าติดขัดเพราะรอการแยกนี้
คุยกับคนดูแลฝั่ง Backend (หรือทั้งทีม) เรื่องจัดลำดับความสำคัญให้
`TODO.md` ข้อ 1 — เป็นการตัดสินใจด้านสถาปัตยกรรมที่ค้างอยู่ใหญ่ที่สุด
(จะทำ client-side rendering หรือจะ server-render ต่อแต่ย้ายเครื่อง)
