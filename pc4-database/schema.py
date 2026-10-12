"""
============================================================
 PC4 : DATABASE  (172.20.56.108)
 schema.py — โครงสร้างตารางทั้งหมดของระบบ
 เครื่องฐานข้อมูลเป็นเจ้าของ schema เครื่องเดียว
 (เดิม init_db() อยู่ใน app.py ของ Flask — ย้ายมาไว้ที่นี่)
============================================================
"""

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
    """สร้างตาราง + migrate ฐานข้อมูลเก่าให้ครบคอลัมน์"""
    for stmt in CREATE_STATEMENTS:
        conn.execute(stmt)
    conn.commit()

    # --- migration: ฐานข้อมูลเก่าที่สร้างก่อนมีคอลัมน์ is_admin ---
    user_cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
    if "is_admin" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # --- migration: ฐานข้อมูลเก่าที่สร้างก่อนมีคอลัมน์ checkpoint ---
    gen_cols = [row["name"] for row in conn.execute("PRAGMA table_info(generations)")]
    if "checkpoint" not in gen_cols:
        conn.execute("ALTER TABLE generations ADD COLUMN checkpoint TEXT")
        conn.commit()

    # ถ้ายังไม่มี admin สักคน ให้ยกคนที่สมัครไว้ก่อนใครเป็น admin อัตโนมัติ
    has_admin = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE is_admin = 1"
    ).fetchone()["c"]
    if not has_admin:
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)")
        conn.commit()
