import os
import json
from styling import BOLD, COLOR_USER, RESET, DIM, RED

CONFIG_PATH = os.path.expanduser("~/.amagi_cli_config.json")

def get_api_key(force_prompt=False):
    # 1. Check environment variable first (if not forcing prompt)
    if not force_prompt:
        api_key = os.getenv("ASTBYTE_API_KEY")
        if api_key:
            return api_key.strip()
        
        # 2. Check local config file
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
                    if api_key:
                        return api_key.strip()
            except Exception:
                pass

    # 3. Prompt user for API key if not found
    print(f"  {BOLD}{COLOR_USER}AstByte API Key tidak ditemukan.{RESET}")
    print(f"  {DIM}Kunci ini akan disimpan di {CONFIG_PATH} agar tidak perlu dimasukkan lagi.{RESET}")
    while True:
        api_key = input("  Masukkan ASTBYTE_API_KEY Anda: ").strip()
        if api_key:
            # Save to config file
            try:
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump({"api_key": api_key}, f, indent=4)
                print(f"  {BOLD}✓ API Key berhasil disimpan.{RESET}\n")
            except Exception as e:
                print(f"  {RED}Warning: Gagal menyimpan API key ke file: {e}{RESET}")
            return api_key

def reset_api_key():
    if os.path.exists(CONFIG_PATH):
        try:
            os.remove(CONFIG_PATH)
            return True
        except Exception as e:
            print(f"  {RED}Error menghapus file konfigurasi: {e}{RESET}")
    return False
