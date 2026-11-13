import os
import sys
import json
import time
import socket
import webbrowser
from styling import BOLD, COLOR_USER, RESET, DIM, RED, GREEN, choose, NOT_INTERACTIVE

CONFIG_PATH = os.path.expanduser("~/.amagi_cli_config.json")

# ─── Load / Save Config ───────────────────────────────────────────────────────

def load_config():
    """Muat seluruh config dari file. Return dict kosong jika tidak ada."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config: dict):
    """Simpan seluruh config ke file."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"  {RED}Warning: Gagal menyimpan config: {e}{RESET}")

# ─── Login & API Key ─────────────────────────────────────────────────────────

AUTH_BASE = "https://authx.astbyte.com"
ACCOUNT_TOKEN_PREFIX = "astcli_"

def uses_account_login(config: dict = None) -> bool:
    """True when requests go out with an AstByte account token (tier quota) instead of an API key."""
    if os.getenv("ASTBYTE_API_KEY", "").strip():
        return False
    if config is None:
        config = load_config()
    return config.get("auth_method") == "account" and bool(config.get("cli_token"))

def login_with_account(config: dict):
    """
    Masuk dengan akun AstByte (device flow): tampilkan kode, buka browser, tunggu persetujuan.
    Return token CLI dan simpan ke config, atau None bila dibatalkan / gagal.
    """
    import requests
    try:
        resp = requests.post(f"{AUTH_BASE}/api/cli/auth/start",
                             json={"device_name": f"Amagi CLI ({socket.gethostname()[:30]})"}, timeout=15)
        data = resp.json()["data"] if resp.status_code == 200 else None
    except Exception as e:
        print(f"  {RED}Tidak bisa menghubungi server login: {e}{RESET}\n")
        return None
    if not data:
        print(f"  {RED}Server login menolak permintaan (HTTP {resp.status_code}). Coba lagi sebentar.{RESET}\n")
        return None

    url = data["verification_url"]
    print(f"\n  {BOLD}{COLOR_USER}Login dengan akun AstByte{RESET}")
    print(f"  Buka halaman ini dan setujui kode {BOLD}{data['user_code']}{RESET}:")
    print(f"  {BOLD}{url}{RESET}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print(f"  {DIM}Menunggu persetujuan... (Ctrl+C untuk batal){RESET}")

    deadline = time.time() + int(data.get("expires_in", 600))
    interval = max(2, int(data.get("interval", 3)))
    try:
        while time.time() < deadline:
            time.sleep(interval)
            try:
                poll = requests.post(f"{AUTH_BASE}/api/cli/auth/poll",
                                     json={"device_code": data["device_code"]}, timeout=15)
                body = poll.json()
            except Exception:
                continue   # jaringan putus sebentar; coba lagi sampai kode kedaluwarsa
            state = body.get("status")
            if state == "approved":
                config["auth_method"] = "account"
                config["cli_token"] = body["token"]
                config["cli_user"] = (body.get("user") or {}).get("email", "")
                save_config(config)
                who = f" sebagai {config['cli_user']}" if config["cli_user"] else ""
                quota = body.get("quota") or {}
                tier = str(quota.get("tier", "")).upper()
                extra = f" Kuota {tier}: {quota['limit']:,} token/hari." if quota.get("limit") else ""
                print(f"  {GREEN}✓ Berhasil masuk{who}.{extra}{RESET}\n")
                return body["token"]
            if state in ("denied", "expired"):
                print(f"  {RED}{body.get('message', 'Login dibatalkan.')}{RESET}\n")
                return None
    except KeyboardInterrupt:
        print(f"\n  {DIM}Login dibatalkan.{RESET}\n")
        return None
    print(f"  {RED}Kode kedaluwarsa. Jalankan /login untuk mencoba lagi.{RESET}\n")
    return None

def fetch_quota(config: dict = None):
    """Sisa kuota token (jendela 5 jam dan mingguan) untuk login akun. Return dict atau None (mode API key / gagal)."""
    if config is None:
        config = load_config()
    if not uses_account_login(config):
        return None
    try:
        import requests
        resp = requests.get(f"{AUTH_BASE}/api/cli/quota",
                            headers={"Authorization": f"Bearer {config['cli_token']}"}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data")
    except Exception:
        pass
    return None

def logout(config: dict = None):
    """Hapus login akun dari perangkat ini (token di server tetap bisa dicabut dari dashboard)."""
    if config is None:
        config = load_config()
    for key in ("cli_token", "cli_user", "auth_method"):
        config.pop(key, None)
    save_config(config)
    print(f"  {GREEN}✓ Keluar dari akun AstByte.{RESET}\n")

def _choose_login_method():
    """0 = login akun AstByte, 1 = API key, None = batal."""
    options = [
        ("Login dengan akun AstByte", "Pakai kuota token sesuai tier akunmu (5 jam + mingguan)"),
        ("Pakai API key", "Bayar sesuai pemakaian dari saldo developer"),
    ]
    picked = choose("Masuk ke Amagi CLI", options, 0, "Pilih cara memakai Amagi CLI.")
    if picked is not NOT_INTERACTIVE:
        return picked
    print(f"\n  {BOLD}{COLOR_USER}Masuk ke Amagi CLI{RESET}")
    for number, (label, description) in enumerate(options, 1):
        print(f"  {number}. {BOLD}{label}{RESET} {DIM}- {description}{RESET}")
    try:
        choice = input(f"\n  Pilihan (1-{len(options)}) ❯ ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    return int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(options) else None

def get_api_key(config: dict = None, force_prompt: bool = False):
    """
    Ambil kredensial untuk header Authorization (token login akun atau API key):
      1. Environment variable ASTBYTE_API_KEY
      2. Login akun AstByte yang tersimpan (auth_method = account)
      3. API key yang tersimpan di config
      4. Tanya pengguna: login akun atau API key, lalu simpan
    """
    if config is None:
        config = load_config()

    if not force_prompt:
        env_key = os.getenv("ASTBYTE_API_KEY", "").strip()
        if env_key:
            return env_key

        if config.get("auth_method") == "account" and config.get("cli_token"):
            return config["cli_token"]

        saved_key = config.get("api_key", "").strip()
        if saved_key:
            return saved_key

    while True:
        method = _choose_login_method()
        if method is None:
            continue
        if method == 0:
            token = login_with_account(config)
            if token:
                return token
            continue
        break

    print(f"\n  {BOLD}{COLOR_USER}Masukkan API key AstByte.{RESET}")
    print(f"  {DIM}API Key akan disimpan di {CONFIG_PATH}.{RESET}\n")

    while True:
        try:
            api_key = input("  Masukkan ASTBYTE_API_KEY Anda: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        if api_key:
            config["api_key"] = api_key
            config["auth_method"] = "api_key"
            save_config(config)
            print(f"  {GREEN}✓ API Key berhasil disimpan.{RESET}\n")
            return api_key

def reset_api_key(config: dict = None):
    """Hapus API key dan login akun dari config."""
    if config is None:
        config = load_config()
    for key in ("api_key", "cli_token", "cli_user", "auth_method"):
        config.pop(key, None)
    save_config(config)
    # Hapus file lama jika ada hanya api_key
    if not config:
        try:
            os.remove(CONFIG_PATH)
        except Exception:
            pass
    print(f"  {GREEN}✓ Kredensial berhasil dihapus.{RESET}\n")

# ─── Version & Auto-Update ───────────────────────────────────────────────────
VERSION = "2.12.9"
GITHUB_REPO = "mikumimiestu/lyra-ai-cli"
# Where releases come from, in order. The first source publishes SHA256SUMS next to the files, and /update
# refuses files that do not match it. GitHub is the fallback (no checksum file, HTTPS only). Older installs only
# know GitHub, which is why releases are still pushed there too.
PRIMARY_UPDATE_URL = "https://astbyte.my.id/"
GITHUB_UPDATE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
RAW_VERSION_URL = f"{GITHUB_UPDATE_URL}version.txt"      # kept for older callers
RAW_BASE_URL = GITHUB_UPDATE_URL


def update_sources():
    """[(base url, publishes SHA256SUMS)], most trusted first. LYRA_UPDATE_URL replaces the primary (mirrors, tests)."""
    override = os.environ.get("LYRA_UPDATE_URL", "").strip()
    primary = override or PRIMARY_UPDATE_URL
    if not primary.endswith("/"):
        primary += "/"
    return [(primary, True), (GITHUB_UPDATE_URL, False)]


FILES_TO_UPDATE = ["app.py", "styling.py", "spinner.py", "tools.py", "config.py", "memory.py", "reminder.py", "setup.py", "version.txt"]

def parse_version_tuple(v_str: str):
    """Konversi string versi '2.1.0' atau 'v2.1.0' menjadi tuple angka (2, 1, 0)"""
    try:
        clean = v_str.strip().lstrip("v")
        return tuple(int(x) for x in clean.split(".") if x.isdigit())
    except Exception:
        return (0, 0, 0)

def check_remote_version(timeout=4.0):
    """
    Cek versi terbaru dari server rilis (lalu GitHub bila server utama tidak terjangkau).
    Return: (has_update: bool, latest_version_str: str)
    """
    try:
        import requests
    except Exception:
        return False, VERSION
    for base, _checksums in update_sources():
        try:
            resp = requests.get(f"{base}version.txt", timeout=timeout)
            if resp.status_code == 200 and parse_version_tuple(resp.text) != (0, 0, 0):
                remote_v = resp.text.strip()
                return parse_version_tuple(remote_v) > parse_version_tuple(VERSION), remote_v
        except Exception:
            continue
    return False, VERSION

REQUIRED_PACKAGES = (("requests", "requests"), ("prompt_toolkit", "prompt_toolkit>=3.0.36,<4"))


def missing_packages():
    """pip specs of the required packages this Python cannot import."""
    import importlib.util
    return [spec for module, spec in REQUIRED_PACKAGES if importlib.util.find_spec(module) is None]


def install_packages(specs, timeout=300):
    """pip install into the interpreter that runs Lyra (the installer's venv). Returns (ok, message)."""
    import subprocess
    try:
        done = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *specs],
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if done.returncode == 0:
        return True, "terpasang"
    lines = (done.stderr or done.stdout or "").strip().splitlines()
    return False, lines[-1] if lines else f"pip keluar dengan kode {done.returncode}"


def parse_checksums(text):
    """{filename: sha256} from a SHA256SUMS file ("<hash>  <name>" per line)."""
    sums = {}
    for line in str(text).splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    return sums


def fetch_release(base, verify, timeout=10):
    """Download every file of a release into memory. Returns ({name: bytes}, None) or (None, reason).

    Nothing is written to disk here, so a failure half way never leaves a mix of old and new files.
    """
    import hashlib
    import requests
    sums = {}
    if verify:
        try:
            resp = requests.get(f"{base}SHA256SUMS", timeout=timeout)
        except Exception as e:
            return None, f"SHA256SUMS: {e}"
        if resp.status_code != 200:
            return None, f"SHA256SUMS tidak tersedia (HTTP {resp.status_code})"
        sums = parse_checksums(resp.text)
    files = {}
    for fname in FILES_TO_UPDATE:
        try:
            resp = requests.get(f"{base}{fname}", timeout=timeout)
        except Exception as e:
            return None, f"{fname}: {e}"
        if resp.status_code != 200:
            return None, f"{fname} (HTTP {resp.status_code})"
        content = resp.content if isinstance(resp.content, (bytes, bytearray)) else str(resp.text).encode("utf-8")
        if verify:
            expected = sums.get(fname)
            if not expected:
                return None, f"{fname} tidak ada di SHA256SUMS"
            if hashlib.sha256(content).hexdigest() != expected:
                return None, f"checksum {fname} tidak cocok (file rusak atau diubah)"
        files[fname] = bytes(content)
    return files, None


def perform_update(target_dir=None):
    """
    Unduh rilis terbaru ke direktori instalasi: server utama dengan verifikasi SHA256SUMS, GitHub sebagai cadangan.
    File baru ditulis hanya setelah semuanya lengkap dan lolos verifikasi.
    """
    if not target_dir:
        install_dir = os.path.expanduser("~/.amagi-cli")
        if os.path.exists(os.path.join(install_dir, "app.py")):
            target_dir = install_dir
        else:
            target_dir = os.path.dirname(os.path.abspath(__file__))

    files, source, problems = None, "", []
    for base, verify in update_sources():
        files, reason = fetch_release(base, verify)
        if files is not None:
            source = base.split("/")[2]
            break
        problems.append(f"{base.split('/')[2]}: {reason}")
    if files is None:
        return False, "Gagal mengunduh pembaruan. " + "; ".join(problems)

    os.makedirs(target_dir, exist_ok=True)
    try:
        staged = []
        for fname, content in files.items():
            dest = os.path.join(target_dir, fname)
            temp = dest + ".new"
            with open(temp, "wb") as f:
                f.write(content)
            staged.append((temp, dest))
        for temp, dest in staged:
            os.replace(temp, dest)
    except OSError as e:
        return False, f"Gagal menulis file pembaruan: {e}"

    note = ""
    missing = missing_packages()      # versions before 2.3 shipped without prompt_toolkit; /update only copies files
    if missing:
        ok, detail = install_packages(missing)
        note = f"; paket {', '.join(missing)} " + ("ikut dipasang" if ok else f"belum terpasang ({detail})")
    checked = "terverifikasi" if source != GITHUB_UPDATE_URL.split("/")[2] else "tanpa checksum"
    return True, f"Berhasil memperbarui {len(files)} file ke {target_dir} (dari {source}, {checked}){note}"
