param(
    [string]$RepoRoot = "$(Split-Path -Parent $PSScriptRoot)"
)

$ErrorActionPreference = "Stop"

$serviceRoot = Join-Path $RepoRoot "02_Python_Camera_Service"
$pythonExe = Join-Path $serviceRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $serviceRoot "logs"
$wrapperLog = Join-Path $logDir "service_supervisor.log"

if (-not (Test-Path $pythonExe)) {
    throw "Python venv not found. Run deploy_camera_pc.ps1 first."
}

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Push-Location $serviceRoot
try {
    while ($true) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Add-Content -Path $wrapperLog -Value "$stamp | START uvicorn app.main:app"
        & cmd.exe /c "`"$pythonExe`" -m uvicorn app.main:app --host 127.0.0.1 --port 3037 >> `"$wrapperLog`" 2>&1"
        $exitCode = $LASTEXITCODE
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Add-Content -Path $wrapperLog -Value "$stamp | EXIT_CODE=$exitCode (restart in 2s)"
        Start-Sleep -Seconds 2
    }
}
finally {
    Pop-Location
}
