#!/usr/bin/env bash
# Mengunggah rilis Amagi CLI ke VPS lewat rsync/SSH, lengkap dengan SHA256SUMS.
# Pakai (dari akar repo):   VPS='root@alamat-vps' PORT=22 bash deploy/publish.sh
# Uji tanpa mengunggah:     DRY_RUN=1 bash deploy/publish.sh
set -euo pipefail

cd "$(dirname "$0")/.."
VPS="${VPS:-}"
PORT="${PORT:-22}"
WEBROOT="${WEBROOT:-/var/www/astbyte}"
FILES=(app.py styling.py spinner.py tools.py config.py memory.py reminder.py setup.py install.sh install.ps1)

[ "${DRY_RUN:-0}" = "1" ] || [ -n "$VPS" ] || { echo "Isi VPS, contoh: VPS='root@alamat-vps' PORT=22 bash deploy/publish.sh" >&2; exit 1; }
for f in "${FILES[@]}" version.txt; do [ -f "$f" ] || { echo "File tidak ada: $f" >&2; exit 1; }; done

# Versi di version.txt harus sama dengan config.py, supaya klien tidak menarik versi yang salah.
CONFIG_VERSION="$(sed -n 's/^VERSION = "\(.*\)"/\1/p' config.py)"
FILE_VERSION="$(tr -d '[:space:]' < version.txt)"
[ "$CONFIG_VERSION" = "$FILE_VERSION" ] || { echo "version.txt ($FILE_VERSION) berbeda dari config.py ($CONFIG_VERSION)." >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "${FILES[@]}" version.txt "$STAGE/"
if command -v sha256sum >/dev/null 2>&1; then HASH=(sha256sum); else HASH=(shasum -a 256); fi
( cd "$STAGE" && "${HASH[@]}" "${FILES[@]}" version.txt > SHA256SUMS )
chmod 644 "$STAGE"/*      # rsync -a membawa izin ini ke server; flag --chmod tidak didukung rsync bawaan macOS
echo "Rilis $FILE_VERSION disiapkan:"; cat "$STAGE/SHA256SUMS"

if [ "${DRY_RUN:-0}" = "1" ]; then echo "DRY_RUN: tidak ada yang diunggah."; exit 0; fi

SSH=(ssh -p "$PORT")
RSYNC=(rsync -az -e "ssh -p $PORT")
# Dua tahap: file dulu, lalu version.txt dan SHA256SUMS, agar klien tidak melihat versi baru sebelum filenya lengkap.
"${RSYNC[@]}" "${FILES[@]/#/$STAGE/}" "$VPS:$WEBROOT/"
"${RSYNC[@]}" "$STAGE/SHA256SUMS" "$STAGE/version.txt" "$VPS:$WEBROOT/"
echo "Selesai. Cek: curl -s https://astbyte.my.id/version.txt"
