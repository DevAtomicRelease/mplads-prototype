# MPLADS-GUARD single launcher (SIH PS 26102).
# Checks prerequisites, builds the dataset and front-end only when missing or stale,
# starts the local loopback app and opens it when it is actually ready, and stops the
# process it started on exit. It never installs global software, changes system settings,
# or stops unrelated processes. Everything stays on 127.0.0.1.
#
#   .\run.ps1                 build if needed, then serve at http://127.0.0.1:8766/
#   .\run.ps1 -Rebuild        force a fresh dataset build first
#   .\run.ps1 -Port 8770      use a different local port
[CmdletBinding()]
param([int]$Port = 8766, [switch]$Rebuild, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$py   = Join-Path $root '.venv/Scripts/python.exe'
$six  = Join-Path $root 'six_source'
$web  = Join-Path $root 'mplads-prototype'
$audit = Join-Path $six 'local/audit.json'
$pidFile = Join-Path $six 'local/.serve.pid'

function Fail($msg) { Write-Host ""; Write-Host "  X  $msg" -ForegroundColor Red; exit 1 }
function Ok($msg)   { Write-Host "  OK $msg" -ForegroundColor DarkGreen }
function Step($cmd, $label) {
    Write-Host "  .. $label"
    & $cmd
    if ($LASTEXITCODE -ne 0) { Fail "$label failed (exit $LASTEXITCODE). Nothing was started; fix the error above and re-run." }
}
function Have($name) { $null -ne (Get-Command $name -ErrorAction SilentlyContinue) }
function Sha($path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower() }

Write-Host "MPLADS-GUARD launcher" -ForegroundColor Cyan

# --- Prerequisites -----------------------------------------------------------
if (-not (Test-Path $py)) {
    if (-not (Have 'python')) { Fail "Python 3.12 was not found on PATH. Install it (tick 'Add to PATH'), then re-run. This first-time step needs an internet connection to download packages." }
    Write-Host "First-time setup: creating the Python environment and downloading dependencies (needs internet)..." -ForegroundColor Yellow
    Step { python -m venv (Join-Path $root '.venv') } 'Create virtual environment'
    Step { & $py -m pip install --quiet --upgrade pip } 'Upgrade pip'
    Step { & $py -m pip install --quiet -r (Join-Path $six 'requirements.txt') } 'Install Python dependencies'
}
& $py -c "import numpy,pandas,sklearn,openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "First-time setup: installing Python dependencies (needs internet)..." -ForegroundColor Yellow
    Step { & $py -m pip install --quiet -r (Join-Path $six 'requirements.txt') } 'Install Python dependencies'
}
Ok "Python environment ready"

# Raw dataset present? (needed only when a build is required)
$cohorts = @('Lok Sabha','Rajya_Sabha_sitting','Rajya_Sabha_retired')
$haveData = $true
foreach ($c in $cohorts) { if (-not (Test-Path (Join-Path $root "Dataset/$c/03_works_recommended.csv"))) { $haveData = $false } }

# --- Decide whether the dataset build is missing or stale --------------------
$needBuild = $Rebuild.IsPresent -or -not (Test-Path $audit)
$staleReason = $null
if (-not $needBuild) {
    try {
        $meta = Get-Content $audit -Raw | ConvertFrom-Json
        foreach ($s in $meta.sources) {
            $p = Join-Path $root ("Dataset/" + $s.file)
            if (-not (Test-Path $p)) { $staleReason = "source $($s.file) is missing"; break }
            if ((Sha $p) -ne $s.sha256) { $staleReason = "source $($s.file) changed since the build"; break }
        }
        if (-not $staleReason) {
            if ((Sha (Join-Path $six 'build.py'))  -ne $meta.pipeline_sha256) { $staleReason = 'build.py changed since the build' }
            elseif ((Sha (Join-Path $six 'common.py')) -ne $meta.common_sha256) { $staleReason = 'common.py changed since the build' }
        }
    } catch { $staleReason = 'existing build manifest is unreadable' }
    if ($staleReason) { $needBuild = $true; Write-Host "  !! Rebuilding: $staleReason" -ForegroundColor Yellow }
}

if ($needBuild) {
    if (-not $haveData) { Fail "The dataset needs building but the source CSVs are missing. Place the six CSVs for each cohort under Dataset/<cohort>/ (see README), then re-run." }
    Write-Host "Building the connected dataset and analysis (this can take a few minutes)..."
    Step { & $py (Join-Path $six 'build.py') } 'Build dataset (21 reconciliation checks)'
    Step { & $py (Join-Path $six 'patterns.py') } 'Relations & patterns report'
    Step { & $py (Join-Path $six 'validate.py') } 'Offline A/B validation'
    Step { & $py (Join-Path $six 'workbook.py') } 'Excel review workbook'
    Ok "Dataset built"
} else {
    Ok "Dataset build is present and current"
}

# --- Build the front-end if missing or stale ---------------------------------
$dist = Join-Path $web 'dist/index.html'
$webStale = -not (Test-Path $dist)
if (-not $webStale) {
    $distTime = (Get-Item $dist).LastWriteTimeUtc
    $srcNewest = Get-ChildItem (Join-Path $web 'app'),(Join-Path $web 'index.html'),(Join-Path $web 'vite.config.ts') -Recurse -File -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($srcNewest -and $srcNewest.LastWriteTimeUtc -gt $distTime) { $webStale = $true }
}
if ($webStale) {
    if (-not (Have 'npm')) { Fail "The front-end needs building but Node.js/npm was not found on PATH. Install Node.js 22+ and re-run (first-time step; needs internet for 'npm ci')." }
    Push-Location $web
    try {
        if (-not (Test-Path 'node_modules/vite/bin/vite.js')) {
            Write-Host "First-time setup: installing front-end dependencies (needs internet)..." -ForegroundColor Yellow
            Step { npm ci } 'npm ci'
        }
        Step { npm run build } 'Build front-end'
    } finally { Pop-Location }
    Ok "Front-end built"
} else {
    Ok "Front-end build is present and current"
}

# --- Port check --------------------------------------------------------------
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($busy) {
    try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2 } catch { $h = $null }
    if ($h -and $h.application -eq 'MPLADS Six Source') {
        Ok "MPLADS-GUARD is already running at http://127.0.0.1:$Port/"; if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port/" }; exit 0
    }
    Fail "Port $Port is already in use by another program. Re-run with -Port <number> to choose a free local port."
}

# --- Start the server, wait until ready, open the browser --------------------
# run.ps1 already verified freshness this run, so serve skips its own re-hash.
$proc = Start-Process -FilePath $py -ArgumentList @((Join-Path $six 'serve.py'),'--port',"$Port",'--no-verify') -WorkingDirectory $six -PassThru -NoNewWindow
Set-Content -LiteralPath $pidFile -Value $proc.Id -Encoding ascii
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    if ($proc.HasExited) { Fail "The local service exited during startup (exit $($proc.ExitCode)). Re-run to see the error." }
    try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 1; if ($h.application -eq 'MPLADS Six Source') { $ready = $true; break } } catch { }
    Start-Sleep -Milliseconds 350
}
if (-not $ready) { try { Stop-Process -Id $proc.Id -Force } catch {}; Fail "The service did not become ready in time." }

Write-Host ""
Ok "MPLADS-GUARD is ready at http://127.0.0.1:$Port/"
Write-Host "     The app processes data locally; your review notes stay on this computer."
Write-Host "     Press Ctrl+C here (or run STOP.cmd) to stop." -ForegroundColor DarkGray
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port/" }
try {
    Wait-Process -Id $proc.Id
} finally {
    if (-not $proc.HasExited) { try { Stop-Process -Id $proc.Id -Force } catch {} }
    Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
    Write-Host "Stopped."
}
