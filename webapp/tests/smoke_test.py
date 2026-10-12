"""
Smoke test: hits the routes that don't need the AI Server (Forge) to be reachable.

Runs against a throwaway SQLite DB and throwaway output folders (never touches
webapp/database.db or webapp/static/outputs/), so it's safe to run anytime,
including on a machine with no AI Server configured.

Usage:
    cd webapp
    python tests/smoke_test.py
"""
import io
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("SECRET_KEY", "smoke-test-secret-key")
os.environ.setdefault("FLASK_DEBUG", "true")

import cv2
import numpy as np

import app as app_module

failures = []


def check(label, condition):
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def make_test_png_bytes():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def main():
    tmp_dir = tempfile.mkdtemp(prefix="luma_smoke_")
    app_module.DB_PATH = os.path.join(tmp_dir, "test.db")
    app_module.OUTPUT_DIR = os.path.join(tmp_dir, "outputs")
    app_module.EDIT_OUTPUT_DIR = os.path.join(tmp_dir, "outputs", "edits")
    os.makedirs(app_module.EDIT_OUTPUT_DIR, exist_ok=True)

    try:
        app_module.init_db()
        app_module.app.config["TESTING"] = True
        client = app_module.app.test_client()

        r = client.get("/login")
        check("GET /login -> 200", r.status_code == 200)

        r = client.get("/register")
        check("GET /register -> 200", r.status_code == 200)

        r = client.post("/register", data={
            "username": "smoketest", "password": "test1234", "confirm": "test1234",
        }, follow_redirects=False)
        check("POST /register -> redirect to /login", r.status_code == 302)

        r = client.post("/login", data={"username": "smoketest", "password": "test1234"},
                         follow_redirects=False)
        check("POST /login -> redirect (success)", r.status_code == 302)

        r = client.get("/")
        check("GET / (authenticated) -> 200", r.status_code == 200)

        # AI Server not reachable here -> both endpoints must fail *gracefully* (fallback), not 500
        r = client.get("/api/samplers")
        check("GET /api/samplers -> 200 with fallback list",
              r.status_code == 200 and isinstance(r.get_json(), list) and len(r.get_json()) > 0)

        r = client.get("/api/checkpoints")
        check("GET /api/checkpoints -> 200 (empty list, AI Server unreachable)",
              r.status_code == 200 and r.get_json() == [])

        png_bytes = make_test_png_bytes()
        r = client.post("/api/edit", data={
            "operation": "negative",
            "image": (io.BytesIO(png_bytes), "test.png"),
        }, content_type="multipart/form-data")
        check("POST /api/edit (negative) -> 200", r.status_code == 200)

        r = client.post("/api/edit", data={
            "operation": "resize", "width": "64", "height": "64",
            "image": (io.BytesIO(png_bytes), "test.png"),
        }, content_type="multipart/form-data")
        check("POST /api/edit (resize) -> 200", r.status_code == 200)

        r = client.post("/api/edit", data={
            "operation": "not_a_real_operation",
            "image": (io.BytesIO(png_bytes), "test.png"),
        }, content_type="multipart/form-data")
        check("POST /api/edit (unknown op) -> 400", r.status_code == 400)

        # First registered user is auto-promoted to admin
        r = client.get("/admin")
        check("GET /admin (as first/admin user) -> 200", r.status_code == 200)

        r = client.get("/logout", follow_redirects=False)
        check("GET /logout -> redirect", r.status_code == 302)

        r = client.get("/")
        check("GET / (unauthenticated) -> redirect to login", r.status_code == 302)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED: {failures}")
        sys.exit(1)
    print("All smoke checks passed.")
    print("NOTE: /api/generate and the AI-Server-connected path of /api/png-info were "
          "NOT exercised here — they need a reachable Forge instance (see docs/ai-server.md).")


if __name__ == "__main__":
    main()
