import requests
import json
import sys
import os
import re
import time

# ─── Import custom modules ────────────────────────────────────────────────────
from styling import (
    RESET, BOLD, DIM, ITALIC, WHITE, GREEN, RED, YELLOW, CYAN,
    COLOR_USER, COLOR_LYRA, COLOR_BORDER, COLOR_DIM, COLOR_TITLE,
    COLOR_ACCENT, print_logo, rgb_to_ansi, hex_to_rgb,
)
from spinner import Spinner
from tools import (
    list_directory, read_file, write_file, execute_command,
    create_directory, init_project, DEFAULT_TIMEOUT
)
from config import get_api_key, reset_api_key, save_config, load_config

# ─── Constants ────────────────────────────────────────────────────────────────
API_URL = "https://authx.astbyte.com/v1/chat/completions"

# ─── Model Definitions ────────────────────────────────────────────────────────
MODELS = [
    {
        "id":   "lyra-luma-flash",
        "name": "Lyra Luma Flash",
        "desc": "Tercepat untuk tugas sehari-hari",
        "tag":  "⚡ Fast",
    },
    {
        "id":   "lyra-luma-4",
        "name": "Lyra Luma 4",
        "desc": "Seimbang antara kecepatan & kualitas",
        "tag":  "⚖ Balanced",
    },
    {
        "id":   "lyra-nebula-4",
        "name": "Lyra Nebula 4",
        "desc": "Paling mampu untuk pekerjaan kompleks",
        "tag":  "🌌 Powerful",
    },
    {
        "id":   "nexara-4.5",
        "name": "Nexara 4.5",
        "desc": "Model generasi berikutnya dari Nexara",
        "tag":  "🚀 Next-Gen",
    },
]

DEFAULT_MODEL_INDEX = 0   # lyra-luma-flash

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah Lyra, asisten AI canggih dari AstByte yang berjalan di terminal.
Kamu memiliki akses ke tools komputer lokal pengguna.

Untuk memanggil tool, sertakan blok XML ini TEPAT di akhir jawabanmu:
<tool_call>
{
  "name": "nama_tool",
  "arguments": {
    "key": "value"
  }
}
</tool_call>

Daftar tool yang tersedia:
- list_directory   : Mendaftar file/folder. Args: {"path": ".", "recursive": false, "depth": 2}
- read_file        : Membaca teks file.     Args: {"filepath": "path/ke/file"}
- write_file       : Menulis/edit file.     Args: {"filepath": "path", "content": "isi file"}
- create_directory : Membuat folder baru.   Args: {"dirpath": "path/ke/folder"}
- execute_command  : Jalankan terminal.     Args: {"command": "perintah", "cwd": "/optional/path", "timeout": 300}
- init_project     : Scaffolding project baru. Args: {"project_type": "react|next|vue|laravel|php|...", "project_name": "nama", "target_dir": "/optional"}

Panduan penggunaan tool:
1. Gunakan execute_command untuk instalasi npm, composer, pip, dll.
2. Gunakan init_project untuk membuat project baru (React, Next.js, Laravel, PHP, dst.)
3. Untuk timeout panjang (build, install), timeout sudah diset 300 detik secara default.
4. Jangan sebutkan format XML/tool ini kepada pengguna secara langsung.
5. Setelah tool selesai, berikan ringkasan hasil yang jelas dan actionable.
6. Kamu bisa chain beberapa tool calls secara berurutan untuk menyelesaikan task kompleks.

Ketika membuat project:
- Selalu list_directory dulu untuk cek apakah folder tujuan sudah ada.
- Buat struktur yang rapi dan siap pakai.
- Berikan instruksi cara menjalankan project setelah selesai.
"""

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
def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def pad_to(text, width, fill=" "):
    """Pad plain string to a given width (tanpa ANSI codes)."""
    visible_len = len(re.sub(r'\033\[[0-9;]*m', '', text))
    return text + fill * max(0, width - visible_len)

def render_welcome_panel(model_name, api_key_masked):
    """Render panel welcome ala Claude CLI."""
    w = min(get_terminal_width() - 2, 90)
    half = (w - 2) // 2

    B  = COLOR_BORDER
    T  = COLOR_TITLE
    D  = COLOR_DIM
    A  = COLOR_ACCENT
    Y  = YELLOW
    R  = RESET

    sep_h = "─" * (w - 2)

    def box_line(left_content="", right_content="", divider=True):
        """Render satu baris dalam panel 2-kolom."""
        mid_char = "│" if divider else " "
        l = pad_to(left_content,  half)
        r = pad_to(right_content, w - half - 3)
        return f"  {B}│{R} {l} {B}{mid_char}{R} {r} {B}│{R}"

    lines = []
    lines.append(f"  {B}╭{sep_h}╮{R}")

    # Row: Welcome + Tips header
    welcome_text  = f"{BOLD}{T}Welcome back!{R}"
    tips_text     = f"{A}{BOLD}Tips untuk memulai{R}"
    lines.append(box_line(welcome_text, tips_text))

    lines.append(f"  {B}│{R} {' ' * (half)} {B}│{R} {' ' * (w - half - 3)} {B}│{R}")

    # Row: Model info + Tip 1
    model_text    = f"{D}Model  : {R}{BOLD}{COLOR_LYRA}{model_name}{R}"
    tip1_text     = f"{D}Ketik {R}{BOLD}/model{R}{D} untuk ganti model AI{R}"
    lines.append(box_line(model_text, tip1_text))

    # Row: API key masked + Tip 2
    key_text      = f"{D}API Key: {R}{DIM}{api_key_masked}{R}"
    tip2_text     = f"{D}Ketik {R}{BOLD}/project{R}{D} untuk buat project baru{R}"
    lines.append(box_line(key_text, tip2_text))

    # Row: Tip 3
    blank_l       = ""
    tip3_text     = f"{D}Ketik {R}{BOLD}/help{R}{D} untuk lihat semua perintah{R}"
    lines.append(box_line(blank_l, tip3_text))

    lines.append(f"  {B}╰{sep_h}╯{R}")
    return "\n".join(lines)

def render_model_selector(current_idx):
    """Render model selector interaktif ala Claude CLI."""
    w = min(get_terminal_width() - 2, 80)

    B  = COLOR_BORDER
    T  = COLOR_TITLE
    A  = COLOR_ACCENT
    D  = COLOR_DIM
    Y  = YELLOW
    R  = RESET

    sep_h = "─" * (w - 2)

    print(f"\n  {B}╭{sep_h}╮{R}")
    print(f"  {B}│{R}  {BOLD}{A}Pilih Model{R}{' ' * (w - 15)}{B}│{R}")
    print(f"  {B}│{R}  {D}Ganti model AI untuk sesi ini dan sesi berikutnya.{R}{' ' * max(0, w - 55)}{B}│{R}")
    print(f"  {B}│{R}{' ' * (w - 2)}{B}│{R}")

    for i, m in enumerate(MODELS):
        selected = (i == current_idx)
        cursor   = f"{BOLD}{A}❯{R}" if selected else "  "
        num_col  = f"{BOLD}{T}{i+1}.{R}" if not selected else f"{BOLD}{A}{i+1}.{R}"
        tag_col  = f"{A}{m['tag']}{R}" if selected else f"{D}{m['tag']}{R}"
        name_col = f"{BOLD}{COLOR_LYRA}{m['name']}{R}" if selected else f"{BOLD}{T}{m['name']}{R}"
        desc_col = f"{D}{m['desc']}{R}"
        check    = f" {GREEN}✓{R}" if selected else "  "

        row = f"  {B}│{R} {cursor} {num_col} {name_col}{check}   {tag_col}   {desc_col}"
        visible = len(re.sub(r'\033\[[0-9;]*m', '', row))
        padding = max(0, w - visible + 2)
        print(row + " " * padding + f"{B}│{R}")

    print(f"  {B}│{R}{' ' * (w - 2)}{B}│{R}")
    print(f"  {B}│{R}  {D}Masukkan nomor (1-{len(MODELS)}) lalu Enter • Tekan Enter untuk tetap pakai model sekarang{R}  {B}│{R}")
    print(f"  {B}╰{sep_h}╯{R}")

def render_help():
    """Tampilkan panel bantuan."""
    w = min(get_terminal_width() - 2, 80)
    B  = COLOR_BORDER
    T  = COLOR_TITLE
    A  = COLOR_ACCENT
    D  = COLOR_DIM
    Y  = YELLOW
    R  = RESET
    sep_h = "─" * (w - 2)

    cmds = [
        ("/model",          "Buka pilihan model AI"),
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

    print(f"\n  {B}╭{sep_h}╮{R}")
    print(f"  {B}│{R}  {BOLD}{A}Perintah Lyra CLI{R}{' ' * (w - 21)}{B}│{R}")
    print(f"  {B}│{R}{' ' * (w - 2)}{B}│{R}")
    for cmd, desc in cmds:
        row = f"  {B}│{R}   {BOLD}{Y}{cmd:<18}{R}  {D}{desc}{R}"
        visible = len(re.sub(r'\033\[[0-9;]*m', '', row))
        padding = max(0, w - visible + 2)
        print(row + " " * padding + f"{B}│{R}")
    print(f"  {B}│{R}{' ' * (w - 2)}{B}│{R}")
    print(f"  {B}╰{sep_h}╯{R}\n")

def print_lyra_message(text):
    """Print pesan Lyra dengan prefix dan styling yang konsisten."""
    lines = text.split("\n")
    prefix    = f"  {BOLD}{COLOR_LYRA}Lyra ✦{RESET} "
    continuation = "          "  # same width as prefix without color codes

    for i, line in enumerate(lines):
        if i == 0:
            print(f"{prefix}{WHITE}{line}{RESET}")
        else:
            print(f"{continuation}{WHITE}{line}{RESET}")

def print_tool_status(func_name, args_str, done=False):
    """Print status eksekusi tool."""
    if done:
        print(f"  {GREEN}✔{RESET} {DIM}Tool {COLOR_LYRA}{func_name}{RESET}{DIM} selesai.{RESET}\n")
    else:
        print(f"  {DIM}⚙  Memanggil: {RESET}{BOLD}{COLOR_LYRA}{func_name}{RESET}{DIM}({args_str}){RESET}")

# ─── Slash Command Handlers ───────────────────────────────────────────────────
def handle_model_command(config):
    """Interaktif model selector."""
    current_idx = config.get("model_index", DEFAULT_MODEL_INDEX)
    render_model_selector(current_idx)
    try:
        choice = input(f"\n  {BOLD}{COLOR_USER}Nomor model ❯{RESET} ").strip()
        if choice == "":
            print(f"  {DIM}Model tidak diubah.{RESET}\n")
            return current_idx
        idx = int(choice) - 1
        if 0 <= idx < len(MODELS):
            config["model_index"] = idx
            save_config(config)
            m = MODELS[idx]
            print(f"\n  {GREEN}✓{RESET} Model diubah ke {BOLD}{COLOR_LYRA}{m['name']}{RESET}\n")
            return idx
        else:
            print(f"  {RED}Nomor tidak valid.{RESET}\n")
            return current_idx
    except (ValueError, EOFError):
        print(f"  {RED}Input tidak valid.{RESET}\n")
        return current_idx

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
    # Load config & API key
    config  = load_config()
    api_key = get_api_key(config=config)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    model_idx  = config.get("model_index", DEFAULT_MODEL_INDEX)
    model_info = MODELS[model_idx]

    # Riwayat chat
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Direktori kerja aktif (bisa diubah dengan /cd)
    active_cwd = os.getcwd()

    # ── Tampilan awal ─────────────────────────────────────────────────────────
    print_logo()

    # Masked API key
    masked_key = api_key[:8] + "•" * (len(api_key) - 12) + api_key[-4:] if len(api_key) > 12 else "•" * len(api_key)
    print(render_welcome_panel(model_info["name"], masked_key))

    version_color = rgb_to_ansi(*hex_to_rgb("#A78BFA"))
    print(f"\n  {version_color}Lyra CLI v2.0{RESET}  {DIM}·{RESET}  {DIM}Ketik /help untuk bantuan{RESET}\n")

    # ── Loop utama ────────────────────────────────────────────────────────────
    while True:
        try:
            cwd_short = active_cwd.replace(os.path.expanduser("~"), "~")
            prompt_str = (
                f"  {DIM}{cwd_short}{RESET}\n"
                f"  {BOLD}{COLOR_USER}❯{RESET} "
            )
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
                continue

            elif user_input.lower() == "/project":
                handle_project_command(active_cwd)
                continue

            elif user_input.lower() == "/clear":
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
            messages.append({"role": "user", "content": user_input})

            while True:
                spinner = Spinner(f"Lyra sedang berpikir...")
                spinner.start()

                current_model = MODELS[model_idx]["id"]
                data = {
                    "model":       current_model,
                    "messages":    messages,
                    "temperature": 0.2,
                }

                try:
                    response = requests.post(
                        API_URL,
                        headers=headers,
                        json=data,
                        timeout=DEFAULT_TIMEOUT,
                    )
                    spinner.stop()

                    if response.status_code == 200:
                        resp_json  = response.json()
                        ai_message = resp_json["choices"][0]["message"]["content"]

                        text_before, tool_call_json = extract_tool_call(ai_message)

                        if text_before:
                            print()
                            print_lyra_message(text_before)

                        # Simpan respons ke riwayat
                        messages.append({"role": "assistant", "content": ai_message})

                        if tool_call_json:
                            try:
                                tool_call = json.loads(tool_call_json)
                                func_name = tool_call.get("name", "")
                                args      = tool_call.get("arguments", {})
                            except Exception:
                                print(f"  {RED}Gagal mengurai tool call JSON.{RESET}\n")
                                break

                            args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                            print()
                            print_tool_status(func_name, args_str)

                            # Dispatch tool
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
                            else:
                                result = f"Error: Tool '{func_name}' tidak dikenal."

                            print_tool_status(func_name, args_str, done=True)

                            messages.append({
                                "role":    "user",
                                "content": f"[Hasil Tool '{func_name}']\n{result}",
                            })
                            continue  # Kirim lagi ke AI dengan hasil tool

                        else:
                            if not text_before and ai_message:
                                print()
                                print_lyra_message(ai_message)
                            print()
                            break

                    elif response.status_code == 401:
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

                    else:
                        print(f"\n  {RED}[{response.status_code}] Gagal mendapatkan jawaban.{RESET}")
                        print(f"  {RED}{response.text[:500]}{RESET}\n")
                        if messages[-1]["role"] == "user":
                            messages.pop()
                        break

                except requests.exceptions.Timeout:
                    spinner.stop()
                    print(f"\n  {RED}Request timeout setelah {DEFAULT_TIMEOUT} detik.{RESET}")
                    print(f"  {DIM}Coba gunakan model yang lebih cepat atau sederhanakan pertanyaan.{RESET}\n")
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break
                except Exception as e:
                    spinner.stop()
                    print(f"\n  {RED}Kesalahan: {e}{RESET}\n")
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break

        except KeyboardInterrupt:
            print(f"\n\n  {GREEN}Selamat tinggal! Terima kasih menggunakan Lyra CLI.{RESET}\n")
            break
        except Exception as e:
            print(f"\n  {RED}Kesalahan sistem: {e}{RESET}\n")

if __name__ == "__main__":
    main()