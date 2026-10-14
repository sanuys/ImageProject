
CREATE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        negative_prompt TEXT,
        steps INTEGER,
        cfg_scale REAL,
        width INTEGER,
        height INTEGER,
        sampler TEXT,
        seed INTEGER,
        checkpoint TEXT,
        image_path TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        source_label TEXT,
        operation TEXT NOT NULL,
        params TEXT,
        result_image TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_generations_user ON generations (user_id, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_edits_user ON edits (user_id, id DESC)",
]


def init_db(conn):
# ประกาศฟังก์ชัน init_db โดยรับ conn เข้ามา
# conn คือ Connection ที่ใช้เชื่อมต่อกับฐานข้อมูล SQLite
# ฟังก์ชันนี้ใช้สร้างตารางและตรวจสอบโครงสร้างฐานข้อมูล
# รวมถึงปรับฐานข้อมูลเก่าให้รองรับคอลัมน์ที่เพิ่มเข้ามาใหม่

    """สร้างตาราง + migrate ฐานข้อมูลเก่าให้ครบคอลัมน์"""
    # Docstring ใช้อธิบายหน้าที่ของฟังก์ชัน
    # migrate หมายถึงการปรับโครงสร้างฐานข้อมูลเดิมให้รองรับระบบเวอร์ชันใหม่

    for stmt in CREATE_STATEMENTS:
    # วนลูปอ่านคำสั่ง SQL ทีละรายการจาก CREATE_STATEMENTS
    # stmt คือตัวแปรที่เก็บคำสั่ง SQL ของรอบปัจจุบัน

        conn.execute(stmt)
        # execute() ส่งคำสั่ง SQL ไปให้ฐานข้อมูลทำงาน
        # ในที่นี้ใช้สร้างตารางและ Index ตามรายการที่กำหนดไว้

    conn.commit()
    # commit() ยืนยันและบันทึกการเปลี่ยนแปลงลงในฐานข้อมูล
    # ทำให้การสร้างตารางและ Index ถูกบันทึกเรียบร้อย


    # --- migration: ฐานข้อมูลเก่าที่สร้างก่อนมีคอลัมน์ is_admin ---
    # ส่วนนี้รองรับฐานข้อมูลเก่าที่ยังไม่มีคอลัมน์ is_admin
    # เพื่อให้ระบบเวอร์ชันใหม่สามารถตรวจสอบสิทธิ์ Admin ได้

    user_cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    # PRAGMA table_info(users) ใช้ตรวจสอบคอลัมน์ทั้งหมดในตาราง users
    # conn.execute() ส่งคำสั่งตรวจสอบไปยัง SQLite
    # row["name"] ดึงชื่อคอลัมน์จากผลลัพธ์แต่ละแถว
    # List Comprehension นำชื่อคอลัมน์ทั้งหมดมารวมไว้ใน List user_cols

    if "is_admin" not in user_cols:
    # ตรวจสอบว่าใน user_cols ไม่มีชื่อ is_admin หรือไม่
    # ถ้าไม่มี แสดงว่าฐานข้อมูลเดิมยังไม่มีคอลัมน์นี้
    # จึงต้องเพิ่มคอลัมน์เพื่อให้รองรับระบบสิทธิ์ผู้ดูแล

        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        # ALTER TABLE ใช้ปรับโครงสร้างตารางที่มีอยู่แล้ว
        # ADD COLUMN is_admin เพิ่มคอลัมน์สำหรับเก็บสิทธิ์ Admin
        # INTEGER กำหนดชนิดข้อมูลเป็นจำนวนเต็ม
        # NOT NULL หมายถึงห้ามเป็น NULL
        # DEFAULT 0 กำหนดค่าเริ่มต้นให้เป็นผู้ใช้ทั่วไป

        conn.commit()
        # บันทึกการเพิ่มคอลัมน์ is_admin ลงในฐานข้อมูล


    # --- migration: ฐานข้อมูลเก่าที่สร้างก่อนมีคอลัมน์ checkpoint ---
    # ส่วนนี้รองรับฐานข้อมูลเดิมที่ยังไม่มีคอลัมน์ checkpoint
    # เพื่อให้สามารถเก็บชื่อโมเดลที่ใช้สร้างภาพได้

    gen_cols = [row["name"] for row in conn.execute("PRAGMA table_info(generations)")]
    # ตรวจสอบคอลัมน์ทั้งหมดในตาราง generations
    # row["name"] ใช้ดึงชื่อคอลัมน์แต่ละตัว
    # นำชื่อคอลัมน์ทั้งหมดมาเก็บไว้ใน List gen_cols

    if "checkpoint" not in gen_cols:
    # ตรวจสอบว่าตาราง generations ยังไม่มีคอลัมน์ checkpoint หรือไม่
    # ถ้าไม่มี จะดำเนินการเพิ่มคอลัมน์นี้

        conn.execute("ALTER TABLE generations ADD COLUMN checkpoint TEXT")
        # เพิ่มคอลัมน์ checkpoint เข้าไปในตาราง generations
        # TEXT ใช้เก็บชื่อโมเดลเป็นข้อความ
        # คำสั่งนี้เพิ่มคอลัมน์ให้ตารางเดิมโดยไม่ต้องสร้างตารางใหม่

        conn.commit()
        # บันทึกการเพิ่มคอลัมน์ checkpoint ลงในฐานข้อมูล


    # ถ้ายังไม่มี admin สักคน ให้ยกคนที่สมัครไว้ก่อนใครเป็น admin อัตโนมัติ
    # ส่วนนี้ใช้ตรวจสอบว่ามีบัญชีผู้ดูแลระบบอยู่แล้วหรือยัง

    has_admin = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE is_admin = 1"
    ).fetchone()["c"]
    # SELECT COUNT(*) ใช้นับจำนวนบัญชีที่ตรงกับเงื่อนไข
    # FROM users หมายถึงตรวจสอบข้อมูลจากตาราง users
    # WHERE is_admin = 1 เลือกเฉพาะบัญชีที่เป็น Admin
    # AS c ตั้งชื่อคอลัมน์ผลลัพธ์จากการนับว่า c
    # fetchone() ดึงผลลัพธ์มาเพียงหนึ่งแถว
    # ["c"] อ่านค่าจำนวน Admin ที่นับได้
    # ค่าที่ได้จะถูกเก็บไว้ในตัวแปร has_admin

    if not has_admin:
    # ถ้า has_admin เป็น 0 จะถือว่ายังไม่มี Admin
    # not ทำให้เงื่อนไขเป็นจริงเมื่อ has_admin ไม่มีค่าเป็นจำนวนที่ไม่ใช่ศูนย์
    # จากนั้นจึงเลือกผู้ใช้คนแรกให้เป็น Admin

        conn.execute("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)")
        # UPDATE users ใช้แก้ไขข้อมูลในตาราง users
        # SET is_admin = 1 เปลี่ยนสิทธิ์บัญชีที่เลือกให้เป็น Admin
        # SELECT MIN(id) FROM users หาค่า ID ที่น้อยที่สุด
        # WHERE id = ... เลือกเฉพาะบัญชีที่มี ID ตรงกับค่าที่น้อยที่สุด
        # โดยทั่วไป ID ที่น้อยที่สุดคือบัญชีที่ถูกสร้างก่อนบัญชีอื่น
        # หากตาราง users ยังไม่มีผู้ใช้ คำสั่งนี้จะไม่แก้ไขข้อมูลแถวใด

        conn.commit()
        # บันทึกการเปลี่ยนสิทธิ์ Admin ลงในฐานข้อมูล
        # เพื่อให้การเปลี่ยนแปลงมีผลในฐานข้อมูล