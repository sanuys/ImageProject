# Backups

All state that can't be regenerated lives on **PC4** (the database machine):

| What | Where |
|---|---|
| Users, prompts, history | `pc4-database/database.db` |
| Every generated image | `pc4-database/storage/outputs/` |
| Every edited image | `pc4-database/storage/outputs/edits/` |

Back them up together, so a restore doesn't leave database rows pointing at
missing image files. In single-PC mode the same two things live under
`single-pc/data/` instead.

## Running a backup

On PC4 (Windows):

```powershell
powershell -File scripts\backup.ps1
```

Single-PC mode:

```powershell
powershell -File scripts\backup.ps1 -SinglePc
```

On Linux/macOS use `bash scripts/backup.sh` (or `--single-pc`); it needs `zip`.

Each run writes `backups/luma-backup-<timestamp>.zip` (gitignored — these get
large and contain user data, don't commit them) containing:

```
database.db
storage/outputs/
storage/outputs/edits/
```

The scripts stop with an error if `database.db` isn't there, instead of
writing an empty zip — so running them on the wrong machine fails loudly.

For a guaranteed-consistent copy, run the backup while nobody is using the
site (or stop `db_server.py` first): the script copies `database.db` as a
plain file, and a copy taken in the middle of a write can be incomplete.

## Restoring

1. Stop the Database Server (`pc4-database/start.bat` window), or the
   single-PC window.
2. Unzip the backup **into the data folder** — `pc4-database/` (or
   `single-pc/data/`). The zip has the same layout as that folder, so
   `database.db` and `storage/` land in the right place.
3. Start the server again.

## Not yet done

- No scheduled/automatic backups (Task Scheduler / cron) — manual for now.
- No off-machine destination — zips land on the same disk as the data.
- `pc2-backend/logs/` (the Backend's log files) is not included; it lives on
  PC2, not PC4.
