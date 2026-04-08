param(
    [string]$RepoRoot = "$(Split-Path -Parent $PSScriptRoot)"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$text) {
    Write-Host "==> $text" -ForegroundColor Cyan
}

Write-Step "Checking admin privileges"
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Run this script from elevated PowerShell (Administrator)."
}

$solution = Join-Path $RepoRoot "01_ASCOM_Local_Server\ASCOM.ProjectR1.LocalServer.sln"
$cameraDll = Join-Path $RepoRoot "01_ASCOM_Local_Server\src\ASCOM.ProjectR1.Camera\bin\Release\ASCOM.ProjectR1.Camera.dll"
$serviceRoot = Join-Path $RepoRoot "02_Python_Camera_Service"
$pythonExe = Join-Path $serviceRoot ".venv\Scripts\python.exe"

Write-Step "Building ASCOM driver (Release)"
& "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe" `
    $solution /t:Rebuild /p:Configuration=Release /p:Platform="Any CPU"

Write-Step "Registering COM driver"
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe" $cameraDll /u | Out-Null
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe" $cameraDll /codebase

Write-Step "Preparing Python virtual environment"
if (-not (Test-Path $pythonExe)) {
    python -m venv (Join-Path $serviceRoot ".venv")
}

Write-Step "Installing Python service dependencies"
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -e $serviceRoot

$envFile = Join-Path $serviceRoot ".env"
$envExample = Join-Path $serviceRoot ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "Created .env from .env.example. Fill SDK_DLL_PATH before running native mode." -ForegroundColor Yellow
}

Write-Step "Applying DB migrations"
& $pythonExe -m alembic -c (Join-Path $serviceRoot "alembic.ini") upgrade head

Write-Step "Deployment baseline complete"
Write-Host "Next step: run start_camera_service.ps1 from 07_Deployment_and_Ops." -ForegroundColor Green
