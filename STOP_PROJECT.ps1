. (Join-Path $PSScriptRoot 'PROJECT_RUNTIME.ps1')
$processFile = Join-Path $PSScriptRoot 'prototype-local-data\server-process.json'
if (-not (Test-Path -LiteralPath $processFile)) { Write-Host 'No launcher-owned service is recorded.'; exit 0 }
$launchInfo = Get-Content -Raw -LiteralPath $processFile | ConvertFrom-Json
$servicePid = [int]$launchInfo.processId
$expectedScript = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'mplads-prototype\scripts\serve_local.py'))
$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $servicePid" -ErrorAction SilentlyContinue
if ($processInfo -and $launchInfo.script -eq $expectedScript -and $processInfo.CommandLine.Contains($expectedScript)) {
    Stop-Process -Id $servicePid
    Write-Host 'Stopped the local MPLADS service. All data and review notes are preserved.'
} else { Write-Host 'No matching launcher-owned process is running; nothing was stopped.' }
