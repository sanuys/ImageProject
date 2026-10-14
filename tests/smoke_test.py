"""
Smoke test for the JSON API (pc2-backend) running against a real Database
Server (pc4-database) — everything in one process, nothing on the network.

  * The Database Server is started on a free local port with a throwaway
    database + storage folder (tempfile), so this never touches
    pc4-database/database.db, single-pc/data/ or pc2-backend/logs/.
  * The AI Server (Forge) is faked, so no GPU machine is needed. Both the
    "Forge is up" and "Forge is unreachable" paths are exercised.

Usage (from the repo root, with pc2-backend's venv active):
    python tests/smoke_test.py

Exits non-zero and lists the failed checks if anything breaks.
"""
import base64
import io
import json
import os
import shutil
import socket
import sys
import tempfile
import threading

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pc4-database"))
sys.path.insert(0, os.path.join(ROOT, "pc2-backend"))

TMP_DIR = tempfile.mkdtemp(prefix="luma_smoke_")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


DB_PORT = _free_port()
FORGE_URL = "http://forge.invalid:7860"

# Must be set before config / db_server are imported (both read them at import time).
os.environ["DB_TOKEN"] = "smoke-test-token"
os.environ["SECRET_KEY"] = "smoke-test-secret-key"
os.environ["FLASK_DEBUG"] = "false"
os.environ["DB_PATH"] = os.path.join(TMP_DIR, "test.db")
os.environ["STORAGE_DIR"] = os.path.join(TMP_DIR, "storage")
os.environ["DB_PORT"] = str(DB_PORT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import requests  # noqa: E402
from werkzeug.serving import make_server, WSGIRequestHandler  # noqa: E402

import config  # noqa: E402  (pc2-backend/config.py)

config.DB_SERVER_URL = f"http://127.0.0.1:{DB_PORT}"
config.FORGE_API_URL = FORGE_URL
config.LOG_DIR = os.path.join(TMP_DIR, "logs")
config.GENERATE_COOLDOWN_SECONDS = 0   # switched on only for the cooldown checks

import db_server  # noqa: E402  (pc4-database/db_server.py)
from schema import init_db  # noqa: E402

# Keep the output readable: only the [OK]/[FAIL] lines, not one line per SQL statement / request.
db_server.print = lambda *args, **kwargs: None


class _QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


failures = []


def check(label, condition):
    print(f"[{'OK  ' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


def make_png(value=90):
    ok, buf = cv2.imencode(".png", np.full((32, 32, 3), value, dtype=np.uint8))
    assert ok
    return buf.tobytes()


PNG = make_png()


# ------------------------------------------------------------
#  Fake AI Server: intercept only requests going to FORGE_URL,
#  let everything else (Backend -> Database Server) through.
# ------------------------------------------------------------
class FakeForge:
    up = True
    txt2img_calls = 0

    MODELS = [
        {"title": "realSimpleAnime_v1.safetensors [abc]", "model_name": "realSimpleAnime_v1"},
        {"title": "notOnTheAllowList.safetensors [def]", "model_name": "notOnTheAllowList"},
    ]

    class _Resp:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    @classmethod
    def handle(cls, url, **kwargs):
        if not cls.up:
            raise requests.exceptions.ConnectionError("fake: AI Server is down")
        if url.endswith("/sdapi/v1/samplers"):
            return cls._Resp([{"name": "Fake Sampler"}])
        if url.endswith("/sdapi/v1/sd-models"):
            return cls._Resp(cls.MODELS)
        if url.endswith("/sdapi/v1/txt2img"):
            cls.txt2img_calls += 1
            return cls._Resp({
                "images": [base64.b64encode(PNG).decode()],
                "info": json.dumps({"seed": 4242, "sd_model_name": "fake-model"}),
            })
        raise AssertionError(f"unexpected Forge call: {url}")


_real_get, _real_post = requests.get, requests.post


def _fake_get(url, *args, **kwargs):
    return FakeForge.handle(url, **kwargs) if url.startswith(FORGE_URL) else _real_get(url, *args, **kwargs)


def _fake_post(url, *args, **kwargs):
    return FakeForge.handle(url, **kwargs) if url.startswith(FORGE_URL) else _real_post(url, *args, **kwargs)


def edit(client, **fields):
    data = dict(fields)
    if "generation_id" not in data:
        data["image"] = (io.BytesIO(PNG), "test.png")
    return client.post("/api/edit", data=data, content_type="multipart/form-data")


def main():
    conn = db_server.get_conn()
    init_db(conn)
    conn.close()
    server = make_server("127.0.0.1", DB_PORT, db_server.app,
                         threaded=True, request_handler=_QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    requests.get, requests.post = _fake_get, _fake_post
    import app as backend  # (pc2-backend/app.py)

    backend.app.config["TESTING"] = True
    alice = backend.app.test_client()   # first user -> admin
    bob = backend.app.test_client()     # ordinary user
    anon = backend.app.test_client()

    try:
        # ---------- Database Server ----------
        r = _real_get(f"http://127.0.0.1:{DB_PORT}/health", timeout=5)
        check("DB /health -> 200 ok", r.status_code == 200 and r.json().get("status") == "ok")
        r = _real_post(f"http://127.0.0.1:{DB_PORT}/sql", json={"sql": "SELECT 1"},
                       headers={"X-DB-Token": "wrong-token"}, timeout=5)
        check("DB /sql with a wrong token -> 401", r.status_code == 401)

        # ---------- auth ----------
        r = anon.get("/api/me")
        check("GET /api/me (anonymous) -> 401", r.status_code == 401)

        r = alice.post("/api/register", json={"username": "alice", "password": "test1234", "confirm": "nope"})
        check("POST /api/register (confirm mismatch) -> 400", r.status_code == 400)
        r = alice.post("/api/register", json={"username": "alice", "password": "test1234", "confirm": "test1234"})
        check("POST /api/register -> 201", r.status_code == 201)
        r = alice.post("/api/register", json={"username": "alice", "password": "test1234", "confirm": "test1234"})
        check("POST /api/register (duplicate username) -> 409", r.status_code == 409)
        bob.post("/api/register", json={"username": "bob", "password": "test1234", "confirm": "test1234"})

        r = alice.post("/api/login", json={"username": "alice", "password": "wrong-password"})
        check("POST /api/login (wrong password) -> 401", r.status_code == 401)
        r = alice.post("/api/login", json={"username": "alice", "password": "test1234"})
        check("POST /api/login -> 200", r.status_code == 200)
        bob.post("/api/login", json={"username": "bob", "password": "test1234"})

        r = alice.get("/api/me")
        check("first registered user is admin", r.status_code == 200 and r.get_json()["user"]["is_admin"] is True)
        r = bob.get("/api/me")
        check("second user is not admin", r.status_code == 200 and r.get_json()["user"]["is_admin"] is False)

        # ---------- AI Server unreachable: must degrade, not crash ----------
        FakeForge.up = False
        r = alice.get("/api/samplers")
        check("GET /api/samplers (AI down) -> 200 with fallback list",
              r.status_code == 200 and len(r.get_json()) > 0)
        r = alice.get("/api/checkpoints")
        check("GET /api/checkpoints (AI down) -> 200 []", r.status_code == 200 and r.get_json() == [])
        r = alice.post("/api/generate", json={"prompt": "a cat"})
        check("POST /api/generate (AI down) -> 502", r.status_code == 502)
        r = anon.get("/api/health")
        health = r.get_json()
        check("GET /api/health reports DB ok and AI error",
              r.status_code == 200 and health["database_pc4"].get("status") == "ok"
              and health["ai_server_pc3"].get("status") == "error")
        FakeForge.up = True

        # ---------- AI Server up ----------
        r = alice.get("/api/samplers")
        check("GET /api/samplers -> list from AI Server", r.get_json() == ["Fake Sampler"])
        r = alice.get("/api/checkpoints")
        names = [c["model_name"] for c in r.get_json()]
        check("GET /api/checkpoints -> only allow-listed models", names == ["realSimpleAnime_v1"])

        r = alice.post("/api/generate", json={"prompt": ""})
        check("POST /api/generate (empty prompt) -> 400", r.status_code == 400)
        r = alice.post("/api/generate", json={"prompt": "a cat", "steps": "many"})
        check("POST /api/generate (non-numeric steps) -> 400", r.status_code == 400)
        r = alice.post("/api/generate", json={"prompt": 'a "quoted" <cat>'})
        gen = r.get_json()
        check("POST /api/generate -> 200 with the real seed", r.status_code == 200 and gen.get("seed") == 4242)
        gen_id, gen_url = gen["id"], gen["image_url"]

        r = alice.get(gen_url)
        check("GET /media/<generated> (owner) -> PNG", r.status_code == 200 and r.data[:4] == b"\x89PNG")
        r = anon.get(gen_url)
        check("GET /media/<generated> (anonymous) -> 401", r.status_code == 401)
        check("image file is stored by the Database Server",
              os.path.isfile(os.path.join(TMP_DIR, "storage", *gen_url[len("/media/"):].split("/"))))

        r = alice.get("/api/history")
        hist = r.get_json()
        check("GET /api/history lists the generation",
              r.status_code == 200 and [g["id"] for g in hist["generations"]] == [gen_id]
              and hist["generations"][0]["checkpoint"] == "fake-model")
        r = bob.get("/api/history")
        check("GET /api/history (other user) is empty", r.get_json() == {"generations": [], "edits": []})

        # ---------- generate cooldown ----------
        config.GENERATE_COOLDOWN_SECONDS = 60
        backend._last_generate_at.clear()
        calls_before = FakeForge.txt2img_calls
        r1 = alice.post("/api/generate", json={"prompt": "a dog"})
        r2 = alice.post("/api/generate", json={"prompt": "a dog"})
        r3 = bob.post("/api/generate", json={"prompt": "a dog"})
        check("cooldown: 1st request -> 200", r1.status_code == 200)
        check("cooldown: 2nd request from the same user -> 429", r2.status_code == 429)
        check("cooldown: another user is not affected -> 200", r3.status_code == 200)
        check("cooldown: rejected request never reached the AI Server",
              FakeForge.txt2img_calls == calls_before + 2)
        config.GENERATE_COOLDOWN_SECONDS = 0

        # ---------- edit ----------
        edit_ids = {}
        for operation, method in [("point_op", "negative"), ("point_op", "log"), ("point_op", "stretch"),
                                  ("auto_contrast", "equalize"),
                                  ("linear_filter", "mean"), ("linear_filter", "gaussian"),
                                  ("linear_filter", "laplacian"),
                                  ("nonlinear_filter", "median"), ("nonlinear_filter", "min"),
                                  ("nonlinear_filter", "max")]:
            r = edit(alice, operation=operation, method=method)
            check(f"POST /api/edit {operation}/{method} -> 200", r.status_code == 200)
            if r.status_code == 200:
                edit_ids[(operation, method)] = r.get_json()

        r = edit(alice, operation="auto_contrast", method="auto")
        check("POST /api/edit auto_contrast/auto on a flat image -> 400 (cannot stretch)", r.status_code == 400)
        r = edit(alice, operation="not_a_real_operation", method="negative")
        check("POST /api/edit (unknown operation) -> 400", r.status_code == 400)
        r = edit(alice, operation="point_op", method="not_a_real_method")
        check("POST /api/edit (unknown method) -> 400", r.status_code == 400)
        r = edit(alice, operation="point_op", method="stretch", r1="200", r2="100")
        check("POST /api/edit stretch with r1 >= r2 -> 400", r.status_code == 400)
        r = edit(alice, operation="linear_filter", method="mean", ksize="abc")
        check("POST /api/edit (non-numeric ksize) -> 400", r.status_code == 400)
        r = alice.post("/api/edit", data={"operation": "point_op", "method": "negative",
                                          "image": (io.BytesIO(b"this is not an image"), "x.png")},
                       content_type="multipart/form-data")
        check("POST /api/edit (file is not an image) -> 400", r.status_code == 400)
        r = alice.post("/api/edit", data={"operation": "point_op", "method": "negative"},
                       content_type="multipart/form-data")
        check("POST /api/edit (no source image) -> 400", r.status_code == 400)

        r = edit(alice, operation="point_op", method="negative", generation_id=str(gen_id))
        check("POST /api/edit from own generation -> 200", r.status_code == 200)
        r = edit(bob, operation="point_op", method="negative", generation_id=str(gen_id))
        check("POST /api/edit from someone else's generation -> 404", r.status_code == 404)

        negative = edit_ids.get(("point_op", "negative"))
        if negative:
            r = alice.get(negative["image_url"])
            out = cv2.imdecode(np.frombuffer(r.data, dtype=np.uint8), cv2.IMREAD_COLOR)
            check("negative of a flat 90 image is a flat 165 image",
                  out is not None and out.shape == (32, 32, 3) and int(out.min()) == int(out.max()) == 165)

            r = bob.post(f"/api/edit/delete/{negative['id']}")
            check("POST /api/edit/delete (someone else's edit) -> 404", r.status_code == 404)
            r = alice.post(f"/api/edit/delete/{negative['id']}")
            check("POST /api/edit/delete (own edit) -> 200", r.status_code == 200)
            r = alice.get(negative["image_url"])
            check("deleted edit's image file is gone -> 404", r.status_code == 404)

        # ---------- admin ----------
        r = bob.get("/api/admin/records")
        check("GET /api/admin/records (non-admin) -> 403", r.status_code == 403)
        r = bob.post(f"/api/admin/delete/{gen_id}")
        check("POST /api/admin/delete (non-admin) -> 403", r.status_code == 403)
        r = alice.get("/api/admin/records")
        data = r.get_json()
        check("GET /api/admin/records (admin) sees every user's generations",
              r.status_code == 200 and data["total_count"] == 3
              and {rec["username"] for rec in data["records"]} == {"alice", "bob"})
        r = alice.post(f"/api/admin/delete/{gen_id}")
        check("POST /api/admin/delete (admin) -> 200", r.status_code == 200)
        r = alice.post(f"/api/admin/delete/{gen_id}")
        check("POST /api/admin/delete (already deleted) -> 404", r.status_code == 404)
        r = alice.get(gen_url)
        check("deleted generation's image file is gone -> 404", r.status_code == 404)

        # ---------- logout ----------
        r = alice.post("/api/logout")
        check("POST /api/logout -> 200", r.status_code == 200)
        r = alice.get("/api/me")
        check("GET /api/me after logout -> 401", r.status_code == 401)

        # ---------- log file ----------
        log_path = os.path.join(config.LOG_DIR, "app.log")
        log = open(log_path, encoding="utf-8").read() if os.path.isfile(log_path) else ""
        for needle in ["New user registered: alice", "Login failed for username: alice",
                       "Login success: alice", "Generation created:", "Generate rate-limited: user=alice",
                       "AI Server unreachable (generate)", "Edit created:", "Edit deleted:",
                       "Admin alice deleted generation", "Logout: alice"]:
            check(f"app.log contains '{needle}'", needle in log)
        check("app.log does not contain passwords", "test1234" not in log and "wrong-password" not in log)

    finally:
        requests.get, requests.post = _real_get, _real_post
        server.shutdown()
        for handler in list(backend.app.logger.handlers):   # release app.log so Windows can delete it
            handler.close()
            backend.app.logger.removeHandler(handler)
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED:")
        for label in failures:
            print(f"  - {label}")
        sys.exit(1)
    print("All smoke checks passed.")
    print("NOTE: the AI Server was faked. Real image generation (PC2 -> PC3) and the Nginx layer")
    print("      (PC1) are not covered here - check those with pc2-backend/check-ai.bat and a browser.")


if __name__ == "__main__":
    main()
