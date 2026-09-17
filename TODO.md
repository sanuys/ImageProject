# TODO — Restructure to match `project.pdf` (LUMA distributed system)

Target architecture from `project.pdf`:

```
Browser → Nginx (reverse proxy)
            ├── Frontend (HTML/CSS/JS)      192.168.1.10
            └── Backend (Flask)             192.168.1.20
                    ├── AI Server (Forge)    192.168.1.30
                    └── Database (SQLite)    192.168.1.20
```

Current state: everything (templates, static assets, API, DB) runs as a single
Flask process in `webapp/`. No Nginx, no separate frontend service, no AI-server
machine of its own yet.

## 0. Decide the deployment shape
- [ ] Pick 3-PC vs 4-PC layout from page 2 of `project.pdf` (3-PC: Frontend+Nginx /
      Forge AI / Flask+SQLite — vs 4-PC: adds a dedicated PostgreSQL machine)
- [ ] Assign real LAN IPs to each teammate's machine and write them down somewhere
      the whole team can see (README or shared doc)
- [ ] Confirm who owns which machine, matching the role table in `project.pdf`

## 1. Split frontend out of Flask
- [ ] Decide: static HTML/CSS/JS frontend that calls the Flask API over the
      network, vs keep Jinja templates but move them onto the frontend host
      behind Nginx (the diagram implies frontend and backend are separate
      services, not one process)
- [ ] Extract `webapp/templates/*.html` + `webapp/static/` into a standalone
      `frontend/` directory (or repo) servable independently of Flask
- [ ] Replace Jinja `{{ }}` / `{% %}` templating with client-side rendering or a
      lightweight static templater, since the frontend will no longer run inside
      the Flask process
- [ ] Point frontend's `fetch()` calls at the backend's LAN address
      (`http://192.168.1.20:5000/api/...`) instead of relative paths
- [ ] Handle CORS on the Flask side once frontend and backend are on different
      origins (`flask-cors` or manual headers)

## 2. Set up Nginx reverse proxy
- [ ] Install Nginx on the designated proxy machine (course material: Network
      subject content — routing/reverse proxy)
- [ ] Configure `location /` → frontend host, `location /api/` → backend host
- [ ] Decide whether Nginx also serves `static/outputs/` directly (faster) or
      proxies image requests through Flask
- [x] Add the Nginx config file to the repo (`nginx/luma.conf`) so it's
      versioned, not just live on one machine — **scaffolded only, not tested
      against a live Nginx** (none available in the dev environment this was
      written in). Verify with `nginx -t` on the real proxy machine.
- [ ] Test cross-machine requests end-to-end (browser → Nginx → frontend/backend
      on different PCs, different IPs)

## 3. Backend (Flask) — finish hardening
- [x] Move `SECRET_KEY` / Forge credentials to `.env` (done)
- [ ] Restrict Flask to only bind where needed once behind Nginx (still
      `0.0.0.0` for LAN access, but no longer directly exposed to the browser)
- [x] Add request logging (per the role table: "Authentication, API, Database,
      **Logging**" is explicitly listed as a Backend deliverable) — rotating
      file logger at `webapp/logs/app.log`, covers register/login/failed
      login/generate/edit/admin-delete/AI-Server errors
- [x] Add basic rate limiting on `/api/generate` (per-user cooldown via
      `GENERATE_COOLDOWN_SECONDS`, default 3s, returns HTTP 429). Input
      validation on that route was already present (clamped steps/cfg/size).
- [ ] If moving to the 4-PC layout: swap SQLite (`sqlite3` + `database.db`) for
      PostgreSQL (`psycopg2` + connection config via `.env`)

## 4. AI Server
- [x] Document the exact Forge/Stability Matrix setup steps (`--api`,
      `--api-auth`, model/checkpoint files needed) in
      [`docs/ai-server.md`](docs/ai-server.md) so the AI Engineer's machine can
      be rebuilt/reproduced
- [ ] Confirm `ALLOWED_CHECKPOINTS` in `app.py` matches whatever models actually
      ship with the AI server machine used for grading/demo
- [ ] Look at request queueing if multiple users can hit `/api/generate`
      concurrently (role table calls this out explicitly: "Queue")
- [ ] Decide whether LoRA support (also listed in the role table) is in scope —
      not present in `app.py` yet

## 5. QA / DevOps
- [x] Write a `docs/` folder — [`docs/setup.md`](docs/setup.md) (install/run/env
      vars/smoke test), [`docs/ai-server.md`](docs/ai-server.md),
      [`docs/backup.md`](docs/backup.md). Still missing: how the 3/4 machines
      are networked together (depends on section 0/1 decisions not made yet)
- [x] Basic smoke tests — [`webapp/tests/smoke_test.py`](webapp/tests/smoke_test.py),
      covers auth, `/api/edit` (all 4 ops incl. unknown-op rejection), `/admin`,
      logout, against a throwaway DB. **Does not** cover `/api/generate` or the
      Forge-connected half of `/api/png-info` — those need a reachable AI
      Server, which wasn't available when this was written
- [ ] Deployment steps/scripts (e.g. per-machine `setup.ps1`/`setup.sh` or a
      short runbook) instead of manual `python app.py`
- [ ] Admin dashboard already exists (`/admin`) — confirm it satisfies the
      "Dashboard" deliverable, extend if needed (e.g. show per-machine health)
- [x] Backup strategy — [`scripts/backup.ps1`](scripts/backup.ps1) /
      [`scripts/backup.sh`](scripts/backup.sh), zips `database.db` +
      `static/outputs/` to `backups/` (gitignored). Tested and verified
      (contents checked with `python -m zipfile`). No scheduling/off-machine
      copy yet — see [`docs/backup.md`](docs/backup.md)

## 6. Repo hygiene
- [x] `.env` / secrets excluded from git (done)
- [ ] Decide whether `project.pdf` should be committed (currently untracked) or
      left local/gitignored
- [x] Flesh out `README.md` with the architecture diagram, quick start, links
      to `docs/`, and the role table
- [ ] Once frontend is extracted, revisit repo layout — likely
      `frontend/`, `backend/` (renamed from `webapp/`), `nginx/`, `docs/`

## 7. Team assignment (per `project.pdf` role table)
- [ ] คนที่ 1 — UX/UI Frontend: owns section 1 above
- [ ] คนที่ 2 — Flask Backend: owns sections 3 (+ 5's API tests)
- [ ] คนที่ 3 — AI Engineer: owns section 4
- [ ] คนที่ 4 — QA/DevOps: owns section 5
- [ ] คนที่ 5 (ถ้ามี) — Reverse Proxy/Routing: owns section 2
