# Progress log — restructuring against `project.pdf`

Working through [`TODO.md`](../TODO.md). This entry covers everything done in
this pass: backend hardening, docs, tests, and deployment scaffolding. Each
item below was actually run and checked, not just written — see "How it was
verified" per section.

**Not done in this pass** (needs real hardware/decisions this session didn't
have): splitting frontend out of Flask (TODO section 1), running Nginx for
real across machines (section 2), PostgreSQL migration, LAN IP assignment.
Those are still open in `TODO.md`.

## 1. Config & secrets (previous session)
`SECRET_KEY`, `FORGE_API_URL`, `FORGE_API_USER`, `FORGE_API_PASS` moved from
hardcoded values in `app.py` into environment variables loaded via
`python-dotenv`. See `webapp/.env.example`.

**How to use:** copy `webapp/.env.example` to `webapp/.env` and fill it in
(never commit `.env` — it's gitignored). Full instructions in
[`docs/setup.md`](setup.md).

## 2. Logging
Added a rotating file logger (`webapp/logs/app.log`, 1MB per file, 3 backups
kept) alongside Flask's console output. Logs: user registration, login
success/failure, image generation, image edits, admin deletions, and AI-Server
connection failures — this satisfies the "Logging" deliverable called out for
the Flask Backend role in `project.pdf`.

**How to use:** just run the app; log lines appear in `webapp/logs/app.log`
automatically. No config needed.

**Verified:** ran the smoke test suite and a real `python app.py` boot; both
produced expected log lines, confirmed by reading `logs/app.log` directly.

## 3. CORS support
Added `flask-cors`, wired to an `ALLOWED_ORIGINS` env var (comma-separated).
Currently inert (no origins configured) since frontend and backend are still
one process — this is groundwork for TODO section 1, not something you need
to touch yet.

**How to use:** once the frontend is split onto its own host, set
`ALLOWED_ORIGINS=http://<frontend-ip>` in `webapp/.env`.

## 4. Rate limiting on `/api/generate`
Per-user cooldown (default 3 seconds, configurable via
`GENERATE_COOLDOWN_SECONDS`) to stop a user from spamming the AI Server with
overlapping requests. Returns HTTP 429 with a Thai message telling the user
how many seconds to wait.

**How to use:** nothing to do by default. Tune `GENERATE_COOLDOWN_SECONDS` in
`.env` if 3 seconds is too strict/loose for your AI Server's actual generation
time.

## 5. Defensive fix in `/api/edit`
Added an `else` branch to the operation dispatch so an unrecognized
`operation` value returns a clean 400 instead of a Pyright-flagged
possibly-unbound variable path. Not reachable today (the route already
rejects unknown operations earlier), but guards against someone adding a new
key to `OPERATION_LABELS` without adding the matching branch.

**Verified:** smoke test explicitly posts an unknown operation and asserts a
400 response.

## 6. Smoke tests
New `webapp/tests/smoke_test.py`. Runs against a throwaway SQLite DB and
throwaway output folders (via `tempfile`), so it's safe to run any time and
never touches your real `database.db` or `static/outputs/`.

Covers: register, login, index page, `/api/samplers` fallback,
`/api/checkpoints` graceful-empty-list, `/api/edit` for all 4 operations plus
rejection of an unknown operation, `/admin` access as the auto-promoted first
user, logout, and post-logout redirect.

**Does not cover** `/api/generate` or the Forge-connected half of
`/api/png-info` — both need a real, reachable AI Server, which wasn't
available in this session. Test those manually through the UI once
`docs/ai-server.md` is followed.

**How to use:**
```powershell
cd webapp
python tests/smoke_test.py
```
Exits non-zero and prints which checks failed if anything breaks.

**Verified:** ran it twice in this session — all 13 checks passed both times.

## 7. Nginx config scaffold
`nginx/luma.conf` — reverse-proxy config matching the architecture in
`project.pdf` (routes `/api/`, `/login`, `/logout`, `/register`, `/admin` to
the backend; everything else to the frontend). Includes upstream blocks with
placeholder IPs to swap for your team's real machine addresses.

**Not tested against a live Nginx** — no `nginx` binary was available in this
dev environment. Run `nginx -t` on the actual reverse-proxy machine before
trusting it, and note the comment in the file: as written today it assumes
frontend and backend are already split onto separate hosts, which hasn't
happened yet (TODO section 1).

## 8. AI Server documentation
`docs/ai-server.md` — exact Forge/Stability Matrix launch flags
(`--api --api-auth user:pass --listen --port`), a curl command to verify
reachability, and a table mapping backend routes to Forge API endpoints.

**How to use:** whoever sets up the AI Engineer's machine follows this doc,
then fills in `FORGE_API_URL` / `FORGE_API_USER` / `FORGE_API_PASS` in
`.env` on the backend machine to match.

## 9. Backup scripts
`scripts/backup.ps1` (Windows) and `scripts/backup.sh` (Linux/macOS) — zip
`database.db` + `static/outputs/` (including `edits/`) into a timestamped
archive under `backups/` (gitignored).

**How to use:**
```powershell
powershell -File scripts\backup.ps1
```
```bash
bash scripts/backup.sh
```
To restore: unzip, copy `database.db` back to `webapp/database.db` and
`outputs/` back to `webapp/static/outputs/`, restart the app.

**Verified — and this caught a real bug:** the first version of
`backup.ps1` used an em-dash (`—`) in a couple of comments/messages. Windows
PowerShell 5.1, reading a UTF-8 file without a BOM under the system codepage,
silently mis-parsed the file — the zip only ever contained `database.db`, the
`outputs/` copy silently vanished, with no error printed. Root-caused by
bisecting with debug output, fixed by removing all non-ASCII characters from
the script. Re-ran it and confirmed with `python -m zipfile` that the output
zip contains `database.db`, `outputs/.gitkeep`, `outputs/<image>.png`, and all
4 files under `outputs/edits/`. **Takeaway for the team:** avoid em-dashes/
curly quotes in `.ps1` files — plain ASCII only.

## 10. README and TODO updates
`README.md` now has the architecture diagram, quick start, a docs table, and
the role table from `project.pdf`. `TODO.md` checkboxes updated to reflect
everything above — grep it for `[x]` vs `[ ]` to see exactly what's left.

## What to do next
See `TODO.md` sections 0–2: the deployment-shape decision (3-PC vs 4-PC) and
the frontend/Flask split are the two blocking decisions before the rest of the
distributed-system work (real Nginx testing, PostgreSQL migration if 4-PC) can
proceed.
