$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & .\.venv\Scripts\python.exe -X utf8 -m PyInstaller --noconfirm ZjuRun.spec
    if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
    Copy-Item -LiteralPath config.yaml -Destination dist\config.yaml
    Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*route.txt' |
        Copy-Item -Destination dist
    Write-Host 'Built dist\ZjuRun.exe with its configuration and route files.'
} finally {
    Pop-Location
}
