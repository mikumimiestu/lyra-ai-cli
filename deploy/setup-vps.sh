#!/usr/bin/env bash
# Menyiapkan VPS untuk melayani file Amagi CLI di https://astbyte.my.id (nginx + certbot).
# Jalankan SEBAGAI ROOT di VPS:   EMAIL=kamu@contoh.com bash setup-vps.sh
# Aman dijalankan ulang. Tidak mengubah firewall selain MEMBUKA port 80/443 bila ufw aktif.
set -euo pipefail

DOMAIN="${DOMAIN:-astbyte.my.id}"
WEBROOT="${WEBROOT:-/var/www/astbyte}"
EMAIL="${EMAIL:-}"

say() { printf '\n==> %s\n' "$*"; }
die() { printf 'GAGAL: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "jalankan sebagai root."
[ -n "$EMAIL" ] || die "isi EMAIL untuk sertifikat SSL, contoh: EMAIL=kamu@contoh.com bash setup-vps.sh"

say "Memeriksa siapa yang memakai port 80 dan 443"
LISTEN="$(ss -ltnp 2>/dev/null | grep -E ':(80|443)\s' || true)"
echo "${LISTEN:-  (tidak ada)}"
if [ -n "$LISTEN" ] && ! echo "$LISTEN" | grep -q nginx && [ "${FORCE:-0}" != "1" ]; then
    die "port 80/443 dipakai program lain (bukan nginx). Hentikan dulu, atau jalankan ulang dengan FORCE=1 bila yakin."
fi
if grep -rqs "server_name[^;]*${DOMAIN}" /etc/nginx 2>/dev/null && [ ! -f /etc/nginx/conf.d/amagi-cli.conf ] && [ "${FORCE:-0}" != "1" ]; then
    die "nginx sudah punya konfigurasi untuk ${DOMAIN} di tempat lain. Periksa dulu agar tidak bentrok, atau jalankan ulang dengan FORCE=1."
fi

say "Memasang nginx dan certbot"
if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y nginx certbot python3-certbot-nginx
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y nginx certbot python3-certbot-nginx
else
    die "hanya apt dan dnf yang didukung skrip ini."
fi

say "Menyiapkan folder ${WEBROOT}"
mkdir -p "$WEBROOT"
chmod 755 "$WEBROOT"
[ -f "$WEBROOT/index.html" ] || cat > "$WEBROOT/index.html" <<HTML
<!doctype html><meta charset="utf-8"><title>Amagi CLI</title>
<h1>Amagi CLI</h1>
<p>Mac/Linux: <code>curl -fsSL https://${DOMAIN}/install.sh | bash</code></p>
<p>Windows: <code>iwr -useb https://${DOMAIN}/install.ps1 | iex</code></p>
HTML

say "Menulis konfigurasi nginx"
cat > /etc/nginx/conf.d/amagi-cli.conf <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};
    root ${WEBROOT};
    index index.html;
    autoindex off;
    server_tokens off;

    add_header X-Content-Type-Options nosniff always;

    # Skrip dan versi selalu diambil segar, supaya rilis baru langsung terlihat.
    location ~ ^/(install\.sh|install\.ps1|version\.txt|SHA256SUMS)\$ {
        default_type text/plain;
        add_header Cache-Control "no-cache" always;
        add_header X-Content-Type-Options nosniff always;
        try_files \$uri =404;
    }

    location ~ \.py\$ {
        default_type text/plain;
        add_header Cache-Control "no-cache" always;
        try_files \$uri =404;
    }

    location / {
        try_files \$uri \$uri/ =404;
    }
}
NGINX
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    say "ufw aktif: membuka port 80 dan 443 (aturan lain tidak diubah)"
    ufw allow 80/tcp
    ufw allow 443/tcp
fi

say "Meminta sertifikat SSL (Let's Encrypt)"
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

say "Selesai. Uji dari komputer lain:"
echo "  curl -sSI https://${DOMAIN}/"
echo "Lalu unggah file CLI dari repo:  VPS='root@IP' PORT=xxxx bash deploy/publish.sh"
