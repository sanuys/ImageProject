# Running the backend (`webapp/`)

This currently runs the whole app (auth, templates, static assets, image
generation/editing) as a single Flask process. See `TODO.md` for the plan to
split it into the distributed layout from `project.pdf`.

## 1. Install dependencies

```powershell
cd webapp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure environment

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | yes (unless `FLASK_DEBUG=true`) | generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FORGE_API_URL` | yes, for image generation to work | see `docs/ai-server.md` |
| `FORGE_API_USER` / `FORGE_API_PASS` | yes, must match Forge's `--api-auth` | see `docs/ai-server.md` |
| `FLASK_DEBUG` | no | `true` only for local dev (enables debugger + auto-reload + auto `SECRET_KEY`) |
| `PORT` | no | default `5000` |
| `ALLOWED_ORIGINS` | only once frontend is a separate origin | comma-separated list, enables CORS |
| `GENERATE_COOLDOWN_SECONDS` | no | per-user cooldown on `/api/generate`, default `3` |

`.env` is gitignored — never commit it. `.env.example` is the tracked template.

## 3. Run it

```powershell
python app.py
```

First run creates `database.db` (SQLite) and the `static/outputs/` /
`logs/` directories automatically. The **first user who registers is
auto-promoted to admin** (`/admin`).

App listens on `0.0.0.0:<PORT>` so other machines on the LAN can reach it —
useful once Nginx/frontend live on a different box (see `nginx/luma.conf`).

## 4. Verify it's working

```powershell
python tests/smoke_test.py
```

Runs registration/login/logout, image editing (resize/negative/etc.), and admin
routes against a throwaway DB — doesn't touch `database.db` and doesn't require
the AI Server to be reachable. `/api/generate` and the Forge-connected half of
`/api/png-info` aren't covered by this script since they need a real Forge
instance; test those manually via the UI once `docs/ai-server.md` is set up.

## 5. Logs

Written to `webapp/logs/app.log` (rotates at ~1MB, keeps 3 backups). Covers
registrations, logins/failed logins, generations, edits, admin deletions, and
AI-Server connection failures.

## Backups

See `docs/backup.md`.
