"""
============================================================
 PC2 : BACKEND  — db_client.py
------------------------------------------------------------
 ตัวแทนของ sqlite3 เดิม: แทนที่จะเปิดไฟล์ .db บนเครื่องตัวเอง
 จะยิง HTTP ไปหา DB Server ที่เครื่อง PC4 (172.20.56.108) แทน

 ออกแบบให้ "หน้าตาเหมือน sqlite3 ของเดิม" เพื่อให้โค้ดใน app.py
 แทบไม่ต้องแก้:
     conn = get_db()
     row  = conn.execute("SELECT ...", (a, b)).fetchone()
     rows = conn.execute("SELECT ...").fetchall()
     cur  = conn.execute("INSERT ...", (...)); cur.lastrowid
     conn.commit()   # no-op (DB Server commit ให้ทุกคำสั่งอยู่แล้ว)
     conn.close()    # no-op (ไม่มี connection ค้างไว้)

 ต่างจากเดิมตรงที่ row ที่ได้เป็น dict ธรรมดา (ไม่ใช่ sqlite3.Row)
 แต่เข้าถึงด้วย row["column"] ได้เหมือนกัน

 ไฟล์ภาพก็เก็บที่ PC4 เหมือนกัน — ใช้ put_file / get_file / delete_file ท้ายไฟล์นี้
============================================================
"""

from urllib.parse import quote

import requests

from config import DB_SERVER_URL, DB_TOKEN, DB_TIMEOUT


class DatabaseError(Exception):
    """ยิงไป DB Server ไม่สำเร็จ หรือ SQL ผิดพลาด"""


class Result:
    """ผลลัพธ์ของ execute() หนึ่งครั้ง — เลียนแบบ sqlite3.Cursor"""

    def __init__(self, payload):
        self.rows = payload.get("rows") or []
        self.lastrowid = payload.get("lastrowid")
        self.rowcount = payload.get("rowcount", -1)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)


class Connection:
    """ตัวแทน sqlite3.Connection ที่คุยกับ DB Server ผ่าน HTTP"""

    def execute(self, sql, params=(), fetch="all"):
        try:
            resp = requests.post(
                f"{DB_SERVER_URL}/sql",
                json={"sql": sql, "params": list(params), "fetch": fetch},
                headers={"X-DB-Token": DB_TOKEN},
                timeout=DB_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise DatabaseError(f"เชื่อมต่อ Database Server ({DB_SERVER_URL}) ไม่ได้: {e}") from e

        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", resp.text)
            except ValueError:
                detail = resp.text
            raise DatabaseError(f"Database Server ตอบกลับผิดพลาด ({resp.status_code}): {detail}")

        return Result(resp.json())

    def executescript_batch(self, statements):
        """รันหลายคำสั่งใน transaction เดียว — statements = [(sql, params), ...]"""
        try:
            resp = requests.post(
                f"{DB_SERVER_URL}/sql/batch",
                json={"statements": [{"sql": s, "params": list(p)} for s, p in statements]},
                headers={"X-DB-Token": DB_TOKEN},
                timeout=DB_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise DatabaseError(f"เชื่อมต่อ Database Server ไม่ได้: {e}") from e

        if resp.status_code != 200:
            raise DatabaseError(f"Database Server ตอบกลับผิดพลาด ({resp.status_code})")
        return resp.json().get("lastrowids", [])

    # --- เมธอดที่มีไว้ให้โค้ดเดิมเรียกได้โดยไม่พัง ---
    def commit(self):
        """DB Server commit ให้ทุกคำสั่งอยู่แล้ว ที่นี่จึงไม่ต้องทำอะไร"""

    def close(self):
        """ไม่มี connection ค้างไว้ (ยิง HTTP ทีละครั้ง) จึงไม่ต้องปิดอะไร"""


def get_db():
    return Connection()


def db_health():
    """เช็คว่า DB Server ยังตอบอยู่ไหม — ใช้ใน /api/health"""
    try:
        resp = requests.get(f"{DB_SERVER_URL}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}


# ============================================================
#  ไฟล์ภาพ — เก็บที่ PC4 (ข้างฐานข้อมูล) ไม่ได้เก็บบนเครื่องนี้
#  rel_path คือ path แบบเดียวกับที่เก็บในตาราง เช่น outputs/1_1789.png
# ============================================================
FILE_TIMEOUT = 30   # วินาที — ไฟล์ภาพใหญ่กว่าคำสั่ง SQL จึงให้เวลามากกว่า


def _file_request(method, rel_path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-DB-Token"] = DB_TOKEN
    url = f"{DB_SERVER_URL}/files/{quote(rel_path, safe='/')}"
    try:
        return requests.request(method, url, headers=headers, timeout=FILE_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as e:
        raise DatabaseError(f"เชื่อมต่อที่เก็บไฟล์ภาพบน PC4 ({DB_SERVER_URL}) ไม่ได้: {e}") from e


def put_file(rel_path, data):
    """ส่งไฟล์ (bytes) ไปเก็บที่ PC4"""
    resp = _file_request("PUT", rel_path, data=data,
                         headers={"Content-Type": "application/octet-stream"})
    if resp.status_code != 200:
        raise DatabaseError(f"เก็บไฟล์ภาพที่ PC4 ไม่สำเร็จ ({resp.status_code})")


def get_file(rel_path):
    """ขอไฟล์จาก PC4 — คืน bytes หรือ None ถ้าไม่มีไฟล์นี้"""
    resp = _file_request("GET", rel_path)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise DatabaseError(f"อ่านไฟล์ภาพจาก PC4 ไม่สำเร็จ ({resp.status_code})")
    return resp.content


def delete_file(rel_path):
    """สั่ง PC4 ลบไฟล์ — คืน True ถ้าลบจริง, False ถ้าไม่มีไฟล์นี้อยู่แล้ว"""
    resp = _file_request("DELETE", rel_path)
    if resp.status_code != 200:
        raise DatabaseError(f"ลบไฟล์ภาพที่ PC4 ไม่สำเร็จ ({resp.status_code})")
    return bool(resp.json().get("deleted"))
