#!/usr/bin/env bash
# Backs up webapp/database.db + webapp/static/outputs/ into a timestamped zip
# under backups/ (gitignored).
#
# Usage:
#   bash scripts/backup.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
webapp="$repo_root/webapp"
backups_dir="$repo_root/backups"
mkdir -p "$backups_dir"

timestamp="$(date +%Y%m%d-%H%M%S)"
staging_dir="$(mktemp -d)"
trap 'rm -rf "$staging_dir"' EXIT

if [ -f "$webapp/database.db" ]; then
    cp "$webapp/database.db" "$staging_dir/database.db"
else
    echo "WARNING: database.db not found at $webapp/database.db - skipping" >&2
fi

if [ -d "$webapp/static/outputs" ]; then
    cp -r "$webapp/static/outputs" "$staging_dir/outputs"
else
    echo "WARNING: static/outputs not found at $webapp/static/outputs - skipping" >&2
fi

zip_path="$backups_dir/luma-backup-$timestamp.zip"
(cd "$staging_dir" && zip -r -q "$zip_path" .)

echo "Backup written to $zip_path"
