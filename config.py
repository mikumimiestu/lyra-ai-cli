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
