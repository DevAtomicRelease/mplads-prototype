param([int]$Port = 8765, [switch]$NoBrowser)
. (Join-Path $PSScriptRoot 'PROJECT_RUNTIME.ps1')
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a local port between 1024 and 65535.' }
$prototypeDir = Join-Path $PSScriptRoot 'mplads-prototype'
foreach ($required in @('pipeline_research\artifacts\snapshot.json', 'validation_research\metrics.json', 'mplads-prototype\dist\local\index.html')) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $required))) { throw "Missing $required. Run REBUILD_PROJECT.cmd first." }
}
$projectUrl = "http://127.0.0.1:$Port"
$existingHealth = $null
try { $existingHealth = Invoke-RestMethod "$projectUrl/api/health" -TimeoutSec 2 } catch { }
if ($existingHealth -and $existingHealth.application -eq 'MPLADS Insight') {
    Write-Host "MPLADS Insight is already running at $projectUrl"
} else {
    $pythonPath = Find-ProjectPython
    $localDir = Join-Path $PSScriptRoot 'prototype-local-data'
    New-Item -ItemType Directory -Path $localDir -Force | Out-Null
    $serviceScript = Join-Path $prototypeDir 'scripts\serve_local.py'
    $serviceProcess = Start-Process -FilePath $pythonPath -ArgumentList @(('"' + $serviceScript + '"'), '--port', "$Port") -WorkingDirectory $prototypeDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localDir 'server.log') -RedirectStandardError (Join-Path $localDir 'server-errors.log') -PassThru
    $launchInfo = @{ processId = $serviceProcess.Id; script = $serviceScript; port = $Port }
    $launchInfo | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $localDir 'server-process.json') -Encoding UTF8
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($serviceProcess.HasExited) { throw 'Local service exited. Read prototype-local-data/server-errors.log.' }
        try { $health = Invoke-RestMethod "$projectUrl/api/health" -TimeoutSec 1; $ready = $health.application -eq 'MPLADS Insight' } catch { }
        if ($ready) { break }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) { throw 'Local service is not responding. Inspect prototype-local-data/server-errors.log.' }
    Write-Host "MPLADS Insight is ready at $projectUrl"
}
Write-Host 'The app processes data locally; your review notes stay on this computer. Use STOP_PROJECT.cmd to stop the service.'
if (-not $NoBrowser) { Start-Process $projectUrl }
