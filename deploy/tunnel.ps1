# Share the app from this computer through a free Cloudflare quick tunnel.
# No account, no card. The data never leaves this computer; the link lives only
# while this window is open. The shared copy is always read-only.
#
#   powershell -ExecutionPolicy Bypass -File deploy\tunnel.ps1
#
param([int]$Port = 8767)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
$serve = Join-Path $root 'six_source\serve.py'

if (-not (Test-Path $py)) { Write-Host 'Run START.cmd once first (it creates the Python environment and builds the data).'; exit 1 }
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host 'cloudflared is not installed. Install it once with:'
    Write-Host '    winget install --id Cloudflare.cloudflared'
    Write-Host 'then open a new terminal and run this script again.'
    exit 1
}

# Any *.trycloudflare.com name is accepted, which also forces read-only mode.
$server = Start-Process -FilePath $py -ArgumentList @('-B', "`"$serve`"", '--port', "$Port", '--no-verify', '--allowed-host', '*.trycloudflare.com') -WorkingDirectory (Split-Path $serve) -PassThru -WindowStyle Hidden
try {
    $ok = $false
    foreach ($i in 1..40) {
        Start-Sleep -Milliseconds 500
        try { if ((Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/api/health" -TimeoutSec 2).StatusCode -eq 200) { $ok = $true; break } } catch {}
        if ($server.HasExited) { break }
    }
    if (-not $ok) { Write-Host 'The app did not start. Run START.cmd to check the data build, then try again.'; exit 1 }
    Write-Host ''
    Write-Host 'Read-only demo copy is running. Look for the https://....trycloudflare.com link below.'
    Write-Host 'Share it only with people who should see it. Close this window (or Ctrl+C) to stop sharing.'
    Write-Host ''
    & cloudflared tunnel --url "http://127.0.0.1:$Port"
}
finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
