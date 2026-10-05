import sys
import os

# Pastikan direktori tempat file ini berada selalu ada di sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import requests
import json
import re
import time
import threading

# ─── Import custom modules ────────────────────────────────────────────────────

from styling import (
    RESET, BOLD, DIM, ITALIC, WHITE, GREEN, RED, YELLOW, CYAN,
    COLOR_USER, COLOR_LYRA, COLOR_BORDER, COLOR_DIM, COLOR_TITLE,
    COLOR_ACCENT, print_logo, rgb_to_ansi, hex_to_rgb,
    get_terminal_width, strip_ansi, str_width, format_markdown_line,
    render_header, render_footer_bar, render_markdown_table,
    render_full_divider, format_clean_thinking_line, parse_markdown_table
)
from spinner import Spinner
from tools import (
    list_directory, read_file, write_file, execute_command,
    create_directory, init_project, DEFAULT_TIMEOUT,
    get_system_time, tool_save_memory, tool_read_memory, tool_clear_memory,
    tool_set_reminder, tool_list_reminders, tool_cancel_reminder
)
from config import (
    get_api_key, reset_api_key, save_config, load_config,
    VERSION, check_remote_version, perform_update
)
from memory import read_memory, save_memory, clear_memory
from reminder import (
    add_reminder, list_reminders, cancel_reminder,
    ensure_daemon_running, is_daemon_running, run_reminder_daemon_loop
)

# ─── Constants ────────────────────────────────────────────────────────────────
API_URL = "https://authx.astbyte.com/v1/chat/completions"

# ─── Model Definitions ────────────────────────────────────────────────────────
MODELS = [
    {
        "id":                 "lyra-luma-flash",
        "name":               "Lyra Luma 5.5",
        "supports_reasoning": False,
    },
    {
        "id":                 "lyra-nebula-4",
        "name":               "Lyra Nebula 4",
        "supports_reasoning": True,
    },
    {
        "id":                 "lyra-orpheus-6",
        "name":               "Lyra Orpheus 6",
        "supports_reasoning": True,
    },
    {
        "id":                 "lyra-eurydice-6",
        "name":               "Lyra Eurydice 6",
        "supports_reasoning": True,
    },
]

DEFAULT_MODEL_INDEX = 2   # Lyra Orpheus 6

REASONING_EFFORTS = [
    {"id": "low", "name": "Cepat (Low effort)", "desc": "Penalaran singkat, waktu respon super cepat"},
    {"id": "medium", "name": "Sedang (Medium effort)", "desc": "Penalaran seimbang, analisa lebih komprehensif"},
]

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """Kamu adalah Lyra / Amagi, asisten AI canggih dari AstByte yang berjalan di terminal komputer pengguna.
Kamu memiliki akses ke tools komputer lokal pengguna, memori jangka panjang (.md), sistem waktu laptop, pengingat otomatis, dan mampu membangun project fullstack skala besar.

[WAKTU SISTEM LAPTOP PENGGUNA SAAT INI]:
{system_time}

[ISI MEMORI TERSIMPAN (~/.amagi_memory.md)]:
{memory_section}

Untuk memanggil tool, sertakan blok XML ini TEPAT di akhir jawabanmu:
<tool_call>
{{
  "name": "nama_tool",
  "arguments": {{
    "key": "value"
  }}
}}
</tool_call>

Daftar tool yang tersedia:
- list_directory   : Mendaftar file/folder. Args: {{"path": ".", "recursive": false, "depth": 2}}
- read_file        : Membaca teks file.     Args: {{"filepath": "path/ke/file"}}
- write_file       : Menulis/edit file.     Args: {{"filepath": "path", "content": "isi file"}}
- create_directory : Membuat folder baru.   Args: {{"dirpath": "path/ke/folder"}}
- execute_command  : Jalankan terminal.     Args: {{"command": "perintah", "cwd": "/optional/path", "timeout": 600}}
- init_project     : Scaffolding project baru (NON-INTERAKTIF, langsung jalan).
                     Args: {{"project_type": "TIPE", "project_name": "nama", "target_dir": "/optional"}}
- save_memory      : Simpan fakta/catatan ke file memori ~/.amagi_memory.md. Args: {{"content": "catatan", "mode": "append"}}
- read_memory      : Baca isi file memori ~/.amagi_memory.md. Args: {{}}
- get_system_time  : Ambil tanggal, waktu, dan timezone laptop pengguna. Args: {{}}
- set_reminder     : Setel pengingat baru & notifikasi popup desktop laptop. Amagi akan bangun sendiri menyalakan notifikasi! Args: {{"message": "pesan", "time_input": "10m" / "14:30" / "YYYY-MM-DD HH:MM"}}
- list_reminders   : Daftar pengingat tersimpan. Args: {{"status": "pending"}}
- cancel_reminder  : Batalkan pengingat. Args: {{"reminder_id": "rem_..."}}

Panduan fitur khusus:
1. Memori: Jika pengguna meminta "ingat ini...", "simpan ke memori...", atau memberikan fakta penting pengguna, gunakan tool `save_memory`.
2. Tanggal & Waktu: Selalu gunakan informasi waktu laptop terkini di atas saat menjawab pertanyaan terkait waktu.
3. Pengingat & Notifikasi: Jika pengguna minta ingatkan sesuatu ("ingatkan saya 10 menit lagi untuk...", "set alarm jam 8 pagi"), gunakan tool `set_reminder`.
4. Jangan sebutkan format XML/tool ini secara mentah kepada pengguna.
"""

def get_current_system_prompt():
    """Menghasilkan System Prompt dinamis dengan waktu dan memori terbaru."""
    time_info = get_system_time()
    mem_info = read_memory()
    return SYSTEM_PROMPT_TEMPLATE.format(
        system_time=time_info,
        memory_section=mem_info if mem_info.strip() else "(Belum ada memori tersimpan)"
    )


# ─── Tool Call Parser ─────────────────────────────────────────────────────────
def extract_tool_call(content):
    """Ekstrak tool_call XML dari respons AI."""
    match = re.search(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
    if match:
        json_str    = match.group(1).strip()
        text_before = content.split("<tool_call>")[0].strip()
        return text_before, json_str
    return content, None

# ─── Render Functions ─────────────────────────────────────────────────────────
def render_model_selector(current_idx):
    """Render model selector interaktif sederhana hanya dengan nama model."""
    term_w = get_terminal_width()
    w = max(50, min(term_w - 6, 80))
    B, T, A, D, Y, R = COLOR_BORDER, COLOR_TITLE, COLOR_ACCENT, COLOR_DIM, YELLOW, RESET

    def print_line(content):
        v_len = str_width(content)
        pad = max(0, w - v_len)
        sp = " " * pad
        print(f"  {B}│{R}{content}{sp}{B}│{R}")

    top_b = "─" * w
    print(f"\n  {B}╭{top_b}╮{R}")
    print_line(f"  {BOLD}{A}Pilih Model AI{R}")
    print_line(f"  {D}Ganti model AI untuk sesi ini dan simpan di preferensi.{R}")
    print_line("")

    for i, m in enumerate(MODELS):
        selected = (i == current_idx)
        cursor   = f"{BOLD}{A}❯{R}" if selected else " "
        num_str  = f"{BOLD}{A}{i+1}.{R}" if selected else f"{BOLD}{T}{i+1}.{R}"
        
        name_plain = m['name'] + (" ✓" if selected else "")
        name_formatted = f"{BOLD}{COLOR_LYRA}{name_plain}{R}" if selected else f"{BOLD}{T}{name_plain}{R}"

        print_line(f" {cursor} {num_str} {name_formatted}")
        
    print_line("")
    print_line(f"  {D}Masukkan nomor (1-{len(MODELS)}) lalu Enter • Tekan Enter untuk batal{R}")
    bot_b = "─" * w
    print(f"  {B}╰{bot_b}╯{R}")

def handle_reasoning_command(config):
    """Pilih tingkat penalaran (cepat / sedang)."""
    current_effort = config.get("reasoning_effort", "medium")
    print(f"\n  {BOLD}{COLOR_LYRA}✦ Pilih Tingkat Penalaran (Reasoning Effort){RESET}\n")
    print(f"  1. {BOLD}Cepat (Low effort){RESET}   {DIM}- Penalaran singkat, waktu respon super cepat{RESET}")
    print(f"  2. {BOLD}Sedang (Medium effort){RESET} {DIM}- Penalaran mendalam seimbang{RESET}")
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Pilihan (1-2) ❯{RESET} ").strip()
        if choice == "1":
            config["reasoning_effort"] = "low"
            save_config(config)
            print(f"  {GREEN}✓ Tingkat penalaran diubah ke: Cepat (Low effort){RESET}\n")
            return "low"
        elif choice == "2":
            config["reasoning_effort"] = "medium"
            save_config(config)
            print(f"  {GREEN}✓ Tingkat penalaran diubah ke: Sedang (Medium effort){RESET}\n")
            return "medium"
        else:
            print(f"  {DIM}Tingkat penalaran tidak diubah.{RESET}\n")
            return current_effort
    except (EOFError, KeyboardInterrupt):
        print(f"  {DIM}Dibatalkan.{RESET}\n")
        return current_effort

def handle_model_command(config):
    """Interaktif model selector & reasoning selector."""
    current_idx = config.get("model_index", DEFAULT_MODEL_INDEX)
    if current_idx >= len(MODELS):
        current_idx = DEFAULT_MODEL_INDEX
    render_model_selector(current_idx)
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Nomor model ❯{RESET} ").strip()
        if choice == "":
            print(f"  {DIM}Model tidak diubah.{RESET}\n")
            return current_idx
        idx = int(choice) - 1
        if 0 <= idx < len(MODELS):
            config["model_index"] = idx
            m = MODELS[idx]
            print(f"\n  {GREEN}✓{RESET} Model diubah ke {BOLD}{COLOR_LYRA}{m['name']}{RESET}")
            if m.get("supports_reasoning"):
                handle_reasoning_command(config)
            else:
                config["reasoning_effort"] = "low"
            save_config(config)
            print()
            return idx
        else:
            print(f"  {RED}Nomor tidak valid.{RESET}\n")
            return current_idx
    except (ValueError, EOFError):
        print(f"  {RED}Input tidak valid.{RESET}\n")
        return current_idx

def handle_update_command(interactive=True):
    """Interaktif cek & perbarui Lyra CLI ke versi terbaru dari GitHub."""
    print(f"\n  {BOLD}{COLOR_LYRA}✦ Cek Pembaruan Lyra CLI{RESET}")
    spinner = Spinner("Memeriksa versi terbaru di GitHub...")
    spinner.start()
    has_update, latest_version = check_remote_version(timeout=6.0)
    spinner.stop()

    if not has_update:
        print(f"  {GREEN}✓ Lyra CLI Anda sudah menggunakan versi terbaru (v{VERSION}).{RESET}\n")
        return

    print(f"  {YELLOW}⚡ Versi terbaru tersedia: {BOLD}v{latest_version}{RESET} {DIM}(Versi saat ini: v{VERSION}){RESET}\n")
    if interactive:
        try:
            choice = input(f"  {BOLD}{COLOR_USER}Apakah Anda ingin mengunduh & memperbarui sekarang? (y/n) ❯{RESET} ").strip().lower()
            if choice != 'y':
                print(f"  {DIM}Pembaruan dibatalkan.{RESET}\n")
                return
        except (EOFError, KeyboardInterrupt):
            print(f"  {DIM}Dibatalkan.{RESET}\n")
            return

    spin_up = Spinner("Mengunduh & menginstal file terbaru dari GitHub...")
    spin_up.start()
    success, msg = perform_update()
    spin_up.stop()

    if success:
        print(f"  {GREEN}✓ {msg}{RESET}")
        print(f"  {BOLD}{COLOR_ACCENT}✦ Lyra CLI berhasil diperbarui ke v{latest_version}! Silakan jalankan ulang 'amagi'.{RESET}\n")
    else:
        print(f"  {RED}✖ Gagal memperbarui: {msg}{RESET}\n")

def handle_memory_command():
    """Interaktif pengelola memori Amagi AI."""
    print(f"\n  {BOLD}{COLOR_LYRA}🧠 Memori Jangka Panjang Amagi AI (~/.amagi_memory.md){RESET}\n")
    current_mem = read_memory()
    print(f"  {DIM}--- Isi Memori Saat Ini ---{RESET}")
    print(current_mem.strip() if current_mem.strip() else f"  {DIM}(Memori masih kosong){RESET}")
    print(f"  {DIM}---------------------------{RESET}\n")
    print(f"  1. {BOLD}Tambah Catatan Baru{RESET}")
    print(f"  2. {BOLD}Reset / Bersihkan Memori{RESET}")
    print(f"  3. {BOLD}Kembali{RESET}")
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Pilihan (1-3) ❯{RESET} ").strip()
        if choice == "1":
            note = input(f"  {BOLD}{COLOR_USER}Catatan/Fakta baru ❯{RESET} ").strip()
            if note:
                res = save_memory(note)
                print(f"  {GREEN}{res}{RESET}\n")
        elif choice == "2":
            confirm = input(f"  {RED}Yakin ingin menghapus seluruh isi memori? (y/n) ❯{RESET} ").strip().lower()
            if confirm == 'y':
                res = clear_memory()
                print(f"  {GREEN}{res}{RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()

def handle_time_command():
    """Menampilkan tanggal, waktu, dan timezone laptop pengguna."""
    print(f"\n  {BOLD}{COLOR_LYRA}⏰ Waktu Sistem Laptop Pengguna{RESET}\n")
    print(f"  {get_system_time()}\n")

def handle_reminder_command():
    """Interaktif pengelola pengingat & notifikasi desktop."""
    print(f"\n  {BOLD}{COLOR_LYRA}🔔 Pengingat & Notifikasi Laptop Amagi AI{RESET}")
    daemon_st = f"{GREEN}Aktif (Background Running){RESET}" if is_daemon_running() else f"{YELLOW}Mati (akan menyala otomatis){RESET}"
    print(f"  {DIM}Status Daemon Background: {daemon_st}{RESET}\n")
    
    print(tool_list_reminders())
    print()
    print(f"  1. {BOLD}Buat Pengingat Baru{RESET}")
    print(f"  2. {BOLD}Batalkan Pengingat{RESET}")
    print(f"  3. {BOLD}Pastikan Daemon Background Aktif{RESET}")
    print(f"  4. {BOLD}Kembali{RESET}")
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Pilihan (1-4) ❯{RESET} ").strip()
        if choice == "1":
            msg = input(f"  {BOLD}{COLOR_USER}Pesan pengingat ❯{RESET} ").strip()
            waktu = input(f"  {BOLD}{COLOR_USER}Waktu (cth: '10m', '1h', '14:30', '30s') ❯{RESET} ").strip()
            if msg and waktu:
                res = tool_set_reminder(message=msg, time_input=waktu)
                print(f"\n  {res}\n")
        elif choice == "2":
            rem_id = input(f"  {BOLD}{COLOR_USER}ID Pengingat yang ingin dibatalkan (cth: rem_123) ❯{RESET} ").strip()
            if rem_id:
                res = tool_cancel_reminder(rem_id)
                print(f"  {res}\n")
        elif choice == "3":
            ensure_daemon_running()
            print(f"  {GREEN}✓ Daemon pengingat latar belakang telah diaktifkan!{RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()

def render_help():
    """Tampilkan panel bantuan."""
    w = min(get_terminal_width() - 4, 80)
    B, T, A, D, Y, R = COLOR_BORDER, COLOR_TITLE, COLOR_ACCENT, COLOR_DIM, YELLOW, RESET
    
    def print_line(content):
        v_len = str_width(content)
        pad = max(0, w - v_len)
        print(f"  {B}│{R}{content}{' ' * pad}{B}│{R}")

    print(f"\n  {B}╭{'─' * w}╮{R}")
    print_line(f"  {BOLD}{A}Perintah Lyra CLI (v{VERSION}){R}")
    print_line("")
    
    cmds = [
        ("/model",          "Buka pilihan model AI"),
        ("/reasoning",      "Pilih tingkat penalaran (cepat / sedang)"),
        ("/memory",         "Kelola memori jangka panjang (.md)"),
        ("/time",           "Lihat tanggal, waktu & timezone laptop"),
        ("/reminder",       "Kelola pengingat & notifikasi desktop"),
        ("/update",         "Cek & perbarui Lyra CLI ke versi terbaru"),
        ("/version",        "Tampilkan versi Lyra CLI saat ini"),
        ("/project",        "Buat project baru (React, Laravel, PHP, dll.)"),
        ("/clear",          "Bersihkan riwayat percakapan"),
        ("/history",        "Tampilkan ringkasan riwayat chat"),
        ("/cd <path>",      "Ganti direktori kerja aktif"),
        ("/ls [path]",      "Tampilkan isi direktori"),
        ("/run <cmd>",      "Langsung jalankan perintah terminal"),
        ("/reset-key",      "Hapus & atur ulang API Key"),
        ("/help",           "Tampilkan bantuan ini"),
        ("exit / quit",     "Keluar dari Lyra CLI"),
    ]
    
    for cmd, desc in cmds:
        print_line(f"   {BOLD}{Y}{cmd:<18}{R}  {D}{desc}{R}")
        
    print_line("")
    print(f"  {B}╰{'─' * w}╯{R}\n")



# ─── Stream Response Handler ─────────────────────────────────────────────────
def stream_ai_response(headers, data, model_info=None):
    """
    Stream respons AI secara langsung tanpa kotak border, dengan format Markdown dan Tabel Grid ala Claude CLI.
    """
    model_name = model_info.get("name", "Lyra") if model_info else "Lyra"
    reasoning_effort = data.get("reasoning_effort", "medium")
    reasoning_label = "cepat" if reasoning_effort == "low" else "sedang"
    
    spinner_msg = f"{model_name} (penalaran {reasoning_label}) sedang berpikir..."
    spinner = Spinner(spinner_msg)
    spinner.start()
    
    start_time = time.time()

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={**data, "stream": True},
            stream=True,
            timeout=DEFAULT_TIMEOUT,
        )
    except Exception as e:
        spinner.stop()
        return 0, f"Error koneksi: {e}"

    spinner.stop()

    if response.status_code != 200:
        return response.status_code, response.text

    thinking_printed = False
    in_thinking_mode = False

    full_content = ""
    thinking_buffer = ""
    main_buffer = ""
    table_buffer = []
    markdown_state = {'in_code': False, 'lang': ''}
    tool_call_detected = False

    def flush_table_buffer():
        nonlocal table_buffer
        if table_buffer:
            tbl_lines = render_markdown_table(table_buffer)
            for t_line in tbl_lines:
                print(t_line)
            sys.stdout.flush()
            table_buffer = []

    try:
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line_str = raw_line.decode('utf-8')
            if line_str.startswith("data: "):
                payload_str = line_str[6:].strip()
                if payload_str == "[DONE]":
                    break
                try:
                    payload = json.loads(payload_str)
                    delta = payload["choices"][0]["delta"]
                    content_chunk = delta.get("content", "")
                    reasoning_chunk = delta.get("reasoning_content", "") or delta.get("reasoning", "")
                except Exception:
                    continue

                # 1. Explicit reasoning chunk dari API
                if reasoning_chunk:
                    if not thinking_printed:
                        print(f"\n  {COLOR_DIM}{ITALIC}🧠 Process penalaran ({reasoning_label})...{RESET}")
                        thinking_printed = True
                        in_thinking_mode = True

                    thinking_buffer += reasoning_chunk
                    while "\n" in thinking_buffer:
                        line_to_print, thinking_buffer = thinking_buffer.split("\n", 1)
                        formatted_t = format_clean_thinking_line(line_to_print)
                        if formatted_t:
                            print(formatted_t)
                        sys.stdout.flush()
                    continue

                if not content_chunk:
                    continue

                full_content += content_chunk

                # 2. Tag <think> dalam teks
                if "<think>" in full_content and "</think>" not in full_content:
                    if not thinking_printed:
                        print(f"\n  {COLOR_DIM}{ITALIC}🧠 Process penalaran ({reasoning_label})...{RESET}")
                        thinking_printed = True
                        in_thinking_mode = True
                    
                    think_chunk = content_chunk.replace("<think>", "")
                    thinking_buffer += think_chunk
                    while "\n" in thinking_buffer:
                        line_to_print, thinking_buffer = thinking_buffer.split("\n", 1)
                        formatted_t = format_clean_thinking_line(line_to_print)
                        if formatted_t:
                            print(formatted_t)
                        sys.stdout.flush()
                    continue

                # 3. Transisi saat tag </think> selesai atau sebelum main buffer diprint
                if thinking_printed and (in_thinking_mode or "</think>" in full_content):
                    if thinking_buffer:
                        formatted_t = format_clean_thinking_line(thinking_buffer)
                        if formatted_t:
                            print(formatted_t)
                        thinking_buffer = ""
                    if in_thinking_mode:
                        in_thinking_mode = False
                        print()
                        render_full_divider(COLOR_BORDER)
                        print()

                # 4. Deteksi awal tool call XML
                if "<tool_call>" in full_content or tool_call_detected:
                    tool_call_detected = True
                    continue

                # 5. Render baris konten utama
                clean_chunk = content_chunk.replace("</think>", "")
                main_buffer += clean_chunk
                
                while "\n" in main_buffer:
                    line_to_print, main_buffer = main_buffer.split("\n", 1)
                    stripped_l = line_to_print.strip()
                    
                    if stripped_l.startswith("|"):
                        table_buffer.append(line_to_print)
                    else:
                        flush_table_buffer()
                        row, markdown_state = format_markdown_line(line_to_print, markdown_state)
                        print(row)
                    sys.stdout.flush()

        # Flush sisa buffer jika ada
        if thinking_buffer:
            formatted_t = format_clean_thinking_line(thinking_buffer)
            if formatted_t:
                print(formatted_t)

        if main_buffer and not tool_call_detected:
            stripped_l = main_buffer.strip()
            if stripped_l.startswith("|"):
                table_buffer.append(main_buffer)
                flush_table_buffer()
            else:
                flush_table_buffer()
                row, markdown_state = format_markdown_line(main_buffer, markdown_state)
                print(row)
            sys.stdout.flush()
        else:
            flush_table_buffer()

        elapsed = time.time() - start_time
        if not tool_call_detected and full_content.strip():
            print(f"\n  {COLOR_DIM}* Selesai dalam {elapsed:.1f}s{RESET}")

        return 200, full_content

    except Exception as e:
        flush_table_buffer()
        return 0, f"Error streaming: {e}"

# ─── Slash Command Handlers ───────────────────────────────────────────────────
def handle_project_command(cwd):
    """Wizard pembuatan project baru."""
    print(f"\n  {BOLD}{COLOR_LYRA}✦ Buat Project Baru{RESET}\n")
    print(f"  {DIM}Tipe yang didukung: react, next, vue, laravel, php, express, django, fastapi, flutter, node{RESET}\n")
    try:
        ptype  = input(f"  {BOLD}{COLOR_USER}Tipe project ❯{RESET} ").strip().lower()
        pname  = input(f"  {BOLD}{COLOR_USER}Nama project ❯{RESET} ").strip()
        pdir_input = input(f"  {BOLD}{COLOR_USER}Direktori tujuan (kosong = cwd) ❯{RESET} ").strip()
        target = pdir_input if pdir_input else cwd
        if not ptype or not pname:
            print(f"  {RED}Tipe dan nama project tidak boleh kosong.{RESET}\n")
            return

        print(f"\n  {DIM}Memulai scaffolding {ptype} project '{pname}' di {target}...{RESET}\n")
        result = init_project(ptype, pname, target_dir=target)
        print(f"\n  {GREEN}Hasil:{RESET}\n{result}\n")
    except (EOFError, KeyboardInterrupt):
        print(f"\n  {DIM}Dibatalkan.{RESET}\n")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # Cek jika dipanggil dalam mode daemon
    if len(sys.argv) > 1 and sys.argv[1] in ("--daemon", "daemon"):
        run_reminder_daemon_loop()
        sys.exit(0)

    config  = load_config()
    api_key = get_api_key(config=config)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    model_idx = config.get("model_index", DEFAULT_MODEL_INDEX)
    if model_idx >= len(MODELS):
        model_idx = DEFAULT_MODEL_INDEX
        config["model_index"] = model_idx
        save_config(config)

    reasoning_effort = config.get("reasoning_effort", "medium")

    # Inisialisasi system prompt dengan waktu dan memori terbaru
    messages = [{"role": "system", "content": get_current_system_prompt()}]
    active_cwd = os.getcwd()

    # Pastikan daemon pengingat latar belakang berjalan
    ensure_daemon_running()

    # ── Background Version Check ──────────────────────────────────────────────
    update_state = {"has_update": False, "latest_version": VERSION, "notified": False}

    def _bg_check_update():
        has_up, latest_v = check_remote_version(timeout=4.0)
        if has_up:
            update_state["has_update"] = True
            update_state["latest_version"] = latest_v

    threading.Thread(target=_bg_check_update, daemon=True).start()

    # Render Logo Gradasi Amagi & Header
    print_logo()
    render_header(MODELS[model_idx]["name"], reasoning_effort, active_cwd)

    # ── Loop utama ────────────────────────────────────────────────────────────
    while True:
        try:
            model_info = MODELS[model_idx]
            current_effort = config.get("reasoning_effort", "medium")

            if update_state["has_update"] and not update_state["notified"]:
                update_state["notified"] = True
                print(f"  {YELLOW}⚡ Versi terbaru (v{update_state['latest_version']}) tersedia! Ketik {BOLD}/update{RESET}{YELLOW} untuk memperbarui otomatis.{RESET}\n")

            render_full_divider(COLOR_BORDER)
            prompt_str = f"  {BOLD}{COLOR_USER}❯{RESET} "
            user_input = input(prompt_str).strip()

            if not user_input:
                continue

            # ── Built-in Slash Commands ───────────────────────────────────────
            if user_input.lower() in ("exit", "quit"):
                print(f"\n  {GREEN}Selamat tinggal! Terima kasih menggunakan Lyra CLI.{RESET}\n")
                break

            elif user_input.lower() == "/help":
                render_help()
                continue

            elif user_input.lower() == "/model":
                model_idx  = handle_model_command(config)
                model_info = MODELS[model_idx]
                reasoning_effort = config.get("reasoning_effort", "medium")
                continue

            elif user_input.lower() in ("/reasoning", "/effort"):
                reasoning_effort = handle_reasoning_command(config)
                continue

            elif user_input.lower() in ("/memory", "/mem"):
                handle_memory_command()
                continue

            elif user_input.lower() in ("/time", "/jam", "/tanggal"):
                handle_time_command()
                continue

            elif user_input.lower() in ("/reminder", "/remind", "/alarm"):
                handle_reminder_command()
                continue

            elif user_input.lower() in ("/update", "/check-update"):
                handle_update_command(interactive=True)
                continue

            elif user_input.lower() in ("/version", "/v"):
                print(f"  {BOLD}{COLOR_LYRA}Lyra CLI v{VERSION}{RESET} {DIM}(AstByte AI Terminal Agent){RESET}\n")
                continue

            elif user_input.lower() == "/project":
                handle_project_command(active_cwd)
                continue

            elif user_input.lower() == "/clear":
                messages = [{"role": "system", "content": get_current_system_prompt()}]
                print(f"  {GREEN}✓ Riwayat percakapan dibersihkan.{RESET}\n")
                continue

            elif user_input.lower() == "/history":
                chat_turns = [m for m in messages if m["role"] != "system"]
                if not chat_turns:
                    print(f"  {DIM}Belum ada riwayat percakapan.{RESET}\n")
                else:
                    print(f"\n  {BOLD}{COLOR_LYRA}Riwayat Chat ({len(chat_turns)} pesan):{RESET}")
                    for m in chat_turns[-10:]:
                        role_label = f"{COLOR_USER}Anda{RESET}" if m["role"] == "user" else f"{COLOR_LYRA}Lyra{RESET}"
                        snippet = m["content"][:80].replace("\n", " ")
                        print(f"  {role_label}: {DIM}{snippet}...{RESET}")
                    print()
                continue

            elif user_input.lower().startswith("/cd "):
                new_dir = user_input[4:].strip()
                expanded = os.path.expanduser(new_dir)
                if os.path.isdir(expanded):
                    active_cwd = os.path.abspath(expanded)
                    os.chdir(active_cwd)
                    print(f"  {GREEN}✓{RESET} Direktori aktif: {BOLD}{active_cwd}{RESET}\n")
                else:
                    print(f"  {RED}Direktori tidak ditemukan: {new_dir}{RESET}\n")
                continue

            elif user_input.lower().startswith("/ls"):
                parts = user_input.split(maxsplit=1)
                ls_path = parts[1] if len(parts) > 1 else active_cwd
                print(f"\n{list_directory(ls_path, recursive=True, depth=2)}\n")
                continue

            elif user_input.lower().startswith("/run "):
                cmd = user_input[5:].strip()
                result = execute_command(cmd, cwd=active_cwd)
                print(f"\n{result}\n")
                continue

            elif user_input.lower() == "/reset-key":
                reset_api_key(config)
                api_key = get_api_key(config=config, force_prompt=True)
                headers["Authorization"] = f"Bearer {api_key}"
                continue

            # ── Kirim ke AI ───────────────────────────────────────────────────
            # Selalu perbarui system prompt dengan waktu & memori paling aktual
            messages[0] = {"role": "system", "content": get_current_system_prompt()}
            messages.append({"role": "user", "content": user_input})
            print()

            while True:
                current_model  = MODELS[model_idx]["id"]
                current_effort = config.get("reasoning_effort", "medium")

                data = {
                    "model":            current_model,
                    "messages":         messages,
                    "temperature":      0.2,
                    "reasoning_effort": current_effort,
                }

                status_code, full_content = stream_ai_response(headers, data, model_info=MODELS[model_idx])

                if status_code == 401:
                    print(f"\n  {RED}[401] API Key tidak valid atau tidak memiliki akses.{RESET}")
                    if input("  Reset API Key? (y/n): ").strip().lower() == 'y':
                        reset_api_key(config)
                        api_key = get_api_key(config=config, force_prompt=True)
                        headers["Authorization"] = f"Bearer {api_key}"
                        continue
                    else:
                        if messages[-1]["role"] == "user":
                            messages.pop()
                        break

                elif status_code != 200:
                    print(f"\n  {RED}[{status_code}] Gagal mendapatkan jawaban.{RESET}")
                    print(f"  {RED}{full_content[:300]}{RESET}\n")
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break

                text_before, tool_call_json = extract_tool_call(full_content)
                messages.append({"role": "assistant", "content": full_content})

                if tool_call_json:
                    try:
                        tool_call = json.loads(tool_call_json)
                        func_name = tool_call.get("name", "")
                        args      = tool_call.get("arguments", {})
                    except Exception:
                        print(f"  {RED}Gagal mengurai tool call JSON.{RESET}\n")
                        break

                    print(f"  {DIM}● Menjalankan tool '{func_name}'...{RESET}")

                    if func_name == "list_directory":
                        result = list_directory(
                            args.get("path", "."),
                            args.get("recursive", False),
                            args.get("depth", 2),
                        )
                    elif func_name == "read_file":
                        result = read_file(args.get("filepath"))
                    elif func_name == "write_file":
                        result = write_file(args.get("filepath"), args.get("content", ""))
                    elif func_name == "create_directory":
                        result = create_directory(args.get("dirpath"))
                    elif func_name == "execute_command":
                        result = execute_command(
                            args.get("command"),
                            timeout=args.get("timeout", DEFAULT_TIMEOUT),
                            cwd=args.get("cwd", active_cwd),
                        )
                    elif func_name == "init_project":
                        result = init_project(
                            args.get("project_type", ""),
                            args.get("project_name", "project"),
                            args.get("target_dir", active_cwd),
                        )
                    elif func_name == "save_memory":
                        result = tool_save_memory(args.get("content", ""), mode=args.get("mode", "append"))
                    elif func_name == "read_memory":
                        result = tool_read_memory()
                    elif func_name == "clear_memory":
                        result = tool_clear_memory()
                    elif func_name == "get_system_time":
                        result = get_system_time()
                    elif func_name == "set_reminder":
                        result = tool_set_reminder(
                            args.get("message", ""),
                            time_input=args.get("time_input"),
                            delay_seconds=args.get("delay_seconds")
                        )
                    elif func_name == "list_reminders":
                        result = tool_list_reminders(status=args.get("status"))
                    elif func_name == "cancel_reminder":
                        result = tool_cancel_reminder(args.get("reminder_id", ""))
                    else:
                        result = f"Error: Tool '{func_name}' tidak dikenal."

                    messages.append({
                        "role":    "user",
                        "content": f"[Hasil Tool '{func_name}']\n{result}",
                    })
                    continue
                else:
                    break

        except KeyboardInterrupt:
            print(f"\n\n  {GREEN}Selamat tinggal! Terima kasih menggunakan Lyra CLI.{RESET}\n")
            break
        except Exception as e:
            print(f"\n  {RED}Kesalahan sistem: {e}{RESET}\n")

if __name__ == "__main__":
    main()