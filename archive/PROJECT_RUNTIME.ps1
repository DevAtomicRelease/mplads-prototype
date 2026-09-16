$ErrorActionPreference = 'Stop'
function Find-ProjectPython {
    if ($env:MPLADS_PYTHON -and (Test-Path -LiteralPath $env:MPLADS_PYTHON)) { return $env:MPLADS_PYTHON }
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) { return $bundledPython }
    $foundPython = Get-Command python -ErrorAction SilentlyContinue
    if ($foundPython) { return $foundPython.Source }
    throw 'Python is unavailable. Install Python 3.11+ or set MPLADS_PYTHON to its executable.'
}
function Find-ProjectNode {
    if ($env:MPLADS_NODE -and (Test-Path -LiteralPath $env:MPLADS_NODE)) { return $env:MPLADS_NODE }
    $bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
    if (Test-Path -LiteralPath $bundledNode) { return $bundledNode }
    $foundNode = Get-Command node -ErrorAction SilentlyContinue
    if ($foundNode) { return $foundNode.Source }
    throw 'Node.js is unavailable. Install Node 24 LTS or set MPLADS_NODE to its executable.'
}
function Assert-LastStep([string]$Label) {
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE. No completion is being claimed." }
}
