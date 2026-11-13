# PowerShell Installer for Amagi CLI on Windows
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
# Or online: iwr -useb https://astbyte.my.id/install.ps1 | iex

$ErrorActionPreference = "Stop"

$GITHUB_REPO = "mikumimiestu/lyra-ai-cli"
$BASE_URL = if ($env:AMAGI_BASE_URL) { $env:AMAGI_BASE_URL.TrimEnd("/") } else { "https://astbyte.my.id" }
$INSTALL_DIR = "$HOME\.amagi-cli"
$FILES = @("app.py", "styling.py", "spinner.py", "tools.py", "config.py", "memory.py", "reminder.py", "version.txt")

Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "        Installing Amagi CLI AI Assistant          " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Magenta

# 1. Make sure Python 3 is available (offer to install it when it is not)
$PY_FULL = "3.12.8"      # used only for the python.org installer fallback

# Python 3.7+ that really runs (the Microsoft Store alias for "python" exists but only opens the Store).
function Test-PythonCommand([string]$Command, [string[]]$Prefix = @()) {
    try {
        $null = & $Command @Prefix -c "import sys, venv, ensurepip; sys.exit(0 if sys.version_info >= (3, 7) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    foreach ($name in @("python", "python3")) {
        $found = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found -and $found.Source -notlike "*\WindowsApps\*" -and (Test-PythonCommand $found.Source)) {
            return $found.Source
        }
    }
    if ((Get-Command "py" -ErrorAction SilentlyContinue) -and (Test-PythonCommand "py" @("-3"))) {
        return "py"
    }
    foreach ($dir in @("$env:LOCALAPPDATA\Programs\Python\Python312", "$env:LOCALAPPDATA\Programs\Python\Python313",
                       "$env:ProgramFiles\Python312", "$env:ProgramFiles\Python313")) {
        $exe = Join-Path $dir "python.exe"
        if ((Test-Path $exe) -and (Test-PythonCommand $exe)) { return $exe }
    }
    return $null
}

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    $user = [Environment]::GetEnvironmentVariable("PATH", "User")
    $env:PATH = "$machine;$user"
}

function Confirm-PythonInstall {
    if ($env:AMAGI_ASSUME_YES -eq "1") { return $true }
    try {
        $reply = Read-Host "Python 3 belum terpasang. Pasang sekarang secara otomatis? [Y/n]"
    } catch {
        Write-Host "Tidak ada terminal interaktif untuk bertanya. Jalankan ulang dengan `$env:AMAGI_ASSUME_YES='1'." -ForegroundColor Yellow
        return $false
    }
    return ($reply -eq "" -or $reply -match "^(y|ya|yes)$")
}

function Install-Python {
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Memasang Python lewat winget..." -ForegroundColor Cyan
        try {
            & winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) { return $true }
        } catch { }
        Write-Host "winget gagal, mencoba installer resmi python.org..." -ForegroundColor Yellow
    }
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }
    $url = "https://www.python.org/ftp/python/$PY_FULL/python-$PY_FULL-$arch.exe"
    $installer = Join-Path ([IO.Path]::GetTempPath()) "python-$PY_FULL-$arch.exe"
    Write-Host "Mengunduh Python $PY_FULL dari python.org..." -ForegroundColor Cyan
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Menjalankan installer (untuk pengguna ini, tanpa hak administrator)..." -ForegroundColor Cyan
    $process = Start-Process -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "Include_launcher=0" -Wait -PassThru
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    return ($process.ExitCode -eq 0)
}

$pythonCmd = Find-Python
if (-not $pythonCmd) {
    Write-Host "Python 3.7+ (lengkap dengan venv dan pip) belum ditemukan di komputer ini." -ForegroundColor Yellow
    if (-not (Confirm-PythonInstall)) {
        Write-Host "Pasang Python 3 dulu dari https://www.python.org/downloads/ lalu jalankan installer lagi." -ForegroundColor Red
        exit 1
    }
    $installed = $false
    try { $installed = Install-Python } catch { Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red }
    if (-not $installed) {
        Write-Host "Pemasangan Python otomatis gagal. Pasang manual dari https://www.python.org/downloads/ lalu jalankan installer lagi." -ForegroundColor Red
        exit 1
    }
    Update-SessionPath
    $pythonCmd = Find-Python
    if (-not $pythonCmd) {
        Write-Host "Python sudah dipasang tetapi belum terdeteksi di sesi ini. Buka PowerShell baru lalu jalankan installer lagi." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Python siap: $pythonCmd" -ForegroundColor Green
}
# "py" needs its -3 flag; wrap it so the rest of the script can call $pythonCmd the same way.
$pythonArgs = @()
if ($pythonCmd -eq "py") { $pythonArgs = @("-3") }

# 2. Create Target Directory
Write-Host "Creating installation directory at $INSTALL_DIR..." -ForegroundColor Cyan
if (!(Test-Path -Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR | Out-Null
}

# 3. Retrieve files (Local vs download)
# Download every file of a release into $Dir; with $Verify each must match SHA256SUMS. Returns $true or $false.
function Get-Release([string]$Base, [string]$Dir, [bool]$Verify) {
    try {
        $sums = @{}
        if ($Verify) {
            $sumsPath = Join-Path $Dir "SHA256SUMS"
            Invoke-WebRequest -Uri "$Base/SHA256SUMS" -OutFile $sumsPath -UseBasicParsing
            foreach ($line in Get-Content $sumsPath) {
                $parts = $line.Trim() -split "\s+", 2
                if ($parts.Count -eq 2) { $sums[$parts[1].TrimStart("*")] = $parts[0].ToLower() }
            }
        }
        foreach ($file in $FILES) {
            $path = Join-Path $Dir $file
            Invoke-WebRequest -Uri "$Base/$file" -OutFile $path -UseBasicParsing
            if ($Verify) {
                $actual = (Get-FileHash -Path $path -Algorithm SHA256).Hash.ToLower()
                if (-not $sums.ContainsKey($file)) { Write-Host "$file tidak ada di SHA256SUMS." -ForegroundColor Red; return $false }
                if ($sums[$file] -ne $actual) { Write-Host "Checksum $file tidak cocok (file rusak atau diubah)." -ForegroundColor Red; return $false }
            }
        }
        return $true
    } catch {
        return $false
    }
}

$LOCAL_MODE = $false
if ((Test-Path "app.py") -and (Test-Path "styling.py")) {
    Write-Host "Running in Local installation mode..." -ForegroundColor Yellow
    $LOCAL_MODE = $true
}

if ($LOCAL_MODE) {
    foreach ($file in $FILES) {
        Write-Host "Copying $file..."
        Copy-Item -Path $file -Destination (Join-Path $INSTALL_DIR $file) -Force
    }
} else {
    $staging = Join-Path ([IO.Path]::GetTempPath()) ("amagi-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $staging | Out-Null
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Write-Host "Mengunduh dari $BASE_URL..." -ForegroundColor Cyan
    if (Get-Release $BASE_URL $staging $true) {
        Write-Host "Terverifikasi dengan SHA256SUMS" -ForegroundColor Green
    } else {
        Write-Host "Server utama tidak bisa dipakai, mengunduh dari GitHub..." -ForegroundColor Yellow
        Get-ChildItem $staging | Remove-Item -Force
        if (-not (Get-Release "https://raw.githubusercontent.com/$GITHUB_REPO/main" $staging $false)) {
            Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Gagal mengunduh file Amagi CLI. Periksa koneksi internet lalu coba lagi." -ForegroundColor Red
            exit 1
        }
    }
    foreach ($file in $FILES) {
        Copy-Item -Path (Join-Path $staging $file) -Destination (Join-Path $INSTALL_DIR $file) -Force
    }
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
}

# 4. Set up Virtual Environment
Write-Host "Setting up virtual environment..." -ForegroundColor Cyan
$venvPath = Join-Path $INSTALL_DIR "venv"
$pythonVenv = Join-Path $venvPath "Scripts\python.exe"

if (!(Test-Path $pythonVenv)) {
    & $pythonCmd @pythonArgs -m venv $venvPath
}

Write-Host "Installing dependencies (requests, prompt_toolkit)..." -ForegroundColor Cyan
if (Test-Path $pythonVenv) {
    & $pythonVenv -m ensurepip --default-pip 2>$null | Out-Null
    & $pythonVenv -m pip install requests 'prompt_toolkit>=3.0.36,<4' --quiet
} else {
    $pythonVenv = $pythonCmd
    & $pythonCmd @pythonArgs -m pip install requests 'prompt_toolkit>=3.0.36,<4' --quiet
}

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
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "Untuk menjalankannya, silakan buka Terminal / PowerShell baru lalu ketik:"
Write-Host "  amagi" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Magenta
