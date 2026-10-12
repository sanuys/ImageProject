# Backups

`webapp/database.db` (all users, prompts, history) and `webapp/static/outputs/`
(every generated/edited image) are the only state that isn't reproducible —
back them up together so a restore doesn't end up with orphaned DB rows
pointing at missing image files.

## Running a backup

```powershell
powershell -File scripts\backup.ps1
```

or on Linux/macOS:

```bash
bash scripts/backup.sh
```

Both write a timestamped zip to `backups/` (gitignored — these can get large
and contain user data, don't commit them) containing:

```
database.db
outputs/
outputs/edits/
```

Tested manually: `scripts/backup.ps1` was run against the real dev data and
verified (via `python -m zipfile`) to contain both `database.db` and the full
`outputs/` tree, including the `edits/` subfolder.

## Restoring

1. Stop the Flask app.
2. Unzip the backup.
3. Copy `database.db` to `webapp/database.db`.
4. Copy `outputs/` to `webapp/static/outputs/`.
5. Restart the app.

## Not yet done (see TODO.md section 5)
- No scheduled/automatic backups (cron/Task Scheduler) — these scripts are
  manual for now.
- No off-machine backup destination — zips currently land on the same disk as
  the data they're backing up.
