# Backs up webapp/database.db + webapp/static/outputs/ into a timestamped zip
# under backups/ (gitignored). Run from anywhere; paths are resolved relative
# to this script's location.
#
# Usage:
#   powershell -File scripts\backup.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$webapp = Join-Path $repoRoot "webapp"
$backupsDir = Join-Path $repoRoot "backups"

if (-not (Test-Path $backupsDir)) {
    New-Item -ItemType Directory -Path $backupsDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stagingDir = Join-Path $env:TEMP "luma-backup-$timestamp"
New-Item -ItemType Directory -Path $stagingDir | Out-Null

$dbPath = Join-Path $webapp "database.db"
if (Test-Path $dbPath) {
    Copy-Item -Path $dbPath -Destination (Join-Path $stagingDir "database.db")
} else {
    Write-Warning "database.db not found at $dbPath - skipping"
}

$outputsPath = Join-Path $webapp "static\outputs"
if (Test-Path $outputsPath) {
    Copy-Item -Path $outputsPath -Destination (Join-Path $stagingDir "outputs") -Recurse
} else {
    Write-Warning "static/outputs not found at $outputsPath - skipping"
}

$zipPath = Join-Path $backupsDir "luma-backup-$timestamp.zip"
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath
Remove-Item -Path $stagingDir -Recurse -Force

Write-Host "Backup written to $zipPath"
