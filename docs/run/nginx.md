# วิธีรัน — Nginx (reverse proxy)

**สถานะ: ทำ config scaffold ไว้แล้ว แต่ยังไม่เคยรันกับ Nginx จริง** ไฟล์
config มีอยู่แล้ว (`nginx/luma.conf`) แต่เขียนขึ้นโดยไม่มี Nginx ให้ทดสอบจริง
— ต้องเช็กด้วย `nginx -t` ก่อนเชื่อถือได้

## 1. ติดตั้ง Nginx
บนเครื่องที่กำหนดให้เป็น reverse-proxy host (เนื้อหาจากวิชา Network —
routing/reverse proxy)

- Windows: ดาวน์โหลดจาก [nginx.org](https://nginx.org/en/download.html)
  แตกไฟล์ แล้วรัน `nginx.exe` จากโฟลเดอร์นั้น
- Linux: `sudo apt install nginx` (Debian/Ubuntu) หรือเทียบเท่า

## 2. อัปเดต config ให้เป็น IP จริง

เปิด `nginx/luma.conf` แล้วเช็กว่า `upstream` block ตรงกับเครื่องจริงของทีม
IP ที่รู้อยู่ตอนนี้:

```
Backend   : 172.20.57.27:5000
AI Server : 172.20.56.112:7860  (Nginx ไม่ได้ proxy ไปหาตรงๆ —
                                  มีแค่ Backend ที่คุยกับมัน)
Frontend  : ยังไม่ได้แยกออกมา (ดู docs/run/frontend.md) — ตอนนี้
            luma_frontend ชี้ไปที่ 172.20.57.27:5000 เดียวกับ backend
```

อัปเดต `luma_frontend` ใน `nginx/luma.conf` เมื่อ frontend ย้ายไปอยู่เครื่อง
ของตัวเองจริงๆ

## 3. Deploy config

คัดลอก `nginx/luma.conf` ไปไว้ใน config include path ของ Nginx เช่น:
- Linux: `/etc/nginx/sites-available/luma.conf` แล้วทำ symlink ไปที่
  `sites-enabled/`
- Windows: ใส่ include line ใน `conf/nginx.conf` ให้ชี้มาที่ไฟล์นี้
  หรือแทนที่ server block เริ่มต้น

จากนั้น:
```bash
nginx -t          # เช็ก syntax ก่อนทุกครั้งที่จะ reload
nginx -s reload    # หรือ restart service บน Windows
```

## 4. ตรวจสอบ

จากเบราว์เซอร์หรือเครื่องอื่นในวง LAN ยิงไปที่ IP ของเครื่อง Nginx พอร์ต 80
ควรเข้าแอปได้เหมือนยิงตรงไปที่ Backend พอร์ต 5000 — หน้า login โหลดได้
เรียก `/api/...` สำเร็จ

ถ้าเข้าไม่ได้:
- `client_max_body_size` ตั้งไว้ที่ `20m` ใน config สำหรับอัปโหลดภาพ
  (`/api/edit`, `/api/png-info`) — เพิ่มค่านี้ถ้าเจอ error 413 ตอนอัปโหลด
  ไฟล์ใหญ่
- `/api/generate` ตั้ง `proxy_read_timeout` ไว้ 300 วินาทีแล้ว — ถ้า
  generate ผ่าน Nginx แล้ว timeout แต่ยิงตรงไปที่ Backend ใช้งานได้ปกติ
  ให้เช็กว่ามีอะไรมา override ค่านี้หรือเปล่า

## สิ่งที่ยังไม่ได้ทำ (ดู `TODO.md` ข้อ 2)
- ยังไม่เคยทดสอบแบบ end-to-end กับ multi-machine จริง
- ยังไม่ได้ตัดสินใจว่าจะให้ Nginx serve `static/outputs/` ตรงๆ
  (เร็วกว่า) หรือ proxy ผ่าน Flask เหมือนตอนนี้ — ตอนนี้ยัง proxy
  ผ่าน Flask อยู่
