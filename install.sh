#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
GITHUB_REPO="mikumimiestu/lyra-ai-cli"
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

echo -e "${PURPLE}==================================================${RESET}"
echo -e "${BLUE}        Installing Amagi CLI AI Assistant          ${RESET}"
echo -e "${PURPLE}==================================================${RESET}"

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: Python 3 tidak ditemukan. Silakan instal Python 3 terlebih dahulu.${RESET}"
    exit 1
fi

# 2. Create target directory
echo -e "${CYAN}Creating installation directory at ${INSTALL_DIR}...${RESET}"
mkdir -p "$INSTALL_DIR"

# 3. Retrieve files
# If files exist in current directory, we copy them (Local Dev Mode)
# Otherwise, we download them from raw.githubusercontent.com
FILES=("app.py" "styling.py" "spinner.py" "tools.py" "config.py")
LOCAL_MODE=false

if [ -f "app.py" ] && [ -f "styling.py" ]; then
    echo -e "${YELLOW}Running in Local installation mode...${RESET}"
    LOCAL_MODE=true
fi

for file in "${FILES[@]}"; do
    if [ "$LOCAL_MODE" = true ]; then
        echo -e "Copying $file..."
        cp "$file" "$INSTALL_DIR/$file"
    else
        echo -e "Downloading $file from GitHub..."
        curl -sSf -o "$INSTALL_DIR/$file" "https://raw.githubusercontent.com/$GITHUB_REPO/main/$file"
    fi
done

# 4. Set up Virtual Environment
echo -e "${CYAN}Setting up virtual environment...${RESET}"
python3 -m venv "$INSTALL_DIR/venv"

echo -e "${CYAN}Installing dependencies (requests)...${RESET}"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip &>/dev/null || true
"$INSTALL_DIR/venv/bin/pip" install requests

# 5. Create wrapper script
WRAPPER_CONTENT=$(cat <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/app.py" "\$@"
EOF
)

# Find where to install the executable
BIN_DIR=""
if [ -d "$HOME/.local/bin" ]; then
    BIN_DIR="$HOME/.local/bin"
elif [ -d "$HOME/bin" ]; then
    BIN_DIR="$HOME/bin"
elif [ -w "/usr/local/bin" ]; then
    BIN_DIR="/usr/local/bin"
else
    # Default fallback to ~/.local/bin
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

echo -e "${CYAN}Installing 'amagi' command wrapper to $BIN_DIR/amagi...${RESET}"
echo "$WRAPPER_CONTENT" > "$BIN_DIR/amagi"
chmod +x "$BIN_DIR/amagi"

echo -e "\n${GREEN}✓ Amagi CLI successfully installed!${RESET}"
echo -e "${PURPLE}==================================================${RESET}"
echo -e "Untuk menjalankannya, silakan ketik perintah berikut:"
echo -e "  ${BOLD}${BLUE}amagi${RESET}"
echo -e "${PURPLE}==================================================${RESET}"

# PATH warning if BIN_DIR is not in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Peringatan: Direktori $BIN_DIR tidak ada di dalam PATH Anda.${RESET}"
    echo -e "Silakan tambahkan baris berikut ke file shell profile Anda (~/.zshrc atau ~/.bashrc):"
    echo -e "  ${BOLD}export PATH=\"\$PATH:$BIN_DIR\"${RESET}"
fi
