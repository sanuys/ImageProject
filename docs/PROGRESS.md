# Progress log — restructuring against `project.pdf`

> **Read this first.** Sections 1–10 below describe the *first* pass, when the
> whole app was still one Flask process in `webapp/`. That folder, its paths
> (`webapp/.env`, `webapp/logs/`, `webapp/tests/`, `static/outputs/`) and
> `nginx/luma.conf` no longer exist — they are kept here as history only.
> For the current layout see [`README.md`](../README.md) and the
> "Pass 2" and "Pass 3" sections at the end of this file.

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

---

# Pass 2 — after the 4-machine split

The app was split into `pc1-frontend/`, `pc2-backend/`, `pc3-ai/`,
`pc4-database/` and `single-pc/`. A review of that split found security holes,
features lost in the move, and files still describing `webapp/`. This pass
fixed the following.

## 11. Secrets out of the code
`SECRET_KEY`, the Forge user/password and `DB_TOKEN` were hardcoded in
`pc2-backend/config.py` and `pc4-database/db_server.py`. They are now read
from a `.env` file next to each program (templates: `.env.example`). PC2 and
PC4 refuse to start without `DB_TOKEN`; a missing `SECRET_KEY` is replaced by
a random one per start. Flask debug mode is off unless `FLASK_DEBUG=true`.

**Still to do by hand:** the old values are in git history — choose new ones.

## 12. XSS and image access
`escapeHtml()` in `pc1-frontend/html/js/common.js` did not escape quotes but
was used inside HTML attributes, so a prompt could inject script into the
admin page. It now escapes `& < > " '`. `/media/...` now requires login.

**Not verified in a browser** — no Node/browser was available to run the JS.

## 13. Single-PC storage path
`single-pc/run_single_pc.py` set a config value nothing read, so images went
to `pc4-database/storage/` instead of `single-pc/data/storage/`. Fixed by
passing `STORAGE_DIR` to the database server.

## 14. Logging and generate cooldown restored
Both existed in `webapp/app.py` (sections 2 and 4 above) and were lost in the
split. Back in `pc2-backend/app.py`: rotating `logs/app.log`, and
`GENERATE_COOLDOWN_SECONDS` (HTTP 429). The cooldown check is now behind a
lock and runs after input validation.

## 15. Smoke test rewritten
`tests/smoke_test.py` replaces `webapp/tests/smoke_test.py`, which imported a
module that no longer exists. It starts the real Database Server on a free
port with throwaway data, drives the real Backend through Flask's test client,
and fakes the AI Server (both "up" and "unreachable").

**Verified:** 70 checks pass (first written here as 71 — a miscount). **Not covered:** real generation (PC2 → PC3)
and the Nginx layer.

## 16. Backup scripts repointed
`scripts/backup.ps1` / `backup.sh` looked for `webapp/database.db`, printed a
warning and wrote an empty zip. They now back up `pc4-database/database.db` +
`pc4-database/storage/` (or `single-pc/data/` with `-SinglePc`) and stop with
an error if there is no database.

**Verified:** `backup.ps1 -SinglePc` on freshly generated data — the zip
contained `database.db` and the image under `storage/outputs/edits/`; without
data it exits 1 and writes nothing. `backup.sh` was **not run** (no `zip` on
the dev machine).

## 17. Stale files removed
Deleted: `nginx/luma.conf` (superseded by
`pc1-frontend/nginx/imageproject.conf`), `docs/setup.md`, `docs/ai-server.md`
and `docs/run/` (superseded by the README in each `pc*` folder),
`webapp/.env.example`, `webapp/tests/`. `README.md`, `TODO.md` and
`docs/backup.md` were rewritten for the current layout.

---

# Pass 3 — report, real machines, first incident (13–14 Oct)

## 18. Project report and tech stack
`docs/REPORT.md` (Thai): introduction, architecture and design reasons, each
machine in detail, the 12 image-processing methods with formulas, security,
testing, installation/backup, role table, limitations, conclusion. A Tech
Stack table was added to both the report (section 2.2) and `README.md`.
The team has since filled in the cover (members and machine assignment).

**Still empty in the report:** the real-machine results table (section 6.2)
and the "ผู้รับผิดชอบ" column (section 8).

## 19. Changes by the team
- `pc2-backend/db_client.py`: removed the unused no-op `commit()` / `close()`
  methods (nothing in `app.py` called them).
- `pc4-database/db_server.py`, `schema.py`: explanatory comments added; no
  change to routes or behaviour.
- `pc2-backend/config.py`: addresses updated for the current network —
  PC1 `172.20.56.117`, PC3 `172.20.56.108`, PC4 `172.20.56.113`.
- The local `webapp/` folder was deleted; everything is committed on the
  `cleanup` branch.

**Verified:** `tests/smoke_test.py` re-run after these edits on 14 Oct — all
70 checks pass. (Section 15 originally said 71; that was a miscount, the test
file has not changed.)

**Not updated yet:** the address table in `README.md`, section 2.1 of the
report and several comments still show the old addresses — see `TODO.md`
section 0.

## 20. First run on the real machines (14 Oct)
Evidence is `pc2-backend/logs/app.log` on PC2 (the logging restored in
section 14) plus direct checks from PC2:

- **PC2 → PC4 works.** `/health` on PC4 answered with real data (2 users,
  12 generations, 26 edits at 07:51) and read queries took about 0.05 s.
- **PC2 → PC3 works.** 8 images generated at 1024×1024 with both
  allow-listed checkpoints, taking 34–116 s each (most 40–85 s).
- Not established from the log: whether those requests came through Nginx
  on PC1 or straight to port 5000.

## 21. Incident: PC4 read timeouts (14 Oct, 07:28–07:59)
About 25 requests (login, register, `/api/me`) failed with
`Read timed out (read timeout=15)` from the Database Server.

**What was ruled out**, by testing from PC2 at 07:51: the network (TCP
connect in 0.08 s), the token (a wrong token got an immediate 401) and the IP
allow-list (queries with the real token succeeded). So PC4 was reachable and
accepting connections, but slow to answer.

**What was observed:** one `/health` call took 4 s and one write that changes
zero rows took 13.2 s, while the calls right after each took 0.05 s. The
stall is intermittent and is on PC4, not on the network.

**Cause: not confirmed** — the investigation was stopped before looking at
PC4 itself. Candidates, in the order worth checking, are listed in `TODO.md`
section 3 (paused console window, `database.db` open in another program,
PC2's 15 s timeout being shorter than SQLite's 30 s busy timeout).

A separate short burst at 09:17 (8 errors) was different: PC4 answered 403
"IP 172.20.56.107 not allowed", i.e. the allow-list on PC4 was briefly wrong.
It was working again by 09:19.

## What to do next
See `TODO.md`. In order: find the cause of the PC4 stalls (section 3), take a
first real backup of PC4 (section 5), bring the addresses in the docs back in
line with `config.py` (section 0), then the open security items (rotate
secrets, image ownership check, server-side checkpoint validation) and the
queue (section 4).
