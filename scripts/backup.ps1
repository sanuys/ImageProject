# Backs up the database + all image files into a timestamped zip under
# backups/ (gitignored). Run it on the machine that owns the data (PC4).
#
#   default     : pc4-database\database.db  + pc4-database\storage\
#   -SinglePc   : single-pc\data\database.db + single-pc\data\storage\
#
# The zip mirrors the data folder (database.db, storage\outputs\...), so a
# restore is just "unzip into the data folder". See docs\backup.md.
#
# Usage:
#   powershell -File scripts\backup.ps1
#   powershell -File scripts\backup.ps1 -SinglePc
#
# NOTE: keep this file plain ASCII. Windows PowerShell 5.1 mis-parses UTF-8
# without a BOM, which once made this script silently skip files.

param([switch]$SinglePc)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if ($SinglePc) {
    $dataDir = Join-Path $repoRoot "single-pc\data"
} else {
    $dataDir = Join-Path $repoRoot "pc4-database"
}
$backupsDir = Join-Path $repoRoot "backups"

$dbPath = Join-Path $dataDir "database.db"
$storagePath = Join-Path $dataDir "storage"

# Refuse to write an empty zip: a backup with nothing in it looks like success.
if (-not (Test-Path $dbPath)) {
    Write-Error "database.db not found at $dbPath - nothing to back up. Run this on the machine that holds the data (PC4), or pass -SinglePc."
}

if (-not (Test-Path $backupsDir)) {
    New-Item -ItemType Directory -Path $backupsDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stagingDir = Join-Path $env:TEMP "luma-backup-$timestamp"
New-Item -ItemType Directory -Path $stagingDir | Out-Null

try {
    Copy-Item -Path $dbPath -Destination (Join-Path $stagingDir "database.db")

    if (Test-Path $storagePath) {
        Copy-Item -Path $storagePath -Destination (Join-Path $stagingDir "storage") -Recurse
    } else {
        Write-Warning "storage folder not found at $storagePath - backing up database.db only"
    }

    $zipPath = Join-Path $backupsDir "luma-backup-$timestamp.zip"
    Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath
} finally {
    Remove-Item -Path $stagingDir -Recurse -Force
}

$fileCount = (Get-ChildItem -Path $storagePath -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "Backup written to $zipPath (database.db + $fileCount image file(s))"
