# Stop only this project's recorded server, checking executable, command and creation time.
[CmdletBinding()]
param([int]$Port=8766)
$ErrorActionPreference='Stop'
$record=Join-Path $PSScriptRoot "six_source/local/.serve-$Port.json"
if(-not(Test-Path -LiteralPath $record)){Write-Host "No server recorded for port $Port.";exit 0}
$saved=Get-Content -LiteralPath $record -Raw|ConvertFrom-Json
$script=Join-Path $PSScriptRoot 'six_source/serve.py'
$identities=if($saved.processes){@($saved.processes)}else{@($saved)}
$verified=@()
foreach($entry in $identities){
    $process=Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.pid)"
    if(-not $process){continue}
    if($process.ExecutablePath -ne $entry.executable -or $process.CreationDate.ToUniversalTime() -ne ([datetime]$entry.created).ToUniversalTime() -or $process.CommandLine -notlike "*$script*" -or $process.CommandLine -notmatch "--port\s+$Port(?:\s|$)"){
        throw 'Process identity differs from the saved server. Nothing was stopped.'
    }
    $verified += $process
}
foreach($process in $verified){Stop-Process -Id $process.ProcessId -ErrorAction SilentlyContinue}
Remove-Item -LiteralPath $record -ErrorAction SilentlyContinue
Write-Host "Stopped this project server on port $Port. Data and review history were preserved."
