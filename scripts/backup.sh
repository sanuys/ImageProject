#!/usr/bin/env bash
# Backs up the database + all image files into a timestamped zip under
# backups/ (gitignored). Run it on the machine that owns the data (PC4).
#
#   default       : pc4-database/database.db  + pc4-database/storage/
#   --single-pc   : single-pc/data/database.db + single-pc/data/storage/
#
# The zip mirrors the data folder (database.db, storage/outputs/...), so a
# restore is just "unzip into the data folder". See docs/backup.md.
#
# Usage:
#   bash scripts/backup.sh
#   bash scripts/backup.sh --single-pc
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "${1:-}" = "--single-pc" ]; then
    data_dir="$repo_root/single-pc/data"
else
    data_dir="$repo_root/pc4-database"
fi
backups_dir="$repo_root/backups"

if ! command -v zip >/dev/null 2>&1; then
    echo "ERROR: 'zip' is not installed (on Windows use scripts/backup.ps1 instead)" >&2
    exit 1
fi

# Refuse to write an empty zip: a backup with nothing in it looks like success.
if [ ! -f "$data_dir/database.db" ]; then
    echo "ERROR: database.db not found at $data_dir/database.db - nothing to back up." >&2
    echo "       Run this on the machine that holds the data (PC4), or pass --single-pc." >&2
    exit 1
fi

mkdir -p "$backups_dir"
timestamp="$(date +%Y%m%d-%H%M%S)"
staging_dir="$(mktemp -d)"
trap 'rm -rf "$staging_dir"' EXIT

cp "$data_dir/database.db" "$staging_dir/database.db"

if [ -d "$data_dir/storage" ]; then
    cp -r "$data_dir/storage" "$staging_dir/storage"
else
    echo "WARNING: storage folder not found at $data_dir/storage - backing up database.db only" >&2
fi

zip_path="$backups_dir/luma-backup-$timestamp.zip"
(cd "$staging_dir" && zip -r -q "$zip_path" .)

echo "Backup written to $zip_path"
