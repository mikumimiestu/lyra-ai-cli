#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
GITHUB_REPO="mikumimiestu/lyra-ai-cli"
BASE_URL="${AMAGI_BASE_URL:-https://astbyte.my.id}"      # main download server (publishes SHA256SUMS)
FILES=("app.py" "styling.py" "spinner.py" "tools.py" "config.py" "memory.py" "reminder.py" "version.txt")
INSTALL_DIR="$HOME/.amagi-cli"

# Colors
BLUE='\033[1;34m'
PURPLE='\033[1;35m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'
BOLD='\033[1m'

# ── Python: find a usable one, or offer to install it for this OS ───────────────
PYTHON_BIN=""
PY_FULL="3.12.8"      # used only for the python.org macOS installer fallback

# Python 3.7+ with the venv and pip modules (Debian/Ubuntu ship them in separate packages).
python_ok() {
    "$1" -c 'import sys, venv, ensurepip; sys.exit(0 if sys.version_info >= (3, 7) else 1)' >/dev/null 2>&1
}

find_python() {
    local candidate
    for candidate in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python python3.7; do
        if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done
    # Places a fresh Homebrew / python.org install lands before the shell's PATH knows about it.
    for candidate in ${AMAGI_PYTHON_PATHS-/opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3}; do
        if [ -x "$candidate" ] && python_ok "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

as_root() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo -e "${RED}Butuh hak administrator (sudo) untuk memasang Python, tetapi sudo tidak tersedia.${RESET}" >&2
        return 127
    fi
}

# Ask before touching the system. AMAGI_ASSUME_YES=1 answers yes without asking (unattended installs).
confirm_python_install() {
    local tty="${AMAGI_TTY:-/dev/tty}" reply=""
    if [ "${AMAGI_ASSUME_YES:-}" = "1" ]; then
        return 0
    fi
    if ( : < "$tty" ) 2>/dev/null; then
        printf "Pasang Python sekarang secara otomatis? [Y/n] " >> "$tty" 2>/dev/null || printf "Pasang Python sekarang secara otomatis? [Y/n] "
        read -r reply < "$tty" || reply=""
        case "$reply" in
            ""|y|Y|ya|YA|Ya|yes|YES) return 0 ;;
            *) return 1 ;;
        esac
    fi
    echo -e "${YELLOW}Tidak ada terminal interaktif untuk bertanya. Jalankan ulang dengan AMAGI_ASSUME_YES=1 agar Python dipasang otomatis.${RESET}"
    return 1
}

install_python_macos() {
    if command -v brew >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat Homebrew...${RESET}"
        brew install python@3.12 && return 0
        echo -e "${YELLOW}Homebrew gagal, mencoba installer resmi python.org...${RESET}"
    fi
    local tmp url
    tmp="$(mktemp -d)"
    url="https://www.python.org/ftp/python/$PY_FULL/python-$PY_FULL-macos11.pkg"
    echo -e "${CYAN}Mengunduh Python $PY_FULL dari python.org...${RESET}"
    curl -fL --progress-bar -o "$tmp/python.pkg" "$url" || { rm -rf "$tmp"; return 1; }
    echo -e "${CYAN}Menjalankan installer (diminta password administrator)...${RESET}"
    as_root installer -pkg "$tmp/python.pkg" -target / || { rm -rf "$tmp"; return 1; }
    rm -rf "$tmp"
}

install_python_linux() {
    if command -v apt-get >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat apt...${RESET}"
        as_root apt-get update -qq || true
        as_root apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat dnf...${RESET}"
        as_root dnf install -y python3 python3-pip
    elif command -v yum >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat yum...${RESET}"
        as_root yum install -y python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat pacman...${RESET}"
        as_root pacman -S --noconfirm python python-pip
    elif command -v zypper >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat zypper...${RESET}"
        as_root zypper --non-interactive install python3 python3-pip
    elif command -v apk >/dev/null 2>&1; then
        echo -e "${CYAN}Memasang Python lewat apk...${RESET}"
        as_root apk add python3 py3-pip
    else
        echo -e "${RED}Package manager tidak dikenali.${RESET}"
        return 1
    fi
}

install_python() {
    case "$(uname -s)" in
        Darwin) install_python_macos ;;
        Linux)  install_python_linux ;;
        *)      echo -e "${RED}Sistem operasi ini belum didukung untuk pemasangan Python otomatis.${RESET}"; return 1 ;;
    esac
}

ensure_python() {
    if PYTHON_BIN="$(find_python)"; then
        return 0
    fi
    echo -e "${YELLOW}Python 3.7+ (lengkap dengan venv dan pip) belum ditemukan di komputer ini.${RESET}"
    if ! confirm_python_install; then
        echo -e "${RED}Pasang Python 3 dulu dari https://www.python.org/downloads/ lalu jalankan installer lagi.${RESET}"
        exit 1
    fi
    if ! install_python; then
        echo -e "${RED}Pemasangan Python otomatis gagal. Pasang manual dari https://www.python.org/downloads/ lalu jalankan installer lagi.${RESET}"
        exit 1
    fi
    hash -r 2>/dev/null || true
    if PYTHON_BIN="$(find_python)"; then
        echo -e "${GREEN}✓ Python siap: $PYTHON_BIN${RESET}"
        return 0
    fi
    echo -e "${YELLOW}Python sudah dipasang tetapi belum terdeteksi di sesi ini. Buka terminal baru lalu jalankan installer lagi.${RESET}"
    exit 1
}

# ── Download: main server with checksum verification, GitHub as fallback ─────────
sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

# fetch_release BASE_URL DIR VERIFY(1|0): every file into DIR; with VERIFY each must match SHA256SUMS.
fetch_release() {
    local base="$1" dir="$2" verify="$3" f want got
    if [ "$verify" = "1" ]; then
        curl -fsS --max-time 30 -o "$dir/SHA256SUMS" "$base/SHA256SUMS" || return 1
    fi
    for f in "${FILES[@]}"; do
        curl -fsS --max-time 60 -o "$dir/$f" "$base/$f" || return 1
        if [ "$verify" = "1" ]; then
            want="$(awk -v n="$f" '$2 == n {print $1}' "$dir/SHA256SUMS")"
            got="$(sha256_of "$dir/$f")"
            [ -n "$want" ] || { echo -e "${RED}$f tidak ada di SHA256SUMS.${RESET}" >&2; return 1; }
            if [ -z "$got" ]; then
                echo -e "${YELLOW}Tidak ada sha256sum/shasum, $f tidak diverifikasi.${RESET}" >&2
            elif [ "$got" != "$want" ]; then
                echo -e "${RED}Checksum $f tidak cocok (file rusak atau diubah).${RESET}" >&2
                return 1
            fi
        fi
    done
}

# download_release DIR: main server first (verified), then GitHub (HTTPS only).
download_release() {
    local dir="$1"
    echo -e "${CYAN}Mengunduh dari ${BASE_URL}...${RESET}"
    if fetch_release "${BASE_URL%/}" "$dir" 1; then
        echo -e "${GREEN}✓ Terverifikasi dengan SHA256SUMS${RESET}"
        return 0
    fi
    echo -e "${YELLOW}Server utama tidak bisa dipakai, mengunduh dari GitHub...${RESET}"
    rm -f "$dir"/*
    fetch_release "https://raw.githubusercontent.com/$GITHUB_REPO/main" "$dir" 0
}

# Tests source this file to reach the functions above without installing anything.
if [ "${AMAGI_INSTALL_SOURCE_ONLY:-0}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi

echo -e "${PURPLE}==================================================${RESET}"
echo -e "${BLUE}        Installing Amagi CLI AI Assistant          ${RESET}"
echo -e "${PURPLE}==================================================${RESET}"

# 1. Make sure Python 3 is available (offer to install it when it is not)
ensure_python

# 2. Create target directory
echo -e "${CYAN}Creating installation directory at ${INSTALL_DIR}...${RESET}"
mkdir -p "$INSTALL_DIR"

# 3. Retrieve files
# If the files are in the current directory, copy them (Local Dev Mode); otherwise download the release.
if [ -f app.py ] && [ -f styling.py ]; then
    echo -e "${YELLOW}Running in Local installation mode...${RESET}"
    for file in "${FILES[@]}"; do
        echo -e "Copying $file..."
        cp "$file" "$INSTALL_DIR/$file"
    done
else
    STAGING="$(mktemp -d)"
    if ! download_release "$STAGING"; then
        rm -rf "$STAGING"
        echo -e "${RED}Gagal mengunduh file Amagi CLI. Periksa koneksi internet lalu coba lagi.${RESET}"
        exit 1
    fi
    for file in "${FILES[@]}"; do
        cp "$STAGING/$file" "$INSTALL_DIR/$file"
    done
    rm -rf "$STAGING"
fi

# 4. Set up Virtual Environment
echo -e "${CYAN}Setting up virtual environment...${RESET}"
rm -rf "$INSTALL_DIR/venv"
"$PYTHON_BIN" -m venv "$INSTALL_DIR/venv"

echo -e "${CYAN}Installing dependencies (requests, prompt_toolkit)...${RESET}"
if [ -f "$INSTALL_DIR/venv/bin/python3" ]; then
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip &>/dev/null || true
    "$INSTALL_DIR/venv/bin/pip" install requests 'prompt_toolkit>=3.0.36,<4'
elif [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip &>/dev/null || true
    "$INSTALL_DIR/venv/bin/pip" install requests 'prompt_toolkit>=3.0.36,<4'
else
    pip3 install requests 'prompt_toolkit>=3.0.36,<4' --user
fi

# 5. Create wrapper script
PYTHON_EXEC="$INSTALL_DIR/venv/bin/python3"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$INSTALL_DIR/venv/bin/python"
fi
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$PYTHON_BIN"
fi

WRAPPER_CONTENT=$(cat <<EOF
#!/usr/bin/env bash
if [ -f "$INSTALL_DIR/venv/bin/python3" ]; then
    exec "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/app.py" "\$@"
elif [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/app.py" "\$@"
else
    exec python3 "$INSTALL_DIR/app.py" "\$@"
fi
EOF
)

# Find where to install the executable
mkdir -p "$HOME/.local/bin"
echo "$WRAPPER_CONTENT" > "$HOME/.local/bin/amagi"
chmod +x "$HOME/.local/bin/amagi"

if [ -w "/usr/local/bin" ]; then
    echo -e "${CYAN}Installing 'amagi' command wrapper to /usr/local/bin/amagi...${RESET}"
    echo "$WRAPPER_CONTENT" > "/usr/local/bin/amagi"
    chmod +x "/usr/local/bin/amagi"
fi

echo -e "\n${GREEN}✓ Amagi CLI successfully installed!${RESET}"
echo -e "${PURPLE}==================================================${RESET}"
echo -e "Untuk menjalankannya, silakan buka terminal baru dan ketik:"
echo -e "  ${BOLD}${BLUE}amagi${RESET}"
echo -e "${PURPLE}==================================================${RESET}"
