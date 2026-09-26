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
param([ValidateRange(1,65535)][int]$Port = 8766, [switch]$Rebuild, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$py   = Join-Path $root '.venv/Scripts/python.exe'
$six  = Join-Path $root 'six_source'
$web  = Join-Path $root 'mplads-prototype'
$audit = Join-Path $six 'local/audit.json'
$pidFile = Join-Path $six "local/.serve-$Port.json"

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

# --- Port check --------------------------------------------------------------
$busy = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if ($busy) {
    try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2 } catch { $h = $null }
    if ($h -and $h.application -eq 'MPLADS Six Source') {
        if($Rebuild){Fail 'Stop the running instance before forcing a rebuild, or use Prepare release in the frontend.'}
        Ok "MPLADS-GUARD is already running at http://127.0.0.1:$Port/"; if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port/" }; exit 0
    }
    Fail "Port $Port is already in use by another program. Re-run with -Port <number> to choose a free local port."
}


# --- Prerequisites -----------------------------------------------------------
if (-not (Test-Path $py)) {
    if (-not (Have 'python')) { Fail "Python 3.12 was not found on PATH. Install it (tick 'Add to PATH'), then re-run. This first-time step needs an internet connection to download packages." }
    Write-Host "First-time setup: creating the Python environment and downloading dependencies (needs internet)..." -ForegroundColor Yellow
    Step { python -m venv (Join-Path $root '.venv') } 'Create virtual environment'
    Step { & $py -m pip install --quiet --upgrade pip } 'Upgrade pip'
    Step { & $py -m pip install --quiet -r (Join-Path $six 'requirements.txt') } 'Install Python dependencies'
}
& $py -c "import sys,importlib.metadata as m;from pathlib import Path;req=[line.split('#',1)[0].strip() for line in Path(sys.argv[1]).read_text().splitlines()];installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()};sys.exit(0 if all(installed.get(x.split('==')[0].strip().lower().replace('_','-'))==x.split('==')[1].strip() for x in req if '==' in x) else 1)" (Join-Path $six 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    Write-Host "First-time setup: installing Python dependencies (needs internet)..." -ForegroundColor Yellow
    Step { & $py -m pip install --quiet -r (Join-Path $six 'requirements.txt') } 'Install Python dependencies'
}
Ok "Python environment ready"

# Raw dataset present? (needed only when a build is required)
$cohorts = @('Lok Sabha','Rajya_Sabha_sitting','Rajya_Sabha_retired')
$haveData = $true
foreach ($c in $cohorts) { if (-not (Test-Path (Join-Path $root "Dataset/$c/03_works_recommended.csv"))) { $haveData = $false } }

# Verify actual artifact bytes, code and raw inputs. Always prepare into a fresh release.
& $py (Join-Path $six 'preflight.py')
$needBuild = $Rebuild.IsPresent -or $LASTEXITCODE -ne 0
if($needBuild) {
    if(-not $haveData){Fail 'Source CSVs are missing. Obtain the authorized local Dataset folders (see README).'}
    Step { & $py (Join-Path $six 'prepare_release.py') } 'Prepare and atomically activate verified release'
} else { Ok 'Verified active data release' }

# --- Build the front-end if missing or stale ---------------------------------
$dist = Join-Path $web 'dist/index.html'
$webStale = -not (Test-Path $dist)
if (-not $webStale) {
    $distTime = (Get-Item $dist).LastWriteTimeUtc
    $srcNewest = Get-ChildItem (Join-Path $web 'app'),(Join-Path $web 'components'),(Join-Path $web 'hooks'),(Join-Path $web 'lib'),(Join-Path $web 'public'),(Join-Path $web 'package.json'),(Join-Path $web 'package-lock.json'),(Join-Path $web 'index.html'),(Join-Path $web 'vite.config.ts') -Recurse -File -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($srcNewest -and $srcNewest.LastWriteTimeUtc -gt $distTime) { $webStale = $true }
}
if ($webStale) {
    if (-not (Have 'npm')) { Fail "The front-end needs building but Node.js/npm was not found on PATH. Install Node.js 22+ and re-run (first-time step; needs internet for 'npm ci')." }
    Push-Location $web
    try {
        $lockStamp=Join-Path $web 'node_modules/.mplads-lock-sha'
        $lockHash=Sha (Join-Path $web 'package-lock.json')
        if (-not (Test-Path 'node_modules/vite/bin/vite.js') -or -not(Test-Path $lockStamp) -or (Get-Content $lockStamp -Raw).Trim() -ne $lockHash) {
            Write-Host "First-time setup: installing front-end dependencies (needs internet)..." -ForegroundColor Yellow
            Step { npm ci } 'npm ci'
            Set-Content -LiteralPath $lockStamp -Value $lockHash
        }
        Step { npm exec -- tsc --noEmit } 'Type check front-end'
        Step { npm run lint } 'Lint front-end'
        Step { npm run build } 'Build front-end'
    } finally { Pop-Location }
    Ok "Front-end built"
} else {
    Ok "Front-end build is present and current"
}

# --- Start the server, wait until ready, open the browser --------------------
# run.ps1 already verified freshness this run, so serve skips its own re-hash.
$proc = Start-Process -FilePath $py -ArgumentList @(('"'+(Join-Path $six 'serve.py')+'"'),'--port',"$Port",'--no-verify') -WorkingDirectory $six -PassThru -WindowStyle Hidden
function Save-ServerIdentity {
    # Windows venv Python may be a redirector with a separate listening child.
    # Record both identities; never infer ownership merely from a port number.
    $scriptPath=Join-Path $six 'serve.py'
    $owned=@(Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id) OR ParentProcessId = $($proc.Id)" |
        Where-Object { $_.CommandLine -like "*$scriptPath*" -and $_.CommandLine -match "--port\s+$Port(?:\s|$)" } |
        ForEach-Object { @{pid=$_.ProcessId;created=$_.CreationDate.ToUniversalTime().ToString('o');executable=$_.ExecutablePath} })
    @{processes=$owned;port=$Port}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $pidFile -Encoding UTF8
}
try {
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    if ($proc.HasExited) { Fail "The local service exited during startup (exit $($proc.ExitCode)). Re-run to see the error." }
    try { $h = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 1; if ($h.application -eq 'MPLADS Six Source') { $ready = $true; break } } catch { }
    Start-Sleep -Milliseconds 350
}
if (-not $ready) { throw 'The service did not become ready in time.' }
Save-ServerIdentity

Write-Host ""
Ok "MPLADS-GUARD is ready at http://127.0.0.1:$Port/"
Write-Host "     The app processes data locally; your review notes stay on this computer."
Write-Host "     Press Ctrl+C here (or run STOP.cmd) to stop." -ForegroundColor DarkGray
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port/" }
    Wait-Process -Id $proc.Id
} finally {
    if (-not $proc.HasExited) {
        Save-ServerIdentity
        & (Join-Path $root 'stop.ps1') -Port $Port
    }
    Write-Host "Stopped."
}
