# PC1 — Frontend + Nginx (10.187.226.36)

หน้าที่: **Presentation Tier** — เสิร์ฟหน้าเว็บ (HTML/CSS/JS) และเป็น
Reverse Proxy ประตูทางเข้าของระบบทั้งหมด

ผู้ใช้เปิดแค่ `http://10.187.226.36` เครื่องเดียว ไม่ต้องรู้เลยว่าข้างหลัง
มีอีก 3 เครื่อง

```
Browser ──> Nginx (PC1) ─┬─ /        ─> ไฟล์ HTML/CSS/JS บนเครื่องนี้
                          ├─ /api/    ─> Flask ที่ PC2 :5000
                          └─ /media/  ─> ไฟล์ภาพที่ PC2 :5000
```

## โครงสร้าง

```
pc1-frontend/
├─ html/                 <- root ของเว็บ (ชี้ Nginx มาที่โฟลเดอร์นี้)
│  ├─ index.html         สร้างภาพ / แก้ไขภาพ
│  ├─ login.html
│  ├─ register.html
│  ├─ admin.html
│  ├─ css/style.css
│  └─ js/
│     ├─ config.js       ตั้งค่า API_BASE
│     ├─ common.js       apiFetch / requireLogin / navbar
│     ├─ auth.js         หน้า login + register
│     ├─ main.js         หน้าหลัก
│     └─ admin.js        หน้า admin
└─ nginx/imageproject.conf
```

## ติดตั้ง Nginx บน Windows

1. โหลด Nginx จาก https://nginx.org/en/download.html (เวอร์ชัน Stable, Windows)
2. แตกไฟล์ไว้ที่ `C:\nginx`
3. ก๊อปโฟลเดอร์ `pc1-frontend` ไปไว้ที่ `C:\ImageProject\pc1-frontend`
4. ก๊อป `nginx\imageproject.conf` ไปไว้ที่ `C:\nginx\conf\imageproject.conf`
5. แก้ `C:\nginx\conf\nginx.conf` — ใส่บรรทัดนี้ **ข้างใน** บล็อก `http { ... }`
   และลบ/คอมเมนต์บล็อก `server { listen 80; ... }` เดิมออก

   ```nginx
   include imageproject.conf;
   ```

6. **แก้ path กับ IP ใน `imageproject.conf`** ให้ตรงกับเครื่องจริง
   - `root C:/ImageProject/pc1-frontend/html;` (ใช้ `/` ไม่ใช่ `\`) — มี 2 ที่
   - `server 10.187.226.226:5000;` ในบล็อก `upstream`

## รัน

```bat
cd C:\nginx
nginx.exe -t          :: ตรวจว่า config ถูกต้องก่อนเสมอ
start nginx
```

คำสั่งอื่นที่ใช้บ่อย:

```bat
nginx -s reload       :: โหลด config ใหม่หลังแก้ไฟล์
nginx -s stop         :: หยุด
tasklist /fi "imagename eq nginx.exe"   :: เช็คว่ารันอยู่ไหม
```

## ตรวจสอบ

เปิดจากเครื่องไหนก็ได้ในวง LAN:

| URL | ควรได้ |
|---|---|
| `http://10.187.226.36/login.html` | หน้าเข้าสู่ระบบ |
| `http://10.187.226.36/api/health` | JSON บอกสถานะ PC2/PC3/PC4 |

## สิ่งที่ต้องตั้งค่าเพิ่ม

1. **Firewall (Windows)** — เปิดพอร์ต 80 ขาเข้า
   ```bat
   netsh advfirewall firewall add rule name="ImageProject Web" dir=in action=allow protocol=TCP localport=80
   ```
2. ตั้ง IP เครื่องนี้เป็น `10.187.226.36` แบบ Static
3. ถ้าจะทดสอบโดยไม่ใช้ Nginx ให้แก้ `html/js/config.js` เป็น
   `const API_BASE = "http://10.187.226.226:5000";` (ต้องมี origin ของหน้าเว็บ
   อยู่ใน `ALLOWED_ORIGINS` ของ `pc2-backend/config.py` ด้วย)
