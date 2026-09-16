param([switch]$SkipWorkbook)
. (Join-Path $PSScriptRoot 'PROJECT_RUNTIME.ps1')
$pythonPath = Find-ProjectPython
$nodePath = Find-ProjectNode
$prototypeDir = Join-Path $PSScriptRoot 'mplads-prototype'
& $pythonPath -c 'import numpy, pandas; print(numpy.__version__, pandas.__version__)'
Assert-LastStep 'Python dependency check (install pipeline_research/requirements.txt if missing)'
if (-not (Test-Path -LiteralPath (Join-Path $prototypeDir 'node_modules\vite\bin\vite.js'))) { throw 'Application dependencies are missing. In mplads-prototype run npm ci, then retry.' }
Push-Location $PSScriptRoot
try {
    & $pythonPath pipeline_research/build_features.py
    Assert-LastStep 'Feature pipeline'
    & $pythonPath pipeline_research/test_pipeline.py
    Assert-LastStep 'Pipeline regression tests'
    & $pythonPath validation_research/run_ab_validation.py
    Assert-LastStep 'A/B validation'
    & $pythonPath pipeline_research/build_features.py --output-dir pipeline_research/artifacts_reproduced
    Assert-LastStep 'Independent feature rebuild'
    & $pythonPath validation_research/run_ab_validation.py --out validation_research/reproduced
    Assert-LastStep 'Independent A/B rerun'
    & $pythonPath validation_research/check_reproducibility.py
    Assert-LastStep 'Reproducibility comparison'
    Push-Location $prototypeDir
    try {
        & $nodePath node_modules/typescript/bin/tsc --noEmit --incremental false
        Assert-LastStep 'Type checking'
        & $nodePath --experimental-strip-types --test scripts/model.test.mjs
        Assert-LastStep 'Dashboard tests'
        & $pythonPath scripts/test_local_service.py
        Assert-LastStep 'Review service tests'
        & $nodePath node_modules/vite/bin/vite.js build
        Assert-LastStep 'Local application build'
    } finally { Pop-Location }
    if (-not $SkipWorkbook) {
        $workbookDir = Join-Path $PSScriptRoot 'pipeline_research\workbook'
        if (-not (Test-Path -LiteralPath (Join-Path $workbookDir 'node_modules\@oai\artifact-tool'))) { throw 'The optional Excel exporter requires the bundled artifact-tool library. The core CSV/JSON and app are complete. Re-run with -SkipWorkbook to omit Excel regeneration.' }
        & $nodePath --max-old-space-size=8192 pipeline_research/workbook/build_workbook.mjs
        Assert-LastStep 'Final Excel export'
    }
    Write-Host 'Rebuild and validation completed. Restart the service with STOP_PROJECT.cmd, then START_PROJECT.cmd.'
} finally { Pop-Location }
