param(
    [switch]$Clean,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Err($msg) { Write-Host "[ERR ] $msg" -ForegroundColor Red }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if ($Clean) {
    Write-Info "清理 dist/ build/ __pycache__ *.spec"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$scriptDir\dist"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$scriptDir\build"
    Get-ChildItem -Recurse -Force -Include "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Force -ErrorAction SilentlyContinue "$scriptDir\ghidra_ai_gui.spec"
}

# 1) 准备虚拟环境
$venvPath = Join-Path $scriptDir ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (!(Test-Path $venvPython)) {
    Write-Info "创建虚拟环境: $venvPath"
    & $PythonExe -m venv "$venvPath"
}

Write-Info "升级 pip"
& $venvPython -m pip install -U pip wheel setuptools

# 2) 安装依赖
$reqFile = Join-Path $scriptDir "requirements.txt"
if (Test-Path $reqFile) {
    Write-Info "安装依赖: requirements.txt"
    & $venvPython -m pip install -r "$reqFile"
} else {
    Write-Err "未找到 requirements.txt"
    exit 1
}

# 3) 安装 PyInstaller
Write-Info "安装 PyInstaller"
& $venvPython -m pip install pyinstaller

# 4) 运行打包
Write-Info "运行 PyInstaller 构建"
$pyi = Join-Path $venvPath "Scripts\pyinstaller.exe"

# 若 spec 存在，优先使用；否则用命令行参数构建
$specPath = Join-Path $scriptDir "ghidra_ai_gui.spec"
if (Test-Path $specPath) {
    & $pyi "$specPath"
} else {
    & $pyi --noconfirm --noconsole --name "Ghidra-AI-Rename-GUI" `
        --add-data "ai_rename.py;." `
        --add-data "startup_checker.py;." `
        --hidden-import PyQt6 --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtWidgets `
        --hidden-import openai --hidden-import requests --hidden-import mcp.server.fastmcp --hidden-import dotenv `
        "ghidra_ai_gui.py"
}

if ($LASTEXITCODE -ne 0) {
    Write-Err "打包失败"
    exit $LASTEXITCODE
}

Write-Ok "打包完成。可执行文件位于 dist/Ghidra-AI-Rename-GUI/" 