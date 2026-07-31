# PowerShell Installer for Amagi CLI on Windows
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
# Or online: iwr -useb https://raw.githubusercontent.com/mikumimiestu/lyra-ai-cli/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$GITHUB_REPO = "mikumimiestu/lyra-ai-cli"
$INSTALL_DIR = "$HOME\.amagi-cli"
$FILES = @("app.py", "styling.py", "spinner.py", "tools.py", "config.py")

Write-Host "==================================================" -ForegroundColor Purple
Write-Host "        Installing Amagi CLI AI Assistant          " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Purple

# 1. Check Python
$pythonCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Host "Error: Python 3 tidak ditemukan. Silakan instal Python dari https://python.org" -ForegroundColor Red
    exit 1
}

# 2. Create Target Directory
Write-Host "Creating installation directory at $INSTALL_DIR..." -ForegroundColor Cyan
if (!(Test-Path -Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR | Out-Null
}

# 3. Retrieve files (Local vs GitHub Raw)
$LOCAL_MODE = $false
if ((Test-Path "app.py") -and (Test-Path "styling.py")) {
    Write-Host "Running in Local installation mode..." -ForegroundColor Yellow
    $LOCAL_MODE = $true
}

foreach ($file in $FILES) {
    $targetPath = Join-Path $INSTALL_DIR $file
    if ($LOCAL_MODE) {
        Write-Host "Copying $file..."
        Copy-Item -Path $file -Destination $targetPath -Force
    } else {
        Write-Host "Downloading $file from GitHub..."
        $url = "https://raw.githubusercontent.com/$GITHUB_REPO/main/$file"
        Invoke-WebRequest -Uri $url -OutFile $targetPath -UseBasicParsing
    }
}

# 4. Set up Virtual Environment
Write-Host "Setting up virtual environment..." -ForegroundColor Cyan
$venvPath = Join-Path $INSTALL_DIR "venv"
if (!(Test-Path $venvPath)) {
    & $pythonCmd -m venv $venvPath
}

$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$pythonVenv = Join-Path $venvPath "Scripts\python.exe"

Write-Host "Installing dependencies (requests)..." -ForegroundColor Cyan
& $pipExe install requests --quiet

# 5. Create amagi.cmd wrapper in User Bin directory
$BIN_DIR = Join-Path $HOME ".local\bin"
if (!(Test-Path $BIN_DIR)) {
    New-Item -ItemType Directory -Path $BIN_DIR | Out-Null
}

$cmdWrapperPath = Join-Path $BIN_DIR "amagi.cmd"
$wrapperContent = "@echo off`r`n""$pythonVenv"" ""$INSTALL_DIR\app.py"" %*"
Set-Content -Path $cmdWrapperPath -Value $wrapperContent -Encoding ASCII

# Also place amagi.bat in venv\Scripts for direct PATH access
$batWrapperPath = Join-Path $venvPath "Scripts\amagi.bat"
Set-Content -Path $batWrapperPath -Value $wrapperContent -Encoding ASCII

# 6. Add BIN_DIR to User PATH Environment Variable if not already present
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$BIN_DIR*") {
    Write-Host "Adding $BIN_DIR to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$BIN_DIR", "User")
}

Write-Host "`n✓ Amagi CLI successfully installed!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Purple
Write-Host "Untuk menjalankannya, silakan buka Terminal / PowerShell baru lalu ketik:"
Write-Host "  amagi" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Purple
