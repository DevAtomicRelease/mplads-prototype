# One-command local launch for MPLADS-GUARD (SIH PS 26102, six_source stack).
# Creates the venv and builds the dataset + front-end on first run, then serves
# the loopback investigation app. Everything stays on this device.
#
#   .\run.ps1                # build if needed, then serve at http://127.0.0.1:8766/
#   .\run.ps1 -Rebuild       # force a fresh dataset build first
#   .\run.ps1 -Port 8770     # use a different local port
param([int]$Port = 8766, [switch]$Rebuild)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$py = Join-Path $root '.venv/Scripts/python.exe'

if (-not (Test-Path $py)) {
    Write-Host 'Creating virtual environment and installing dependencies...'
    python -m venv (Join-Path $root '.venv')
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r (Join-Path $root 'six_source/requirements.txt')
}

$audit = Join-Path $root 'six_source/local/audit.json'
if ($Rebuild -or -not (Test-Path $audit)) {
    Write-Host 'Building connected dataset (all cohorts)...'
    & $py (Join-Path $root 'six_source/build.py')
    & $py (Join-Path $root 'six_source/patterns.py')
    & $py (Join-Path $root 'six_source/validate.py')
    & $py (Join-Path $root 'six_source/workbook.py')
}

$dist = Join-Path $root 'mplads-prototype/dist/six/six.html'
if (-not (Test-Path $dist)) {
    Write-Host 'Building front-end...'
    Push-Location (Join-Path $root 'mplads-prototype')
    try {
        if (-not (Test-Path 'node_modules/vite/bin/vite.js')) { npm ci }
        npm run build:six
    } finally { Pop-Location }
}

Write-Host "MPLADS-GUARD ready at http://127.0.0.1:$Port/  (Ctrl+C to stop)"
& $py (Join-Path $root 'six_source/serve.py') --port $Port
