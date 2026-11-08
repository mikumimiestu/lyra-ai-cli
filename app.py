import sys
import os

# Pastikan direktori tempat file ini berada selalu ada di sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import requests
import json
import re
import subprocess
import threading
import time

# ─── Import custom modules ────────────────────────────────────────────────────

from styling import (
    RESET, BOLD, DIM, ITALIC, WHITE, GREEN, RED, YELLOW, CYAN,
    COLOR_USER, COLOR_LYRA, COLOR_BORDER, COLOR_DIM, COLOR_TITLE,
    COLOR_ACCENT, print_logo, rgb_to_ansi, hex_to_rgb,
    get_terminal_width, strip_ansi, str_width, format_markdown_line,
    render_header, render_footer_bar, render_markdown_table,
    render_full_divider, format_clean_thinking_line, parse_markdown_table
)
from spinner import Spinner, EscapeWatcher, LIVE, TurnCancelled, live_supported, run_live
from styling import (TerminalInput, COMMANDS, ActivityLog, StreamRenderer, prepare_user_message, ui_symbol,
                     fit_console_text, render_box, box_width, short_path, render_todo_lines, unicode_terminal,
                     USE_COLOR, workspace_branch, render_user_band, wrap_text_display_width, choose, NOT_INTERACTIVE,
                     clear_terminal)
from tools import (
    list_directory, read_file, write_file, execute_command,
    create_directory, init_project, DEFAULT_TIMEOUT,
    get_system_time, tool_save_memory, tool_read_memory, tool_clear_memory,
    tool_set_reminder, tool_list_reminders, tool_cancel_reminder, TodoList,
    APPROVAL, APPROVAL_LABELS, edit_file, search, UNDO, undo_last, describe_undo_stack
)
from config import (
    get_api_key, reset_api_key, save_config, load_config,
    login_with_account, logout, fetch_quota, uses_account_login,
    VERSION, check_remote_version, perform_update
)
from memory import (read_memory, save_memory, clear_memory, new_session_id, save_session, list_sessions,
                    load_session, delete_all_sessions, relative_time, history_enabled)
from reminder import (
    add_reminder, list_reminders, cancel_reminder,
    ensure_daemon_running, is_daemon_running, run_reminder_daemon_loop
)

# ─── Constants ────────────────────────────────────────────────────────────────
API_URL = "https://authx.astbyte.com/v1/chat/completions"

# ─── Model Definitions ────────────────────────────────────────────────────────
MODELS = [
    {
        "id":                 "lyra-luma-6-1",
        "name":               "Lyra Luma 6.1",
        "supports_reasoning": True,
    },
    {
        "id":                 "lyra-luma-4-mini",
        "name":               "Lyra Luma 4 mini",
        "supports_reasoning": False,
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
    {
        "id":                 "lyra-luma-flash",
        "name":               "Lyra Luma Flash",
        "supports_reasoning": False,
    },
]

DEFAULT_MODEL_INDEX = 2   # Lyra Orpheus 6

# Ids that older configs or sessions may still carry. They are rewritten on read and never sent to the API.
LEGACY_MODEL_IDS = {
    "lyra-luma-5.5":   "lyra-luma-6-1",
    "mimo-v2.5":       "lyra-luma-6-1",
    "lyra-luma-6.1":   "lyra-luma-6-1",   # alias accepted by the backend; keep one canonical spelling
    "lyra-nebula-4":   "lyra-luma-4-mini",
}

def canonical_model_id(model_id):
    """Map a legacy or alias model id to the current one; unknown ids are returned unchanged."""
    return LEGACY_MODEL_IDS.get(str(model_id).strip().lower(), model_id)

def migrate_model_config(config):
    """Redirect saved model ids to current ones. Returns True when the config changed."""
    changed = False
    for key in ("model", "model_id", "default_model"):
        value = config.get(key)
        if not isinstance(value, str):
            continue
        current = canonical_model_id(value)
        if current != value:
            config[key] = current
            changed = True
        for index, model in enumerate(MODELS):
            if model["id"] == current and config.get("model_index") != index and key != "default_model":
                config["model_index"] = index
                changed = True
    return changed

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
- write_file       : Membuat file baru atau menulis ulang seluruh isi file. Args: {{"filepath": "path", "content": "isi file"}}
- edit_file        : Mengubah SEBAGIAN file yang sudah ada dengan mengganti teks persis. Args: {{"filepath": "path", "old": "teks lama persis", "new": "teks baru", "replace_all": false}}
- search           : Cari teks (regex) di banyak file atau daftar file lewat glob. Args: {{"pattern": "regex", "path": ".", "glob": "*.py", "ignore_case": false, "max_results": 100}}
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
- update_todos     : Tampilkan/perbarui daftar tugas untuk pekerjaan multi-langkah. Kirim SELURUH daftar setiap kali. Args: {{"todos": [{{"content": "langkah", "status": "pending|in_progress|completed"}}]}}

Panduan fitur khusus:
1. Memori: Jika pengguna meminta "ingat ini...", "simpan ke memori...", atau memberikan fakta penting pengguna, gunakan tool `save_memory`.
2. Tanggal & Waktu: Selalu gunakan informasi waktu laptop terkini di atas saat menjawab pertanyaan terkait waktu.
3. Pengingat & Notifikasi: Jika pengguna minta ingatkan sesuatu ("ingatkan saya 10 menit lagi untuk...", "set alarm jam 8 pagi"), gunakan tool `set_reminder`.
4. Daftar tugas: Untuk pekerjaan dengan 3 langkah atau lebih, mulai dengan `update_todos`, jaga tepat satu item berstatus in_progress, dan perbarui daftar setiap satu langkah selesai. Jangan pakai untuk permintaan sederhana.
5. Mengubah file: untuk file yang sudah ada, baca dulu dengan `read_file`, lalu pakai `edit_file` dengan potongan `old` yang unik dan persis (termasuk spasi). Pakai `write_file` hanya untuk file baru atau penulisan ulang total. Pakai `search` untuk menemukan kode sebelum membaca banyak file.
6. Jangan sebutkan format XML/tool ini secara mentah kepada pengguna.
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

def pick_option(title, options, selected=0, subtitle=""):
    """Arrow-key menu; without a terminal it falls back to numbered input.

    Returns the 0-based index, or None when cancelled or the typed number is invalid.
    """
    picked = choose(title, options, selected, subtitle)
    if picked is not NOT_INTERACTIVE:
        return picked
    print(f"\n  {BOLD}{COLOR_LYRA}{ui_symbol('✦', '*')} {title}{RESET}\n")
    for number, (label, description) in enumerate(options, 1):
        print(f"  {number}. {BOLD}{label}{RESET}" + (f" {DIM}- {description}{RESET}" if description else ""))
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Pilihan (1-{len(options)}) ❯{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    return int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(options) else None

def handle_reasoning_command(config):
    """Pilih tingkat penalaran (cepat / sedang)."""
    current_effort = config.get("reasoning_effort", "medium")
    picked = pick_option(
        "Pilih Tingkat Penalaran",
        [(e["name"], e["desc"]) for e in REASONING_EFFORTS],
        selected=next((i for i, e in enumerate(REASONING_EFFORTS) if e["id"] == current_effort), 1),
        subtitle="Tersimpan sebagai default untuk sesi berikutnya.")
    if picked is None:
        print(f"  {DIM}Tingkat penalaran tidak diubah.{RESET}\n")
        return current_effort
    effort = REASONING_EFFORTS[picked]
    config["reasoning_effort"] = effort["id"]
    save_config(config)
    print(f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  Tingkat penalaran: {BOLD}{effort['name']}{RESET} {COLOR_DIM}(disimpan sebagai default){RESET}\n")
    return effort["id"]

def handle_model_command(config):
    """Interaktif model selector & reasoning selector."""
    current_idx = config.get("model_index", DEFAULT_MODEL_INDEX)
    if not isinstance(current_idx, int) or not 0 <= current_idx < len(MODELS):
        current_idx = DEFAULT_MODEL_INDEX
    options = [(m["name"], ("reasoning" if m["supports_reasoning"] else "tanpa reasoning")
                + ("   ✓ dipakai" if i == current_idx else "")) for i, m in enumerate(MODELS)]
    idx = choose("Pilih Model AI", options, current_idx, "Ganti model AI untuk sesi ini dan simpan di preferensi.")
    if idx is NOT_INTERACTIVE:
        render_model_selector(current_idx)
        try:
            choice = input(f"\n  {BOLD}{COLOR_USER}Nomor model ❯{RESET} ").strip()
            idx = int(choice) - 1 if choice else None
        except (ValueError, EOFError):
            print(f"  {RED}Input tidak valid.{RESET}\n")
            return current_idx
        if idx is not None and not 0 <= idx < len(MODELS):
            print(f"  {RED}Nomor tidak valid.{RESET}\n")
            return current_idx
    if idx is None:
        print(f"  {DIM}Model tidak diubah.{RESET}\n")
        return current_idx
    config["model_index"] = idx
    m = MODELS[idx]
    print(f"\n  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  Model: {BOLD}{COLOR_LYRA}{m['name']}{RESET} {COLOR_DIM}(disimpan sebagai default){RESET}")
    if m.get("supports_reasoning"):
        handle_reasoning_command(config)
    else:
        config["reasoning_effort"] = "low"
    save_config(config)
    print()
    return idx

def handle_update_command(interactive=True):
    """Interaktif cek & perbarui Lyra CLI ke versi terbaru dari GitHub."""
    print(f"\n  {BOLD}{COLOR_LYRA}✦ Cek Pembaruan Lyra CLI{RESET}")
    spinner = Spinner("Memeriksa versi terbaru di GitHub...")
    spinner.start()
    try:
        has_update, latest_version = check_remote_version(timeout=6.0)
    finally:
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
    try:
        success, msg = perform_update()
    finally:
        spin_up.stop()

    if success:
        print(f"  {GREEN}✓ {msg}{RESET}")
        print(f"  {BOLD}{COLOR_ACCENT}✦ Lyra CLI berhasil diperbarui ke v{latest_version}! Ketik /restart untuk memakai versi baru.{RESET}\n")
        return True
    print(f"  {RED}✖ Gagal memperbarui: {msg}{RESET}\n")
    return False

def restart_application():
    """Replace this process with a fresh one so an update takes effect without retyping `amagi`."""
    if LIVE.active:
        LIVE.shutdown()               # hand the terminal back before the process image is replaced
        for _ in range(50):
            if not LIVE.active:
                break
            time.sleep(0.05)
    sys.stdout.flush()
    try:
        if os.name == "nt":
            sys.exit(subprocess.call([sys.executable] + sys.argv))
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except OSError as error:
        print(f"  {RED}Gagal memulai ulang: {error}. Jalankan 'amagi' lagi secara manual.{RESET}\n")

def handle_memory_command():
    """Interaktif pengelola memori Amagi AI."""
    print(f"\n  {BOLD}{COLOR_LYRA}🧠 Memori Jangka Panjang Amagi AI (~/.amagi_memory.md){RESET}\n")
    current_mem = read_memory()
    print(f"  {DIM}--- Isi Memori Saat Ini ---{RESET}")
    print(current_mem.strip() if current_mem.strip() else f"  {DIM}(Memori masih kosong){RESET}")
    print(f"  {DIM}---------------------------{RESET}")
    picked = pick_option("Kelola memori", [("Tambah catatan baru", ""), ("Reset / bersihkan memori", ""), ("Kembali", "")])
    try:
        if picked == 0:
            note = input(f"  {BOLD}{COLOR_USER}Catatan/Fakta baru ❯{RESET} ").strip()
            if note:
                res = save_memory(note)
                print(f"  {GREEN}{res}{RESET}\n")
        elif picked == 1:
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
    picked = pick_option("Kelola pengingat", [("Buat pengingat baru", ""), ("Batalkan pengingat", ""),
                                              ("Pastikan daemon background aktif", ""), ("Kembali", "")])
    try:
        if picked == 0:
            msg = input(f"  {BOLD}{COLOR_USER}Pesan pengingat ❯{RESET} ").strip()
            waktu = input(f"  {BOLD}{COLOR_USER}Waktu (cth: '10m', '1h', '14:30', '30s') ❯{RESET} ").strip()
            if msg and waktu:
                res = tool_set_reminder(message=msg, time_input=waktu)
                print(f"\n  {res}\n")
        elif picked == 1:
            rem_id = input(f"  {BOLD}{COLOR_USER}ID Pengingat yang ingin dibatalkan (cth: rem_123) ❯{RESET} ").strip()
            if rem_id:
                res = tool_cancel_reminder(rem_id)
                print(f"  {res}\n")
        elif picked == 2:
            ensure_daemon_running()
            print(f"  {GREEN}✓ Daemon pengingat latar belakang telah diaktifkan!{RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()

def render_help():
    print(f"\n  {COLOR_LYRA}✦{RESET} {BOLD}Perintah Lyra{RESET}\n")
    width = max(10, get_terminal_width() - 24)
    from styling import wrap_text_display_width
    for command, description in COMMANDS + [('exit / quit', 'Keluar dari Lyra')]:
        lines = wrap_text_display_width(description, width)
        print(f"  {COLOR_LYRA}{command:<16}{RESET}  {COLOR_DIM}{lines[0]}{RESET}")
        for line in lines[1:]:
            print(f"                    {COLOR_DIM}{line}{RESET}")
    print(f"\n  {COLOR_DIM}Enter kirim · Alt+Enter / Ctrl+J baris baru{RESET}")
    print(f"  {COLOR_DIM}Tab / panah pilih perintah · Ctrl+C batalkan input · Ctrl+D keluar{RESET}\n")


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    return f"{hours} jam {minutes} menit" if hours else f"{minutes} menit"

def quota_error_message(body):
    """Friendly text for a 429 from the quota check; falls back to the raw body."""
    try:
        error = json.loads(body)["error"]
        text = error.get("message") or body
        reset = error.get("resets_in_seconds")
        return text + (f" Reset dalam {format_duration(reset)}." if reset is not None else "")
    except (ValueError, KeyError, TypeError, AttributeError):
        return body[:300]

BILLING_STATE = {"balance": False, "notified": False}

def note_balance_billing():
    """Tell the user once per session that the daily quota is gone and the developer balance is being used."""
    if BILLING_STATE["balance"] and not BILLING_STATE["notified"]:
        BILLING_STATE["notified"] = True
        print(f"\n  {YELLOW}Kuota harian habis, sekarang memakai saldo developer.{RESET}")

def show_quota(config):
    if not uses_account_login(config):
        print(f"\n  {DIM}Kuota token hanya berlaku untuk login akun AstByte. Pakai /login untuk masuk.{RESET}\n")
        return
    quota = fetch_quota(config)
    if not quota:
        print(f"\n  {RED}Gagal mengambil kuota. Coba lagi sebentar.{RESET}\n")
        return
    percent = min(100, round(quota["used"] * 100 / quota["limit"])) if quota["limit"] else 100
    print(f"\n  {BOLD}Kuota token hari ini{RESET} {DIM}(tier {quota['tier'].upper()}){RESET}")
    print(f"  Terpakai {quota['used']:,} dari {quota['limit']:,} token ({percent}%)")
    print(f"  Sisa     {BOLD}{quota['remaining']:,}{RESET} token {DIM}· reset dalam {format_duration(quota['resets_in_seconds'])}{RESET}")
    fallback = quota.get("fallback") or {}
    if fallback.get("enabled") and fallback.get("has_key"):
        print(f"  Cadangan {DIM}saldo developer aktif, dipakai setelah kuota habis{RESET}\n")
    else:
        print(f"  Cadangan {DIM}mati. Aktifkan di web: Pengaturan → Amagi CLI{RESET}\n")


# ─── Stream Response Handler ─────────────────────────────────────────────────
class VisibleResponseFilter:
    """Hide reasoning and tool XML, including tags split across SSE chunks."""
    def __init__(self):
        self.pending = ''
        self.thinking = False
        self.tool_call = False
        self.saw_reasoning = False
        self.tool_chunks = []

    @staticmethod
    def _tail_length(text, tags):
        return max((size for tag in tags for size in range(1, len(tag))
                    if text.endswith(tag[:size])), default=0)

    def feed(self, text, final=False):
        if self.tool_call:
            self.tool_chunks.append(text)
            return ''
        self.pending += text
        visible = []
        while self.pending:
            if self.thinking:
                end = self.pending.find('</think>')
                if end < 0:
                    keep = self._tail_length(self.pending, ['</think>'])
                    self.pending = self.pending[-keep:] if keep else ''
                    break
                self.pending = self.pending[end + len('</think>'):]
                self.thinking = False
                continue
            tags = ['<think>', '<tool_call>']
            found = [(self.pending.find(tag), tag) for tag in tags if tag in self.pending]
            if found:
                position, tag = min(found)
                visible.append(self.pending[:position])
                self.pending = self.pending[position + len(tag):]
                if tag == '<think>':
                    self.thinking = True
                    self.saw_reasoning = True
                else:
                    self.tool_call = True
                    self.tool_chunks.append(tag + self.pending)
                    self.pending = ''
                    break
            else:
                keep = self._tail_length(self.pending, tags)
                visible.append(self.pending[:-keep] if keep else self.pending)
                self.pending = self.pending[-keep:] if keep else ''
                break
        # An unfinished protocol tag must not leak into the transcript.
        if final:
            self.pending = ''
        return ''.join(visible)


def stream_ai_response(headers, data, model_info=None):
    spinner = Spinner('Menunggu respons...', tip=True)
    response = None
    chunks = []
    parser = VisibleResponseFilter()
    visible_started = False

    def emit(text):
        """Write answer text as it arrives; the spinner leaves the screen before the first character."""
        nonlocal visible_started
        if not text:
            return
        if not visible_started:
            if not text.strip():
                return
            visible_started = True
            if LIVE.active:
                spinner.set_message('Menulis jawaban...')   # the status line stays up while text streams
                LIVE.write_stream('\n')
            else:
                spinner.stop()
                sys.stdout.write('\n')
        if LIVE.active:
            LIVE.write_stream(text)
            return
        sys.stdout.write(text)
        sys.stdout.flush()

    # Lambdas resolve the formatters at call time so they stay patchable.
    renderer = StreamRenderer(emit, lambda line, state: format_markdown_line(line, state),
                              lambda lines: render_markdown_table(lines))

    try:
        spinner.start()
        with EscapeWatcher():
            response = requests.post(API_URL, headers=headers, json={**data, 'stream': True},
                                     stream=True, timeout=DEFAULT_TIMEOUT)
            LIVE.response = response
            LIVE.check_cancel()
            BILLING_STATE["balance"] = response.headers.get('X-Amagi-Billing') == 'balance'
            if response.status_code != 200:
                return response.status_code, response.text
            for raw_line in response.iter_lines():
                LIVE.check_cancel()
                if not raw_line:
                    continue
                line = raw_line.decode('utf-8')
                if not line.startswith('data: '):
                    continue
                payload = line[6:].strip()
                if payload == '[DONE]':
                    break
                try:
                    delta = json.loads(payload)['choices'][0]['delta']
                    content = delta.get('content') or ''
                    reasoning = delta.get('reasoning_content') or delta.get('reasoning')
                except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                    continue
                if not visible_started or LIVE.active:
                    spinner.add_tokens(len(reasoning or '') + (len(content) if isinstance(content, str) else 0))
                if reasoning and not visible_started:
                    spinner.set_message('Memproses permintaan...')
                if not isinstance(content, str) or not content:
                    continue
                visible = parser.feed(content)
                chunks.append(visible)
                if parser.saw_reasoning and not visible_started:
                    spinner.set_message('Memproses permintaan...')
                if parser.tool_call and not visible_started:
                    spinner.set_message('Menyiapkan aksi...')
                renderer.feed(visible)
            renderer.feed(parser.feed('', final=True))
        renderer.finish()
        if not visible_started and not parser.tool_call:
            return 0, 'Layanan selesai tanpa jawaban. Coba kirim ulang permintaan.'
        return 200, ''.join(chunks) + ''.join(parser.tool_chunks)
    except Exception as error:
        # Clear progress before any error text or pending answer is printed.
        spinner.stop()
        renderer.abort()
        if LIVE.cancel_requested():      # Esc closed the connection under us
            LIVE.check_cancel()
        return 0, f'Error streaming: {error}'
    except BaseException:
        spinner.stop()
        renderer.abort()
        raise
    finally:
        spinner.stop()
        LIVE.response = None
        if LIVE.active:
            LIVE.flush_stream()
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

# ─── Context estimate ─────────────────────────────────────────────────────────
DEFAULT_CONTEXT_TOKENS = 128000   # assumed window; override with LYRA_CONTEXT_TOKENS

def context_limit():
    try:
        value = int(os.environ.get("LYRA_CONTEXT_TOKENS", ""))
        return value if value > 0 else DEFAULT_CONTEXT_TOKENS
    except ValueError:
        return DEFAULT_CONTEXT_TOKENS

def estimate_context_tokens(messages):
    """Rough size of the conversation: about four characters per token."""
    return sum(len(str(m.get("content", ""))) for m in messages) // 4

def context_percent(messages):
    return min(999, round(estimate_context_tokens(messages) * 100 / context_limit()))

# ─── Slash Command Handlers ───────────────────────────────────────────────────
def handle_status_command(config, model_idx, cwd, messages, todo_list):
    """Session summary in a rounded card; never prints the API key."""
    model = MODELS[model_idx]
    effort = config.get("reasoning_effort", "medium") if model["supports_reasoning"] else "tanpa reasoning"
    if os.getenv("ASTBYTE_API_KEY", "").strip():
        key_source = "dari ASTBYTE_API_KEY"
    elif uses_account_login(config):
        key_source = f"login akun {config.get('cli_user') or 'AstByte'}"
    else:
        key_source = "tersimpan di config" if config.get("api_key") else "belum diatur"
    turns = len([m for m in messages if m["role"] != "system"])
    tokens = estimate_context_tokens(messages)
    done = sum(1 for item in todo_list.items if item["status"] == "completed")
    rows = [
        ("Versi", f"v{VERSION}"),
        ("Model", f"{model['name']} ({model['id']})"),
        ("Reasoning", effort),
        ("Direktori", short_path(cwd)),
        ("Branch", workspace_branch(cwd) or "-"),
        ("Akses", key_source),
        ("Endpoint", API_URL.split("/")[2]),
        ("Percakapan", f"{turns} pesan, ~{tokens:,} token ({context_percent(messages)}% dari {context_limit():,})"),
        ("Tugas", f"{done}/{len(todo_list.items)} selesai" if todo_list.items else "-"),
        ("Persetujuan", APPROVAL_LABELS[APPROVAL.mode]),
        ("Urungkan", f"{len(UNDO.items)} perubahan bisa diurungkan" if UNDO.items else "-"),
        ("Riwayat", "tersimpan di ~/.amagi_sessions" if history_enabled() else "dimatikan (LYRA_NO_HISTORY)"),
        ("Memori", f"{len(read_memory().strip())} karakter"),
        ("Pengingat", "daemon aktif" if is_daemon_running() else "daemon mati"),
        ("Terminal", f"{get_terminal_width()} kolom, {'unicode' if unicode_terminal() else 'ASCII'}, {'warna' if USE_COLOR else 'tanpa warna'}"),
    ]
    width = box_width(78)
    room = width - 4
    key_w = max(len(label) for label, _ in rows) + 2
    body = [f"{COLOR_DIM}{label:<{key_w}}{RESET}{fit_console_text(value, max(8, room - key_w))}" for label, value in rows]
    print()
    for line in render_box(body, width, title=f"{BOLD}{COLOR_LYRA}{ui_symbol('✦', '*')} Status{RESET}"):
        print("  " + line)
    print()

MODE_ALIASES = {"ask": "ask", "tanya": "ask", "edit": "edits", "edits": "edits", "all": "all", "semua": "all"}

def render_auto_all_warning():
    width = box_width(78)
    lines = []
    for text in (
        "Lyra menulis file dan menjalankan perintah terminal tanpa bertanya.",
        "Perintah berbahaya (rm -rf, sudo, git push --force, curl | sh, dan sejenisnya) tetap meminta izin.",
        "Kembali ke aman kapan saja dengan Shift+Tab atau /mode ask.",
    ):
        lines.extend(wrap_text_display_width(text, width - 4))
    print()
    for line in render_box(lines, width, color=RED, title=f"{BOLD}{RED}{ui_symbol('⚠', '!')} Mode AUTO SEMUA aktif{RESET}"):
        print("  " + line)
    print()

def handle_mode_command(user_input):
    """/mode [ask|edit|all]: choose how much Lyra may do without asking. Never saved between sessions."""
    parts = user_input.split()
    note = f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  "
    if len(parts) == 1:
        print(f"\n{note}Mode persetujuan: {BOLD}{APPROVAL_LABELS[APPROVAL.mode]}{RESET}")
        print(f"     {COLOR_DIM}/mode ask · /mode edit (auto-setuju edit file) · /mode all (tanpa tanya) · Shift+Tab berganti{RESET}\n")
        return
    mode = MODE_ALIASES.get(parts[1].lower())
    if mode is None:
        print(f"  {RED}Mode tidak dikenal: {parts[1]}. Pilih ask, edit, atau all.{RESET}\n")
        return
    if mode == "all":
        try:
            answer = input(f"\n  {BOLD}{RED}Mode AUTO SEMUA menjalankan perintah dan menulis file tanpa bertanya. Aktifkan? (y/n) ❯{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer not in ("y", "ya", "yes"):
            print(f"{note}Mode tidak diubah.\n")
            return
    APPROVAL.set(mode)
    print(f"\n{note}Mode persetujuan: {BOLD}{APPROVAL_LABELS[mode]}{RESET} {COLOR_DIM}(hanya untuk sesi ini){RESET}")
    if mode == "all":
        render_auto_all_warning()
    else:
        print()

def handle_todos_command(todo_list):
    print()
    if not todo_list.items:
        print(f"  {COLOR_DIM}Belum ada daftar tugas. Lyra membuatnya sendiri untuk pekerjaan multi-langkah.{RESET}\n")
        return
    print(f"{COLOR_LYRA}{ui_symbol('●', '*')}{RESET} {BOLD}Daftar tugas{RESET}")
    for line in render_todo_lines(todo_list.items, indent="  "):
        print(line)
    print()

# ─── Compaction ───────────────────────────────────────────────────────────────
def collect_completion(headers, data):
    """Run a streaming request silently and return (status, visible text). Honours Esc in the live console."""
    response = None
    parser = VisibleResponseFilter()
    chunks = []
    try:
        response = requests.post(API_URL, headers=headers, json={**data, "stream": True}, stream=True,
                                 timeout=DEFAULT_TIMEOUT)
        LIVE.response = response
        if response.status_code != 200:
            return response.status_code, response.text
        for raw_line in response.iter_lines():
            LIVE.check_cancel()
            line = raw_line.decode("utf-8") if raw_line else ""
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            try:
                content = json.loads(payload)["choices"][0]["delta"].get("content") or ""
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                continue
            if isinstance(content, str) and content:
                chunks.append(parser.feed(content))
        chunks.append(parser.feed("", final=True))
        return 200, "".join(chunks).strip()
    except Exception as error:
        if LIVE.cancel_requested():
            LIVE.check_cancel()
        return 0, f"Error: {error}"
    finally:
        LIVE.response = None
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

SUMMARY_PROMPT = (
    "Kamu bertugas meringkas percakapan antara pengguna dan asisten coding supaya percakapan bisa dilanjutkan "
    "dengan konteks yang jauh lebih kecil. Tulis ringkasan padat dalam bahasa yang sama dengan percakapan, "
    "maksimal sekitar 400 kata, dengan bagian: Tujuan pengguna, Yang sudah dikerjakan (file yang dibuat atau "
    "diubah, perintah penting, hasilnya), Keputusan dan preferensi, Tugas yang tersisa, Fakta penting "
    "(path, nama, angka). Jangan menjawab pertanyaan di dalam percakapan dan jangan memanggil tool."
)

def _is_real_user_message(message):
    content = str(message.get("content", ""))
    return message.get("role") == "user" and not content.startswith("[Hasil Tool") and not content.startswith("[Ringkasan")

def compact_messages(messages, headers, model_id, effort, focus=""):
    """Replace everything before the latest user request with a summary.

    Returns (new_messages, error). The latest request and anything after it stay word for word.
    """
    system = messages[0] if messages and messages[0].get("role") == "system" else None
    body = messages[1:] if system else list(messages)
    split = max((i for i, m in enumerate(body) if _is_real_user_message(m)), default=0)
    older, tail = body[:split], body[split:]
    if len(older) < 3:
        return None, "Percakapan masih pendek, belum perlu diringkas."
    pieces = []
    for message in older:
        text = str(message.get("content", ""))
        limit = 1500 if text.startswith("[Hasil Tool") else 4000
        pieces.append(f"{message['role'].upper()}: {text[:limit]}" + (" …[dipotong]" if len(text) > limit else ""))
    transcript = "\n\n".join(pieces)
    if len(transcript) > 90000:
        transcript = "…[bagian awal dipotong]\n\n" + transcript[-90000:]
    request = "TRANSKRIP PERCAKAPAN:\n\n" + transcript + "\n\nTulis ringkasannya sekarang." + (f"\nFokus khusus: {focus}" if focus else "")
    status, text = collect_completion(headers, {
        "model": canonical_model_id(model_id),
        "messages": [{"role": "system", "content": SUMMARY_PROMPT}, {"role": "user", "content": request}],
        "temperature": 0.2, "reasoning_effort": effort,
    })
    if status != 200:
        return None, f"Gagal meringkas ({status}): {str(text)[:200]}"
    if not text.strip():
        return None, "Layanan tidak mengembalikan ringkasan. Percakapan tidak diubah."
    summary = [
        {"role": "user", "content": "[Ringkasan percakapan sebelumnya — gunakan sebagai konteks, jangan dibalas]\n" + text.strip()},
        {"role": "assistant", "content": "Baik, saya lanjutkan berdasarkan ringkasan tersebut."},
    ]
    return ([system] if system else []) + summary + tail, None

def handle_compact_command(messages, headers, model_id, effort, focus=""):
    """Returns the new message list (or the old one when nothing changed)."""
    before = estimate_context_tokens(messages)
    spinner = Spinner("Meringkas percakapan...")
    spinner.start()
    try:
        new_messages, error = compact_messages(messages, headers, model_id, effort, focus)
    finally:
        spinner.stop()
    note = f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  "
    if error:
        print(f"\n{note}{YELLOW}{error}{RESET}\n")
        return messages
    after = estimate_context_tokens(new_messages)
    print(f"\n{note}Percakapan diringkas: ~{before:,} → ~{after:,} token {COLOR_DIM}({len(messages) - len(new_messages) + 2} pesan lama jadi ringkasan){RESET}\n")
    return new_messages

# ─── Undo, saved sessions ─────────────────────────────────────────────────────
def handle_undo_command(user_input):
    parts = user_input.split()
    if len(parts) > 1 and parts[1].lower() in ("list", "daftar"):
        lines = describe_undo_stack()
        print()
        if not lines:
            print(f"  {COLOR_DIM}Belum ada perubahan yang bisa diurungkan.{RESET}\n")
            return
        print(f"{COLOR_LYRA}{ui_symbol('●', '*')}{RESET} {BOLD}Bisa diurungkan{RESET} {COLOR_DIM}(paling baru dulu; /undo mengurungkan nomor 1){RESET}")
        for line in lines:
            print(f"  {line}")
        print()
        return
    print()
    result = undo_last()
    print(f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  {result}\n")

def handle_resume_command(user_input, active_cwd):
    """Pick a saved conversation. Returns the session dict to continue, or None."""
    parts = user_input.split()
    if len(parts) > 1 and parts[1].lower() in ("hapus", "clear", "delete"):
        try:
            answer = input(f"\n  {RED}Hapus SEMUA percakapan tersimpan di ~/.amagi_sessions? (y/n) ❯{RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        print(f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  " + (f"{delete_all_sessions()} sesi dihapus." if answer == "y" else "Tidak ada yang dihapus.") + "\n")
        return None
    if not history_enabled():
        print(f"\n  {YELLOW}Riwayat dimatikan (LYRA_NO_HISTORY).{RESET}\n")
        return None
    sessions = list_sessions()
    if not sessions:
        print(f"\n  {COLOR_DIM}Belum ada percakapan tersimpan.{RESET}\n")
        return None
    options = [(item["title"], f"{relative_time(item['updated'])} · {item['count']} pesan · {short_path(item['cwd'])}" if item["cwd"] else
                f"{relative_time(item['updated'])} · {item['count']} pesan") for item in sessions]
    picked = pick_option("Lanjutkan percakapan", options, 0, "Percakapan tersimpan di ~/.amagi_sessions. /resume hapus menghapus semuanya.")
    if picked is None:
        print(f"  {DIM}Dibatalkan.{RESET}\n")
        return None
    data = load_session(sessions[picked]["id"])
    if data is None:
        print(f"  {RED}Sesi tidak bisa dibaca.{RESET}\n")
        return None
    other = data.get("cwd") and os.path.abspath(data["cwd"]) != os.path.abspath(active_cwd)
    print(f"\n  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  Dilanjutkan: {BOLD}{data['title']}{RESET} {COLOR_DIM}({len(data['messages'])} pesan)"
          + (f"; dibuat di {short_path(data['cwd'])}, folder aktif tidak berubah" if other else "") + f"{RESET}\n")
    return data

PROJECT_TYPES = [
    ("react", "React"), ("next", "Next.js"), ("vue", "Vue"), ("laravel", "Laravel (PHP)"), ("php", "PHP polos"),
    ("express", "Express (Node.js)"), ("django", "Django (Python)"), ("fastapi", "FastAPI (Python)"),
    ("flutter", "Flutter"), ("node", "Node.js polos"),
]

def handle_project_command(cwd):
    """Wizard pembuatan project baru."""
    print(f"\n  {BOLD}{COLOR_LYRA}✦ Buat Project Baru{RESET}")
    try:
        picked = choose("Pilih tipe project", PROJECT_TYPES, 0, "Nama dan folder tujuan ditanyakan setelah ini.")
        if picked is NOT_INTERACTIVE:
            print(f"\n  {DIM}Tipe yang didukung: {', '.join(name for name, _ in PROJECT_TYPES)}{RESET}\n")
            ptype = input(f"  {BOLD}{COLOR_USER}Tipe project ❯{RESET} ").strip().lower()
        elif picked is None:
            print(f"  {DIM}Dibatalkan.{RESET}\n")
            return
        else:
            ptype = PROJECT_TYPES[picked][0]
            print(f"\n  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  Tipe: {BOLD}{PROJECT_TYPES[picked][1]}{RESET}\n")
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

    if live_supported():
        # The composer stays at the bottom while Lyra works; the agent loop runs in a worker thread.
        run_live(_run_session)
    else:
        _run_session(None)

def end_session(live, message):
    """Leave with a clean screen: wipe the conversation, then say goodbye in one line."""
    if live is not None:
        live.exit_message = message          # printed by run_live once the live UI has released the terminal
        return
    clear_terminal()
    print(message)

def _run_session(live=None):
    config  = load_config()
    if migrate_model_config(config):
        save_config(config)
    api_key = get_api_key(config=config)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    model_idx = config.get("model_index", DEFAULT_MODEL_INDEX)
    if not isinstance(model_idx, int) or not 0 <= model_idx < len(MODELS):
        model_idx = DEFAULT_MODEL_INDEX
        config["model_index"] = model_idx
        save_config(config)

    reasoning_effort = config.get("reasoning_effort", "medium")

    # Inisialisasi system prompt dengan waktu dan memori terbaru
    messages = [{"role": "system", "content": get_current_system_prompt()}]
    active_cwd = os.getcwd()
    todo_list = TodoList()
    context_warned = False
    warned_all = False
    session_id = new_session_id()
    session_started = time.time()
    if any(arg in ("--continue", "-c") for arg in sys.argv[1:]):
        latest = list_sessions(1)
        loaded = load_session(latest[0]["id"]) if latest else None
        if loaded:
            messages += loaded["messages"]
            session_id, session_started = loaded["id"], loaded.get("started", session_started)
            print(f"\n  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  Melanjutkan: {BOLD}{loaded['title']}{RESET} {COLOR_DIM}({len(loaded['messages'])} pesan){RESET}")

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

    # Compact Lyra welcome
    print_logo()
    render_header(MODELS[model_idx]["name"], reasoning_effort, active_cwd, MODELS[model_idx]["supports_reasoning"])
    editor = TerminalInput(lambda: {
        "model": MODELS[model_idx]["name"],
        "effort": config.get("reasoning_effort", "medium"),
        "directory": active_cwd,
        "supports_reasoning": MODELS[model_idx]["supports_reasoning"],
        "context_pct": context_percent(messages),
        "approval": APPROVAL.mode,
    }, on_cycle_mode=APPROVAL.cycle, **({"live": live} if live is not None else {}))
    if live is not None:
        live.editor = editor
        live.ready.set()

    activity = ActivityLog()

    # ── Loop utama ────────────────────────────────────────────────────────────
    while True:
        try:
            model_info = MODELS[model_idx]
            current_effort = config.get("reasoning_effort", "medium")

            if update_state["has_update"] and not update_state["notified"]:
                update_state["notified"] = True
                editor.notice = f"{ui_symbol('⚡', '!')} v{update_state['latest_version']} tersedia {ui_symbol('·', '/')} /update"

            try:
                user_input = editor.read().strip()
            except KeyboardInterrupt:
                print(f"\n  {COLOR_DIM}Input dibatalkan.{RESET}\n")
                continue
            except EOFError:
                end_session(live, f"\n  {COLOR_DIM}Sampai nanti.{RESET}\n")
                break

            if not user_input:
                continue
            if getattr(editor, "session", None) is not None:
                render_user_band(user_input)
            if APPROVAL.mode == "all" and not warned_all:
                warned_all = True
                render_auto_all_warning()
            elif APPROVAL.mode != "all":
                warned_all = False

            # ── Built-in Slash Commands ───────────────────────────────────────
            if user_input.lower() in ("exit", "quit"):
                end_session(live, f"\n  {GREEN}Selamat tinggal! Terima kasih menggunakan Lyra CLI.{RESET}\n")
                break

            elif user_input.lower() in ("/", "/help"):
                render_help()
                continue

            elif user_input.lower().split()[0] == "/mode":
                handle_mode_command(user_input)
                warned_all = APPROVAL.mode == "all"
                continue

            elif user_input.lower().split()[0] == "/undo":
                handle_undo_command(user_input)
                continue

            elif user_input.lower().split()[0] == "/compact":
                messages = handle_compact_command(messages, headers, MODELS[model_idx]["id"],
                                                  config.get("reasoning_effort", "medium"), user_input[len("/compact"):].strip())
                save_session(session_id, messages, active_cwd, session_started)
                context_warned = False
                continue

            elif user_input.lower().split()[0] == "/resume":
                resumed = handle_resume_command(user_input, active_cwd)
                if resumed:
                    messages = [{"role": "system", "content": get_current_system_prompt()}] + resumed["messages"]
                    session_id, session_started = resumed["id"], resumed.get("started", time.time())
                    todo_list.clear()
                    context_warned = False
                continue

            elif user_input.lower() == "/status":
                handle_status_command(config, model_idx, active_cwd, messages, todo_list)
                continue

            elif user_input.lower() in ("/todos", "/todo"):
                handle_todos_command(todo_list)
                continue

            elif user_input.lower() == '/details':
                activity.show_details()
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
                if handle_update_command(interactive=True):
                    editor.notice = f"{ui_symbol('✔', 'OK')} Update terpasang {ui_symbol('·', '/')} /restart"
                continue

            elif user_input.lower() == "/restart":
                restart_application()
                continue

            elif user_input.lower() in ("/version", "/v"):
                print(f"  {BOLD}{COLOR_LYRA}Lyra CLI v{VERSION}{RESET} {DIM}(AstByte AI Terminal Agent){RESET}\n")
                continue

            elif user_input.lower() == "/project":
                handle_project_command(active_cwd)
                continue

            elif user_input.lower() == "/clear":
                messages = [{"role": "system", "content": get_current_system_prompt()}]
                todo_list.clear()
                context_warned = False
                session_id, session_started = new_session_id(), time.time()
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

            elif user_input.lower() == "/login":
                token = login_with_account(config)
                if token:
                    api_key = token
                    headers["Authorization"] = f"Bearer {api_key}"
                continue

            elif user_input.lower() == "/logout":
                logout(config)
                print(f"  {DIM}Gunakan /login atau /reset-key untuk masuk lagi.{RESET}\n")
                continue

            elif user_input.lower() in ("/kuota", "/quota"):
                show_quota(config)
                continue

            elif user_input.lower() == "/reset-key":
                reset_api_key(config)
                api_key = get_api_key(config=config, force_prompt=True)
                headers["Authorization"] = f"Bearer {api_key}"
                continue

            try:
                message_content = prepare_user_message(user_input, active_cwd)
            except ValueError as error:
                print(f"\n  {YELLOW}{error}{RESET}\n")
                continue
            activity.begin_turn()

            # ── Kirim ke AI ───────────────────────────────────────────────────
            # Selalu perbarui system prompt dengan waktu & memori paling aktual
            messages[0] = {"role": "system", "content": get_current_system_prompt()}
            messages.append({"role": "user", "content": message_content})
            if not context_warned and context_percent(messages) >= 90:
                context_warned = True
                print(f"\n  {YELLOW}{ui_symbol('⚠', '!')} Konteks hampir penuh (~{context_percent(messages)}%). Ketik /compact untuk meringkas, atau /clear untuk mulai baru.{RESET}")

            while True:
                current_model  = canonical_model_id(MODELS[model_idx]["id"])
                current_effort = config.get("reasoning_effort", "medium")

                data = {
                    "model":            current_model,
                    "messages":         messages,
                    "temperature":      0.2,
                    "reasoning_effort": current_effort,
                }

                status_code, full_content = stream_ai_response(headers, data, model_info=MODELS[model_idx])
                if status_code == 200:
                    note_balance_billing()

                if status_code == 401 and uses_account_login(config):
                    print(f"\n  {RED}[401] Login akun berakhir atau akses perangkat ini dicabut.{RESET}")
                    if input("  Login ulang? (y/n): ").strip().lower() == 'y':
                        api_key = login_with_account(config)
                        if api_key:
                            headers["Authorization"] = f"Bearer {api_key}"
                            continue
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break

                elif status_code == 429 and uses_account_login(config):
                    print(f"\n  {YELLOW}{quota_error_message(full_content)}{RESET}\n")
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break

                elif status_code == 401:
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
                if text_before.strip():
                    activity.close_group()
                messages.append({"role": "assistant", "content": full_content})

                if tool_call_json:
                    try:
                        tool_call = json.loads(tool_call_json)
                        func_name = tool_call.get("name", "")
                        args      = tool_call.get("arguments", {})
                    except Exception:
                        print(f"  {RED}Gagal mengurai tool call JSON.{RESET}\n")
                        break

                    LIVE.check_cancel()
                    activity.start(func_name, args)

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
                    elif func_name == "edit_file":
                        result = edit_file(args.get("filepath"), args.get("old", ""), args.get("new", ""),
                                           bool(args.get("replace_all", False)))
                    elif func_name == "search":
                        result = search(args.get("pattern", ""), args.get("path", "."), args.get("glob"),
                                        bool(args.get("ignore_case", False)), args.get("max_results", 100))
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
                    elif func_name == "update_todos":
                        result = todo_list.update(args.get("todos"))
                    else:
                        result = f"Error: Tool '{func_name}' tidak dikenal."

                    activity.finish(func_name, args, result)
                    messages.append({
                        "role":    "user",
                        "content": f"[Hasil Tool '{func_name}']\n{result}",
                    })
                    continue
                else:
                    activity.complete_turn()
                    save_session(session_id, messages, active_cwd, session_started)
                    break

        except KeyboardInterrupt:
            print(f"\n  {COLOR_DIM}Proses dibatalkan. Kamu bisa lanjut mengetik.{RESET}\n")
            continue
        except EOFError:
            end_session(live, f"\n  {COLOR_DIM}Sampai nanti.{RESET}\n")
            break
        except Exception as e:
            print(f"\n  {RED}Kesalahan sistem: {e}{RESET}\n")

if __name__ == "__main__":
    main()