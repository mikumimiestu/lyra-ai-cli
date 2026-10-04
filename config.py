import os
import json
from styling import BOLD, COLOR_USER, RESET, DIM, RED, GREEN

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

# ─── API Key ──────────────────────────────────────────────────────────────────

def get_api_key(config: dict = None, force_prompt: bool = False):
    """
    Ambil API key dengan urutan prioritas:
      1. Environment variable ASTBYTE_API_KEY
      2. Config dict (sudah di-load sebelumnya)
      3. Prompt ke pengguna, simpan ke config
    """
    if config is None:
        config = load_config()

    if not force_prompt:
        # 1. Env variable
        env_key = os.getenv("ASTBYTE_API_KEY", "").strip()
        if env_key:
            return env_key

        # 2. Config file
        saved_key = config.get("api_key", "").strip()
        if saved_key:
            return saved_key

    # 3. Prompt user
    print(f"\n  {BOLD}{COLOR_USER}AstByte API Key belum ditemukan.{RESET}")
    print(f"  {DIM}API Key akan disimpan di {CONFIG_PATH}.{RESET}\n")

    while True:
        try:
            api_key = input("  Masukkan ASTBYTE_API_KEY Anda: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        if api_key:
            config["api_key"] = api_key
            save_config(config)
            print(f"  {GREEN}✓ API Key berhasil disimpan.{RESET}\n")
            return api_key

def reset_api_key(config: dict = None):
    """Hapus API key dari config."""
    if config is None:
        config = load_config()
    config.pop("api_key", None)
    save_config(config)
    # Hapus file lama jika ada hanya api_key
    if not config:
        try:
            os.remove(CONFIG_PATH)
        except Exception:
            pass
    print(f"  {GREEN}✓ API Key berhasil dihapus.{RESET}\n")

# ─── Version & Auto-Update ───────────────────────────────────────────────────
VERSION = "2.1.1"
GITHUB_REPO = "mikumimiestu/lyra-ai-cli"
RAW_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
FILES_TO_UPDATE = ["app.py", "styling.py", "spinner.py", "tools.py", "config.py", "setup.py", "version.txt"]

def parse_version_tuple(v_str: str):
    """Konversi string versi '2.1.0' atau 'v2.1.0' menjadi tuple angka (2, 1, 0)"""
    try:
        clean = v_str.strip().lstrip("v")
        return tuple(int(x) for x in clean.split(".") if x.isdigit())
    except Exception:
        return (0, 0, 0)

def check_remote_version(timeout=4.0):
    """
    Cek versi terbaru dari GitHub secara langsung.
    Return: (has_update: bool, latest_version_str: str)
    """
    try:
        import requests
        resp = requests.get(RAW_VERSION_URL, timeout=timeout)
        if resp.status_code == 200:
            remote_v = resp.text.strip()
            if parse_version_tuple(remote_v) > parse_version_tuple(VERSION):
                return True, remote_v
            return False, remote_v
    except Exception:
        pass
    return False, VERSION

def perform_update(target_dir=None):
    """
    Download file terbaru dari GitHub ke direktori instalasi.
    """
    import requests
    if not target_dir:
        install_dir = os.path.expanduser("~/.amagi-cli")
        if os.path.exists(os.path.join(install_dir, "app.py")):
            target_dir = install_dir
        else:
            target_dir = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(target_dir, exist_ok=True)
    updated_files = []
    for fname in FILES_TO_UPDATE:
        url = f"{RAW_BASE_URL}{fname}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                dest = os.path.join(target_dir, fname)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                updated_files.append(fname)
            else:
                return False, f"Gagal mengunduh {fname} (HTTP {resp.status_code})"
        except Exception as e:
            return False, f"Gagal mengunduh {fname}: {e}"

    return True, f"Berhasil memperbarui {len(updated_files)} file ke {target_dir}"

