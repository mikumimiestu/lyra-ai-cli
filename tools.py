import os
import sys
import subprocess
import shlex
import datetime
import time
import re
import fnmatch
import shutil

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from styling import (
    BOLD, RED, GREEN, YELLOW, COLOR_USER, COLOR_LYRA, COLOR_DIM, RESET, DIM, CYAN,
    render_permission_box, render_diff_preview, ui_symbol
)
from spinner import Spinner, LIVE
from memory import read_memory, save_memory, clear_memory
from reminder import add_reminder, list_reminders, cancel_reminder, ensure_daemon_running, is_daemon_running

# ─── Timeout yang lebih lama untuk operasi berat ─────────────────────────────
DEFAULT_TIMEOUT = 600   # 10 menit — cukup untuk npm/composer install besar

# ─── Approval modes ───────────────────────────────────────────────────────────
from styling import APPROVAL_MODES

APPROVAL_LABELS = {'ask': 'tanya dulu', 'edits': 'auto-setuju edit file', 'all': 'AUTO SEMUA'}

# Commands that always ask, even in "auto semua": hard to undo or reaching outside the project.
DANGEROUS_COMMAND_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in (
    r'\brm\s+(?:-\S*[rf]\S*|--recursive|--force)\b',
    r'\bsudo\b|\bdoas\b|\bsu\s+-',
    r'\bmkfs\b|\bdd\s+if=|>\s*/dev/(?:sd|nvme|disk)',
    r'\bchmod\s+-R\b|\bchown\s+-R\b',
    r'\bgit\s+push\b.*(?:--force|\s-f\b)|\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-\S*f',
    r'(?:curl|wget|iwr|irm)\b[^|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*iex\b',
    r'\bshutdown\b|\breboot\b|\bpoweroff\b|:\(\)\s*\{',
    r'\bformat\s+[a-z]:|\bdel\s+/[sfq]|\brmdir\s+/s|Remove-Item\b.*-Recurse',
    r'\bdrop\s+(?:database|table|schema)\b|\btruncate\s+table\b',
    r'\b(?:npm|yarn|pnpm|cargo|twine)\s+publish\b|\bpip\s+upload\b',
    r'~/\.ssh|\.env\b|\.aws/credentials',
)]


def is_dangerous_command(command):
    return any(pattern.search(str(command or '')) for pattern in DANGEROUS_COMMAND_PATTERNS)


class ApprovalMode:
    """How much Lyra may do without asking. Lives only for this process: it always starts on "ask"."""

    def __init__(self):
        self.mode = 'ask'

    def set(self, mode):
        if mode not in APPROVAL_MODES:
            raise ValueError(mode)
        self.mode = mode

    def cycle(self):
        self.mode = APPROVAL_MODES[(APPROVAL_MODES.index(self.mode) + 1) % len(APPROVAL_MODES)]
        return self.mode

    def allows(self, kind, details):
        """True when this action may run without a prompt."""
        if self.mode == 'ask':
            return False
        if kind == 'edit':
            return True
        return self.mode == 'all' and not is_dangerous_command(details.get('Perintah'))


APPROVAL = ApprovalMode()


def _confirm_permission(action_title, details, kind='command'):
    """Ask before acting, unless the approval mode already covers this kind of action.

    kind is "edit" for writing files and folders, "command" for anything that runs a program.
    """
    try:
        if APPROVAL.allows(kind, details):
            if kind != 'edit':
                render_permission_box(action_title, details)
            print(f"  {COLOR_DIM}{ui_symbol('⎿', 'L')}{RESET}  {GREEN}{ui_symbol('✔', 'OK')} Disetujui otomatis{RESET} "
                  f"{COLOR_DIM}(mode {APPROVAL_LABELS[APPROVAL.mode]}){RESET}\n")
            return True
        folded = render_permission_box(action_title, details)
        while True:
            hint = "y/n/v lihat semua" if folded else "y/n"
            answer = input(f"  {BOLD}{YELLOW}Izinkan? ({hint}) ❯ {RESET}").strip().lower()
            if folded and answer in ('v', 'lihat'):
                render_permission_box(action_title, details, full=True)
                folded = False
                continue
            print()
            return answer in ('y', 'ya', 'yes')
    except (EOFError, KeyboardInterrupt):
        print()
        return False

def list_directory(path=".", recursive=False, depth=2):
    """Mendaftar isi direktori secara senyap tanpa print log."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: Path '{path}' tidak ditemukan."
        if not os.path.isdir(abs_path):
            return f"Error: '{path}' bukan direktori."

        result = []

        def _walk(current_path, current_depth, prefix=""):
            if current_depth > depth:
                return
            try:
                items = sorted(os.listdir(current_path))
            except PermissionError:
                result.append(f"{prefix}[AKSES DITOLAK]")
                return

            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                item_path = os.path.join(current_path, item)
                is_dir = os.path.isdir(item_path)
                connector = "└── " if is_last else "├── "
                icon = "📁 " if is_dir else "📄 "
                result.append(f"{prefix}{connector}{icon}{item}")
                if is_dir and recursive:
                    extension = "    " if is_last else "│   "
                    _walk(item_path, current_depth + 1, prefix + extension)

        result.append(f"📂 {abs_path}")
        _walk(abs_path, 1)
        return "\n".join(result) if result else "Direktori kosong."
    except Exception as e:
        return f"Error membaca direktori: {str(e)}"

def read_file(filepath):
    """Membaca konten file teks secara senyap."""
    try:
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return f"Error: File '{filepath}' tidak ditemukan."
        if os.path.isdir(abs_path):
            return f"Error: '{filepath}' adalah direktori, bukan file."

        # Cek ukuran file
        size = os.path.getsize(abs_path)
        if size > 2 * 1024 * 1024:  # 2 MB limit
            return f"Error: File terlalu besar ({size // 1024} KB). Maks 2 MB."

        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error membaca file: {str(e)}"

def write_file(filepath, content):
    """Menulis konten ke file hanya jika diizinkan pengguna."""
    try:
        abs_path = os.path.abspath(filepath)
        details = {
            "Operasi": "Menulis File",
            "Path": abs_path,
            "Ukuran": f"{len(content)} karakter"
        }
        before = ''
        if os.path.isfile(abs_path):
            if os.path.getsize(abs_path) <= 2 * 1024 * 1024:
                with open(abs_path, 'r', encoding='utf-8', errors='replace') as existing:
                    before = existing.read()
            else:
                print('  File lama lebih dari 2 MB; preview hanya menampilkan konten baru.')
        render_diff_preview(before, content, filepath)
        if not _confirm_permission("Konfirmasi Tulis File", details, kind="edit"):
            return "Aksi menulis file dibatalkan oleh pengguna."

        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        before_bytes = _read_bytes(abs_path) if os.path.isfile(abs_path) else None
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        after_bytes = _read_bytes(abs_path)
        if after_bytes is not None:
            UNDO.record(abs_path, before_bytes, after_bytes, "write_file")
        return f"✅ Berhasil menulis ke '{filepath}'."
    except Exception as e:
        return f"Error menulis file: {str(e)}"

# ─── Undo stack ───────────────────────────────────────────────────────────────
UNDO_LIMIT_BYTES = 2 * 1024 * 1024   # larger files are not backed up
MAX_UNDO = 20


class UndoStack:
    """Remembers how a file looked before each change Lyra made, so /undo can put it back."""

    def __init__(self):
        self.items = []

    def record(self, path, before, after, tool):
        """before/after are bytes; before is None when Lyra created the file. Returns False when too large."""
        if (before is not None and len(before) > UNDO_LIMIT_BYTES) or len(after) > UNDO_LIMIT_BYTES:
            return False
        self.items.append({"path": path, "before": before, "after": after, "tool": tool, "time": time.time()})
        del self.items[:-MAX_UNDO]
        return True

    def clear(self):
        self.items = []


UNDO = UndoStack()


def _read_bytes(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def undo_last():
    """Restore the file touched by the most recent change, after showing what will happen."""
    if not UNDO.items:
        return "Belum ada perubahan yang bisa diurungkan."
    entry = UNDO.items[-1]
    path = entry["path"]
    current = _read_bytes(path)
    restoring = entry["before"]
    changed_since = current != entry["after"]
    details = {
        "Operasi": "Menghapus file yang dibuat Lyra" if restoring is None else "Mengembalikan versi sebelumnya",
        "Path": path,
    }
    if changed_since:
        details["Peringatan"] = "File diubah setelah perubahan Lyra; isi terkini akan ditimpa"
    try:
        before_text = (current or b"").decode("utf-8", errors="replace")
        after_text = "" if restoring is None else restoring.decode("utf-8", errors="replace")
        render_diff_preview(before_text, after_text, path)
        if not _confirm_permission("Konfirmasi Urungkan", details, kind="edit"):
            return "Pengurungan dibatalkan. Perubahan tetap bisa diurungkan nanti."
        if restoring is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, "wb") as handle:
                handle.write(restoring)
        UNDO.items.pop()
        return "✅ Dihapus: " + path if restoring is None else "✅ Dikembalikan: " + path
    except Exception as e:
        return f"Error mengurungkan: {e}"


def describe_undo_stack():
    lines = []
    for number, entry in enumerate(reversed(UNDO.items), 1):
        verb = {"edit_file": "Ubah", "write_file": "Tulis"}.get(entry["tool"], entry["tool"])
        lines.append(f"{number}. {time.strftime('%H:%M', time.localtime(entry['time']))} {verb} {entry['path']}"
                     + (" (baru)" if entry["before"] is None else ""))
    return lines


# ─── edit_file ────────────────────────────────────────────────────────────────
def edit_file(filepath, old, new, replace_all=False):
    """Replace exact text inside an existing file. Shows a diff and asks before writing."""
    try:
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            return "Error: argumen 'old' dan 'new' harus teks, dan 'old' tidak boleh kosong."
        if old == new:
            return "Error: 'old' dan 'new' sama, tidak ada yang berubah."
        abs_path = os.path.abspath(str(filepath))
        if not os.path.exists(abs_path):
            return f"Error: File '{filepath}' tidak ditemukan. Gunakan write_file untuk membuat file baru."
        if os.path.isdir(abs_path):
            return f"Error: '{filepath}' adalah direktori, bukan file."
        size = os.path.getsize(abs_path)
        if size > 2 * 1024 * 1024:
            return f"Error: File terlalu besar ({size // 1024} KB). Maks 2 MB."
        raw = _read_bytes(abs_path)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return f"Error: '{filepath}' bukan teks UTF-8."

        needle, replacement = old, new
        if "\r\n" in text and "\r\n" not in old:      # keep Windows line endings intact
            needle, replacement = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        count = text.count(needle)
        if count == 0:
            hint = " Spasi atau indentasi berbeda dari isi file." if old.strip() and old.strip() in text else ""
            return ("Error: teks 'old' tidak ditemukan di file." + hint +
                    " Baca ulang file dengan read_file lalu salin teks persis, termasuk spasi dan indentasi.")
        if count > 1 and not replace_all:
            return (f"Error: teks 'old' ditemukan {count} kali. Tambahkan baris di sekitarnya agar unik, "
                    "atau kirim replace_all true untuk mengganti semuanya.")
        updated = text.replace(needle, replacement) if replace_all else text.replace(needle, replacement, 1)
        replaced = count if replace_all else 1

        render_diff_preview(text, updated, filepath)
        details = {"Operasi": "Mengubah File", "Path": abs_path, "Penggantian": str(replaced)}
        if not _confirm_permission("Konfirmasi Ubah File", details, kind="edit"):
            return "Aksi mengubah file dibatalkan oleh pengguna."
        data = updated.encode("utf-8")
        with open(abs_path, "wb") as handle:
            handle.write(data)
        UNDO.record(abs_path, raw, data, "edit_file")
        return f"✅ Berhasil mengubah '{filepath}' ({replaced} penggantian)."
    except Exception as e:
        return f"Error mengubah file: {e}"


# ─── search ───────────────────────────────────────────────────────────────────
SEARCH_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build", ".next",
                    ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "target", ".gradle", ".cache", ".tox"}
SEARCH_MAX_FILE = 1024 * 1024
SEARCH_MAX_FILES = 20000


def _search_files(root, glob):
    """Yield (path, relative path) for text-like candidates under root, skipping junk and hidden folders."""
    if os.path.isfile(root):
        yield root, os.path.basename(root)
        return
    scanned = 0
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SEARCH_SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            scanned += 1
            if scanned > SEARCH_MAX_FILES:
                return
            relative = os.path.relpath(os.path.join(folder, name), root)
            if glob and not (fnmatch.fnmatch(name, glob) or fnmatch.fnmatch(relative, glob)):
                continue
            yield os.path.join(folder, name), relative


def search(pattern="", path=".", glob=None, ignore_case=False, max_results=100):
    """Regex search through text files, or list files by glob when no pattern is given."""
    try:
        try:
            limit = max(1, min(int(max_results), 200))
        except (TypeError, ValueError):
            limit = 100
        root = os.path.abspath(os.path.expanduser(str(path or ".")))
        if not os.path.exists(root):
            return f"Error: path '{path}' tidak ditemukan."
        glob = str(glob) if glob else None
        regex = None
        if pattern:
            try:
                regex = re.compile(str(pattern), re.IGNORECASE if ignore_case else 0)
            except re.error as error:
                return f"Error: pola regex tidak valid: {error}"
        elif not glob:
            return "Error: isi 'pattern' (regex) atau 'glob' (misalnya \"*.py\")."

        results = []
        truncated = False
        for full, relative in _search_files(root, glob):
            if regex is None:
                results.append(relative)
            else:
                try:
                    if os.path.getsize(full) > SEARCH_MAX_FILE:
                        continue
                    with open(full, "rb") as handle:
                        head = handle.read(4096)
                        if b"\0" in head:
                            continue
                        data = head + handle.read()
                except OSError:
                    continue
                for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        text = line.strip()
                        results.append(f"{relative}:{number}: {text[:200]}{'…' if len(text) > 200 else ''}")
                        if len(results) >= limit:
                            break
            if len(results) >= limit:
                truncated = True
                break
        if not results:
            return f"Tidak ada hasil untuk '{pattern or glob}'."
        out = "\n".join(results[:limit])
        return out + (f"\n… dipotong di {limit} hasil; persempit pola atau path." if truncated else "")
    except Exception as e:
        return f"Error mencari: {e}"


def create_directory(dirpath):
    """Membuat direktori hanya jika diizinkan pengguna."""
    try:
        abs_path = os.path.abspath(dirpath)
        details = {
            "Operasi": "Membuat Folder",
            "Path": abs_path
        }
        if not _confirm_permission("Konfirmasi Buat Folder", details, kind="edit"):
            return "Aksi membuat direktori dibatalkan oleh pengguna."

        os.makedirs(abs_path, exist_ok=True)
        return f"✅ Direktori '{dirpath}' berhasil dibuat."
    except Exception as e:
        return f"Error membuat direktori: {str(e)}"

def execute_command(command, timeout=None, cwd=None):
    """
    Menjalankan perintah terminal hanya jika diizinkan pengguna.
    Semua log eksekusi internal disembunyikan.
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    try:
        details = {
            "Perintah": command,
            "Direktori": cwd or os.getcwd(),
            "Timeout": f"{timeout} detik"
        }
        if not _confirm_permission("Konfirmasi Eksekusi Perintah", details):
            return "Eksekusi perintah dibatalkan oleh pengguna."

        spinner = Spinner("Menjalankan perintah...")
        spinner.start()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
        finally:
            spinner.stop()

        output_parts = [f"Exit Code: {result.returncode}"]
        if result.stdout:
            stdout = result.stdout
            if len(stdout) > 8000:
                stdout = stdout[:8000] + "\n... [output terpotong, terlalu panjang] ..."
            output_parts.append(f"STDOUT:\n{stdout}")
        if result.stderr:
            stderr = result.stderr
            if len(stderr) > 4000:
                stderr = stderr[:4000] + "\n... [stderr terpotong] ..."
            output_parts.append(f"STDERR:\n{stderr}")

        return "\n".join(output_parts)

    except subprocess.TimeoutExpired:
        if 'spinner' in locals():
            spinner.stop()
        return f"Error: Perintah melebihi batas waktu {timeout} detik."
    except Exception as e:
        if 'spinner' in locals():
            spinner.stop()
        return f"Error menjalankan perintah: {str(e)}"

# ─── Project scaffolding ──────────────────────────────────────────────────────
# Each project type is a short plan: optional files written by Lyra, plus commands run WITHOUT a shell
# (an argument list), so a project name can never smuggle in extra commands. The exact commands are shown
# in the confirmation, stdin is closed so a framework installer can never wait for a keypress, and a failing
# step is reported as a failure instead of "berhasil".
PROJECT_NAME_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
PYTHON_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
DART_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
RESERVED_NAMES = {
    'django': {'django', 'test', 'tests', 'site', 'admin'},
    'flutter': {'flutter', 'test', 'assert', 'break', 'case', 'catch', 'class', 'const', 'continue', 'default', 'do',
                'else', 'enum', 'extends', 'false', 'final', 'finally', 'for', 'if', 'in', 'is', 'new', 'null',
                'rethrow', 'return', 'super', 'switch', 'this', 'throw', 'true', 'try', 'var', 'void', 'while', 'with'},
}
PROJECT_ALIASES = {
    'react': 'react-ts', 'react-ts': 'react-ts', 'react-js': 'react-js',
    'next': 'next', 'nextjs': 'next', 'next-ts': 'next', 'next-js': 'next-js',
    'vue': 'vue-ts', 'vue-ts': 'vue-ts', 'vue-js': 'vue-js',
    'svelte': 'svelte', 'svelte-ts': 'svelte-ts',
    'node': 'node', 'nodejs': 'node',
    'express': 'express-js', 'express-js': 'express-js', 'express-ts': 'express-ts',
    'fastapi': 'fastapi', 'fast-api': 'fastapi', 'django': 'django', 'flask': 'flask',
    'laravel': 'laravel', 'php': 'php', 'php-native': 'php', 'php-mvc': 'php',
    'flutter': 'flutter',
}
SUPPORTED_PROJECTS = ("react, next, vue, svelte, node, express, fastapi, django, flask, laravel, php, flutter "
                      "(varian: react-js, next-js, vue-js, svelte-ts, express-ts)")
VITE_TEMPLATES = {'react-ts': 'react-ts', 'react-js': 'react', 'vue-ts': 'vue-ts', 'vue-js': 'vue',
                  'svelte': 'svelte', 'svelte-ts': 'svelte-ts'}
REQUIRED_TOOLS = {
    'react-ts': ('node', 'npm', 'npx'), 'react-js': ('node', 'npm', 'npx'), 'vue-ts': ('node', 'npm', 'npx'),
    'vue-js': ('node', 'npm', 'npx'), 'svelte': ('node', 'npm', 'npx'), 'svelte-ts': ('node', 'npm', 'npx'),
    'next': ('node', 'npm', 'npx'), 'next-js': ('node', 'npm', 'npx'), 'node': ('node', 'npm'),
    'express-js': ('node', 'npm'), 'express-ts': ('node', 'npm'),
    'django': ('python',), 'laravel': ('php', 'composer'), 'flutter': ('flutter',),
}
TOOL_HELP = {
    'node': ('Node.js', 'https://nodejs.org'), 'npm': ('Node.js (npm)', 'https://nodejs.org'),
    'npx': ('Node.js (npx)', 'https://nodejs.org'), 'python': ('Python 3', 'https://www.python.org/downloads/'),
    'php': ('PHP', 'https://www.php.net/downloads'), 'composer': ('Composer', 'https://getcomposer.org/download/'),
    'flutter': ('Flutter SDK', 'https://docs.flutter.dev/get-started/install'),
}


def normalize_project_type(project_type):
    """Canonical project kind for what the user or model typed, or None when it is not supported."""
    return PROJECT_ALIASES.get(str(project_type or '').strip().lower())


def validate_project_name(project_type, name):
    """Error text when `name` cannot be used for this project type, else None."""
    kind = normalize_project_type(project_type) or str(project_type or '')
    name = str(name or '')
    if not PROJECT_NAME_PATTERN.match(name):
        return ("Nama project hanya boleh berisi huruf, angka, titik, minus, dan garis bawah (maksimal 64 karakter), "
                "diawali huruf atau angka, tanpa spasi atau karakter khusus.")
    if kind == 'django':
        if not PYTHON_NAME_PATTERN.match(name) or name.lower() in RESERVED_NAMES['django']:
            return (f"Nama project Django harus berupa pengenal Python (huruf, angka, garis bawah; tidak boleh diawali angka "
                    f"atau memakai nama 'django' dan 'test'). Coba '{re.sub(r'[^A-Za-z0-9_]', '_', name)}_app'.")
    if kind == 'flutter':
        if not DART_NAME_PATTERN.match(name) or name in RESERVED_NAMES['flutter']:
            return (f"Nama project Flutter harus huruf kecil, angka, dan garis bawah, diawali huruf, dan bukan kata "
                    f"yang dicadangkan Dart. Coba '{re.sub(r'[^a-z0-9_]', '_', name.lower())}'.")
    return None


def _find_tool(name):
    if name == 'python':
        return shutil.which('python3') or shutil.which('python') or sys.executable
    return shutil.which(name)


def _display_command(args):
    """The command as the user would type it (program shown by name, not by its full path)."""
    shown = [os.path.basename(str(args[0]))] + [str(a) for a in args[1:]] if args else []
    if shown and shown[0].lower().endswith(('.cmd', '.exe', '.bat')):
        shown[0] = shown[0].rsplit('.', 1)[0]
    return subprocess.list2cmdline(shown) if os.name == 'nt' else ' '.join(shlex.quote(a) for a in shown)


def _run_step(args, cwd, timeout):
    """Run one scaffolding command without a shell. Returns (exit code, combined output).

    stdin is closed so an installer that would ask a question fails or takes its default instead of hanging.
    Esc (live console) or Ctrl+C stops the command; the process is killed first.
    """
    env = dict(os.environ, CI='1', NO_UPDATE_NOTIFIER='1', npm_config_yes='true', npm_config_fund='false')
    process = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, errors='replace', env=env)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                output, _ = process.communicate(timeout=0.4)
                return process.returncode, (output or '').strip()
            except subprocess.TimeoutExpired:
                if LIVE.cancel_requested():
                    process.kill()
                    process.communicate()
                    LIVE.check_cancel()
                if time.monotonic() > deadline:
                    process.kill()
                    process.communicate()
                    return -1, f'Waktu habis setelah {timeout} detik.'
    except BaseException:
        if process.poll() is None:
            process.kill()
        raise


def _write_files(root, files):
    for relative, content in files.items():
        path = os.path.join(root, *relative.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(content)


def _activate_hint():
    return r'venv\Scripts\activate' if os.name == 'nt' else 'source venv/bin/activate'


def _readme(name, title, setup='', run=''):
    body = f"# {name}\n\n{title}\n\n"
    if setup:
        body += f"## Setup\n\n```bash\n{setup}\n```\n\n"
    if run:
        body += f"## Run\n\n```bash\n{run}\n```\n"
    return body


def _node_files(name):
    return {
        'src/index.js': (
            "const http = require('http');\n\n"
            "const PORT = process.env.PORT || 3000;\n\n"
            "const server = http.createServer((req, res) => {\n"
            "  res.writeHead(200, { 'Content-Type': 'application/json' });\n"
            "  res.end(JSON.stringify({ message: 'Hello from Node.js!' }));\n"
            "});\n\n"
            "server.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n"),
        'README.md': _readme(name, 'A Node.js project.', run='node src/index.js'),
    }


def _express_files(name, use_ts):
    import json
    pkg = {
        "name": name, "version": "1.0.0", "main": "src/index.js",
        "scripts": {"start": "node src/index.js", "dev": "nodemon src/index.js"},
        "dependencies": {"express": "^4.18.2", "cors": "^2.8.5", "dotenv": "^16.0.3"},
        "devDependencies": {"nodemon": "^3.0.0"},
    }
    if use_ts:
        pkg["main"] = "dist/index.js"
        pkg["scripts"] = {"start": "node dist/index.js", "dev": "ts-node-dev src/index.ts", "build": "tsc"}
        pkg["devDependencies"].update({
            "typescript": "^5.0.0", "ts-node-dev": "^2.0.0", "@types/express": "^4.17.21",
            "@types/cors": "^2.8.13", "@types/node": "^20.0.0"})
    head = ("import express, { Request, Response } from 'express';\nimport cors from 'cors';\nimport dotenv from 'dotenv';\n"
            "dotenv.config();\n\n") if use_ts else (
            "const express = require('express');\nconst cors = require('cors');\nrequire('dotenv').config();\n\n")
    index = head + (
        "const app = express();\nconst PORT = process.env.PORT || 3000;\n\n"
        "app.use(cors());\napp.use(express.json());\n\n"
        "app.get('/', (req, res) => {\n  res.json({ message: 'Hello from Express!' });\n});\n\n"
        "app.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n")
    return {
        'package.json': json.dumps(pkg, indent=2) + "\n",
        f"src/index.{'ts' if use_ts else 'js'}": index,
        '.env': "PORT=3000\n",
        '.gitignore': "node_modules/\n.env\ndist/\n",
        'README.md': _readme(name, f"Express.js {'TypeScript' if use_ts else 'JavaScript'} API.", run="npm install\nnpm run dev"),
    }


def _fastapi_files(name):
    setup = f"python3 -m venv venv\n{_activate_hint()}\npip install -r requirements.txt"
    return {
        'app/main.py': (
            'from fastapi import FastAPI\nfrom app.routers import items\n\n'
            'app = FastAPI(title="My FastAPI App", version="1.0.0")\n\n'
            'app.include_router(items.router, prefix="/api")\n\n'
            '@app.get("/")\nasync def root():\n    return {"message": "Hello from FastAPI!"}\n'),
        'app/routers/__init__.py': "",
        'app/routers/items.py': (
            'from fastapi import APIRouter\n\nrouter = APIRouter()\n\n'
            '@router.get("/items")\nasync def get_items():\n    return [{"id": 1, "name": "Item One"}]\n'),
        'app/models/__init__.py': "", 'app/schemas/__init__.py': "", 'app/core/__init__.py': "", 'app/__init__.py': "",
        'app/core/config.py': (
            'from pydantic_settings import BaseSettings\n\n'
            'class Settings(BaseSettings):\n    app_name: str = "My FastAPI App"\n    debug: bool = True\n\nsettings = Settings()\n'),
        'requirements.txt': "fastapi\nuvicorn[standard]\npydantic-settings\npython-dotenv\n",
        '.env': "DEBUG=true\n",
        '.gitignore': "__pycache__/\n*.pyc\n.env\nvenv/\n",
        'README.md': _readme(name, 'A FastAPI project.', setup=setup, run='uvicorn app.main:app --reload'),
    }


def _flask_files(name, tailwind=False):
    setup = f"python3 -m venv venv\n{_activate_hint()}\npip install -r requirements.txt"
    files = {
        'app/__init__.py': (
            'from flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n\n'
            '    from app.routes.main import main\n    app.register_blueprint(main)\n\n    return app\n'),
        'app/routes/__init__.py': "",
        'app/routes/main.py': (
            'from flask import Blueprint, jsonify\n\nmain = Blueprint("main", __name__)\n\n'
            '@main.route("/")\ndef index():\n    return jsonify({"message": "Hello from Flask!"})\n'),
        'app/templates/.gitkeep': "", 'app/static/.gitkeep': "",
        'run.py': "from app import create_app\n\napp = create_app()\n\nif __name__ == '__main__':\n    app.run(debug=True)\n",
        'requirements.txt': "flask\npython-dotenv\n",
        '.env': "FLASK_DEBUG=true\n",
        '.gitignore': "__pycache__/\n*.pyc\n.env\nvenv/\n",
        'README.md': _readme(name, 'A Flask project.', setup=setup, run='python run.py'),
    }
    if tailwind:
        files['app/routes/main.py'] = (
            'from flask import Blueprint, render_template\n\nmain = Blueprint("main", __name__)\n\n'
            '@main.route("/")\ndef index():\n    return render_template("index.html")\n')
        files['app/templates/base.html'] = (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'  <title>{name}</title>\n'
            '  <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/tailwind.css\') }}">\n</head>\n<body>\n'
            '  {% block content %}{% endblock %}\n</body>\n</html>\n')
        files['app/templates/index.html'] = ("{% extends 'base.html' %}\n{% block content %}\n"
                                             + TAILWIND_PAGE.format(name=name) + "{% endblock %}\n")
        files['.gitignore'] += "node_modules/\n"
        files['README.md'] += "\n## Tailwind\n\n```bash\nnpm run watch:css\n```\n"
    return files


def _php_files(name, tailwind=False):
    files = {
        'public/index.php': '<?php\n\ndefine("ROOT", dirname(__DIR__));\n\nrequire_once ROOT . "/config/app.php";\nrequire_once ROOT . "/routes/web.php";\n',
        'config/app.php': (
            '<?php\n\n// Load .env manually\nif (file_exists(ROOT . "/.env")) {\n'
            '    $lines = file(ROOT . "/.env", FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);\n'
            '    foreach ($lines as $line) {\n        if (strpos($line, "=") !== false) {\n'
            '            [$key, $val] = explode("=", $line, 2);\n            $_ENV[trim($key)] = trim($val);\n        }\n    }\n}\n\n'
            'define("APP_NAME", $_ENV["APP_NAME"] ?? "My PHP App");\n'
            'define("APP_DEBUG", ($_ENV["APP_DEBUG"] ?? "true") === "true");\n'),
        'routes/web.php': (
            '<?php\n\n$uri = parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH);\n\n'
            'if ($uri === "/") {\n    require_once ROOT . "/src/Controllers/HomeController.php";\n'
            '    $ctrl = new HomeController();\n    $ctrl->index();\n} else {\n'
            '    http_response_code(404);\n    echo "404 Not Found";\n}\n'),
        'src/Controllers/HomeController.php': (
            '<?php\n\nclass HomeController {\n    public function index(): void {\n'
            '        require_once ROOT . "/views/layouts/main.php";\n    }\n}\n'),
        'src/Models/.gitkeep': "",
        'views/layouts/main.php': (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n'
            f'  <title>{name}</title>\n</head>\n<body>\n  <h1>Welcome to {name}!</h1>\n  <p>PHP Native MVC is running.</p>\n</body>\n</html>\n'),
        '.env': f'APP_NAME="{name}"\nAPP_DEBUG=true\n',
        '.gitignore': ".env\nvendor/\n",
        'README.md': _readme(name, 'A PHP Native MVC project.', run='cd public && php -S localhost:8000'),
    }
    if tailwind:
        layout = files['views/layouts/main.php']
        files['views/layouts/main.php'] = layout.replace(
            '</head>', '  <link rel="stylesheet" href="/css/tailwind.css">\n</head>', 1).replace(
            '<body>\n  <h1>', '<body class="min-h-screen flex flex-col items-center justify-center gap-2 bg-slate-50">\n  <h1 class="text-3xl font-bold text-slate-800">', 1)
        files['.gitignore'] += "node_modules/\n"
        files['README.md'] += "\n## Tailwind\n\n```bash\nnpm run watch:css\n```\n"
    return files


def _django_files(name):
    setup = f"python3 -m venv venv\n{_activate_hint()}\npip install -r requirements.txt\npython manage.py migrate"
    return {
        'requirements.txt': "Django>=4.2\npython-dotenv\n",
        '.gitignore': "__pycache__/\n*.pyc\n.env\nvenv/\ndb.sqlite3\n",
        'README.md': _readme(name, 'A Django project.', setup=setup, run='python manage.py runserver'),
    }



# ─── Tailwind CSS ─────────────────────────────────────────────────────────────
TAILWIND_KINDS = {'react-ts', 'react-js', 'vue-ts', 'vue-js', 'svelte', 'svelte-ts', 'next', 'next-js',
                  'django', 'flask', 'php'}
TAILWIND_BUILTIN = {'laravel'}          # Laravel already ships Tailwind through Vite
VITE_CSS_CANDIDATES = ('src/index.css', 'src/style.css', 'src/app.css')
TAILWIND_IMPORT = '@import "tailwindcss";\n'


def _patch_vite_config(root):
    """Register @tailwindcss/vite in vite.config.(ts|js|mjs|mts). Returns a note when it needs the user's attention."""
    path = next((os.path.join(root, n) for n in ('vite.config.ts', 'vite.config.js', 'vite.config.mts', 'vite.config.mjs')
                 if os.path.exists(os.path.join(root, n))), None)
    if not path:
        return "vite.config tidak ditemukan: tambahkan plugin tailwindcss() dari '@tailwindcss/vite' secara manual."
    text = open(path, encoding='utf-8').read()
    if '@tailwindcss/vite' in text:
        return None
    imports = list(re.finditer(r"^import .*$", text, re.MULTILINE))
    line = "import tailwindcss from '@tailwindcss/vite'"
    if imports:
        end = imports[-1].end()
        text = text[:end] + "\n" + line + text[end:]
    else:
        text = line + "\n" + text
    if re.search(r"plugins\s*:\s*\[", text):
        text = re.sub(r"plugins\s*:\s*\[", "plugins: [\n    tailwindcss(),", text, count=1)
    elif re.search(r"defineConfig\(\s*\{", text):
        text = re.sub(r"defineConfig\(\s*\{", "defineConfig({\n  plugins: [tailwindcss()],", text, count=1)
    else:
        return ("vite.config punya bentuk yang tidak dikenali: tambahkan tailwindcss() ke daftar plugins "
                "(import dari '@tailwindcss/vite') secara manual.")
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    return None


def _tailwind_vite_post(root):
    notes = []
    note = _patch_vite_config(root)
    if note:
        notes.append(note)
    css = next((c for c in VITE_CSS_CANDIDATES if os.path.exists(os.path.join(root, *c.split('/')))), None)
    if css:
        with open(os.path.join(root, *css.split('/')), 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(TAILWIND_IMPORT)
    else:
        notes.append('File CSS utama tidak ditemukan: tambahkan @import "tailwindcss"; ke CSS yang diimpor aplikasi.')
    return "\n".join(notes) or None


def _tailwind_cli_files(css_in, css_out):
    import json
    scripts = {'build:css': f'tailwindcss -i {css_in} -o {css_out} --minify',
               'watch:css': f'tailwindcss -i {css_in} -o {css_out} --watch'}
    return {'package.json': json.dumps({'private': True, 'scripts': scripts}, indent=2) + "\n", css_in: TAILWIND_IMPORT}


def _tailwind_cli_steps(root):
    npm = _find_tool('npm')
    return [("Memasang Tailwind CSS (npm)", [npm, 'install', '-D', 'tailwindcss', '@tailwindcss/cli', '--no-audit', '--no-fund'], root),
            ("Membuat CSS Tailwind", [npm, 'run', 'build:css'], root)]


TAILWIND_PAGE = ('<main class="min-h-screen flex items-center justify-center bg-slate-50">\n'
                 '  <h1 class="text-3xl font-bold text-slate-800">Selamat datang di {name}</h1>\n</main>\n')


def _tailwind_django_post(name):
    def patch(root):
        notes = []
        _write_files(root, {
            'templates/base.html': ('<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n'
                                    '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                                    f'  <title>{name}</title>\n  {{% load static %}}\n'
                                    '  <link rel="stylesheet" href="{% static \'css/tailwind.css\' %}">\n</head>\n<body>\n'
                                    '  {% block content %}{% endblock %}\n</body>\n</html>\n'),
            'templates/home.html': "{% extends 'base.html' %}\n{% block content %}\n" + TAILWIND_PAGE.format(name=name) + "{% endblock %}\n",
        })
        settings_path = os.path.join(root, name, 'settings.py')
        urls_path = os.path.join(root, name, 'urls.py')
        try:
            text = open(settings_path, encoding='utf-8').read()
            if "'DIRS': []," in text:
                text = text.replace("'DIRS': [],", "'DIRS': [BASE_DIR / 'templates'],", 1)
            else:
                notes.append("Tambahkan BASE_DIR / 'templates' ke TEMPLATES['DIRS'] di settings.py.")
            if 'STATICFILES_DIRS' not in text:
                text += "\nSTATICFILES_DIRS = [BASE_DIR / 'static']\n"
            with open(settings_path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(text)
            text = open(urls_path, encoding='utf-8').read()
            if 'from django.urls import path' in text and 'urlpatterns = [' in text:
                text = text.replace('from django.urls import path', 'from django.urls import path\nfrom django.views.generic import TemplateView', 1)
                text = text.replace('urlpatterns = [', "urlpatterns = [\n    path('', TemplateView.as_view(template_name='home.html'), name='home'),", 1)
                with open(urls_path, 'w', encoding='utf-8', newline='\n') as handle:
                    handle.write(text)
            else:
                notes.append("Tambahkan route ke 'home.html' di urls.py secara manual.")
        except (OSError, UnicodeError) as error:
            notes.append(f"settings.py/urls.py tidak bisa disesuaikan otomatis ({error}).")
        return "\n".join(notes) or None
    return patch


def _plan_project(kind, name, cwd, full_path, tailwind=False):
    """What to do for this project: files before, commands, files after, files that must exist, next steps."""
    npm, npx = _find_tool('npm'), _find_tool('npx')
    plan = {'before': {}, 'steps': [], 'after': {}, 'verify': [], 'make_folder': False, 'next': [], 'post': [],
            'late_steps': [], 'notes': []}
    if kind in VITE_TEMPLATES:
        plan['steps'] = [("Membuat project (create-vite)", [npx, '-y', 'create-vite@latest', name, '--template', VITE_TEMPLATES[kind]], cwd),
                         ("Memasang dependency (npm install)", [npm, 'install', '--no-audit', '--no-fund'], full_path)]
        plan['verify'] = ['package.json']
        plan['next'] = [f"cd {name}", "npm run dev"]
        if tailwind:
            plan['steps'].append(("Memasang Tailwind CSS (npm)", [npm, 'install', 'tailwindcss', '@tailwindcss/vite', '--no-audit', '--no-fund'], full_path))
            plan['post'].append(_tailwind_vite_post)
    elif kind in ('next', 'next-js'):
        plan['steps'] = [("Membuat project (create-next-app)",
                          [npx, '-y', 'create-next-app@latest', name, '--yes', '--js' if kind == 'next-js' else '--ts',
                           '--tailwind' if tailwind else '--no-tailwind', '--eslint', '--app', '--src-dir', '--import-alias', '@/*', '--use-npm',
                           '--disable-git'], cwd)]
        plan['verify'] = ['package.json']
        plan['next'] = [f"cd {name}", "npm run dev"]
    elif kind == 'node':
        plan['make_folder'] = True
        plan['steps'] = [("Menyiapkan package.json (npm init)", [npm, 'init', '-y'], full_path)]
        plan['after'] = _node_files(name)
        plan['verify'] = ['package.json']
        plan['next'] = [f"cd {name}", "node src/index.js"]
    elif kind in ('express-js', 'express-ts'):
        plan['make_folder'] = True
        plan['before'] = _express_files(name, kind == 'express-ts')
        plan['steps'] = [("Memasang dependency (npm install)", [npm, 'install', '--no-audit', '--no-fund'], full_path)]
        plan['verify'] = ['package.json']
        plan['next'] = [f"cd {name}", "npm run dev"]
    elif kind == 'fastapi':
        plan['make_folder'] = True
        plan['before'] = _fastapi_files(name)
        plan['next'] = [f"cd {name}", f"python3 -m venv venv && {_activate_hint()}", "pip install -r requirements.txt", "uvicorn app.main:app --reload"]
    elif kind == 'flask':
        plan['make_folder'] = True
        plan['before'] = _flask_files(name, tailwind)
        if tailwind:
            plan['before'].update(_tailwind_cli_files('app/static/src/input.css', 'app/static/css/tailwind.css'))
            plan['late_steps'] = _tailwind_cli_steps(full_path)
        plan['next'] = [f"cd {name}", f"python3 -m venv venv && {_activate_hint()}", "pip install -r requirements.txt", "python run.py"]
    elif kind == 'php':
        plan['make_folder'] = True
        plan['before'] = _php_files(name, tailwind)
        if tailwind:
            plan['before'].update(_tailwind_cli_files('src/input.css', 'public/css/tailwind.css'))
            plan['late_steps'] = _tailwind_cli_steps(full_path)
        plan['next'] = [f"cd {name}/public && php -S localhost:8000"]
    elif kind == 'django':
        python = _find_tool('python')
        venv_python = os.path.join(full_path, 'venv', 'Scripts' if os.name == 'nt' else 'bin', 'python' + ('.exe' if os.name == 'nt' else ''))
        plan['make_folder'] = True
        plan['steps'] = [("Membuat virtualenv", [python, '-m', 'venv', 'venv'], full_path),
                         ("Memasang Django (pip)", [venv_python, '-m', 'pip', 'install', 'Django'], full_path),
                         ("Membuat project Django", [venv_python, '-m', 'django', 'startproject', name, '.'], full_path),
                         ("Menjalankan migrasi awal", [venv_python, 'manage.py', 'migrate'], full_path)]
        plan['after'] = _django_files(name)
        if tailwind:
            plan['after'].update(_tailwind_cli_files('static/src/input.css', 'static/css/tailwind.css'))
            plan['post'].append(_tailwind_django_post(name))
            plan['late_steps'] = _tailwind_cli_steps(full_path)
        plan['verify'] = ['manage.py']
        plan['next'] = [f"cd {name}", _activate_hint(), "python manage.py runserver"]
    elif kind == 'laravel':
        plan['notes'].append("Laravel sudah memakai Tailwind CSS bawaan (lewat Vite), jadi tidak perlu dipasang lagi.")
        plan['steps'] = [("Membuat project (composer create-project)",
                          [_find_tool('composer'), 'create-project', '--prefer-dist', '--no-interaction', 'laravel/laravel', name], cwd)]
        plan['verify'] = ['artisan']
        plan['next'] = [f"cd {name}", "php artisan serve"]
    elif kind == 'flutter':
        plan['steps'] = [("Membuat project (flutter create)", [_find_tool('flutter'), 'create', name], cwd)]
        plan['verify'] = ['pubspec.yaml']
        plan['next'] = [f"cd {name}", "flutter run"]
    return plan


def _tail(text, lines=25):
    rows = [row for row in str(text).splitlines() if row.strip()]
    return "\n".join(rows[-lines:])


def init_project(project_type, project_name, target_dir=None, tailwind=None):
    """Create a new project (React/Vue/Svelte via Vite, Next.js, Node, Express, FastAPI, Django, Flask, Laravel,
    PHP, Flutter) without ever waiting for input. Returns a result text; never raises for ordinary failures."""
    kind = normalize_project_type(project_type)
    name = str(project_name or '').strip()
    if kind is None:
        return f"Tipe project '{project_type}' belum didukung.\nTipe yang tersedia: {SUPPORTED_PROJECTS}"
    problem = validate_project_name(kind, name)
    if problem:
        return f"❌ {problem}"
    cwd = os.path.abspath(os.path.expanduser(str(target_dir))) if target_dir else os.getcwd()
    full_path = os.path.join(cwd, name)

    missing = [tool for tool in REQUIRED_TOOLS.get(kind, ()) if not _find_tool(tool)]
    if missing:
        lines = []
        for tool in dict.fromkeys(missing):
            label, link = TOOL_HELP[tool]
            lines.append(f"   - {label}: {link}")
        return ("❌ Alat yang dibutuhkan belum terpasang atau belum ada di PATH:\n" + "\n".join(lines) +
                "\n   Pasang, buka terminal baru, lalu coba lagi.")
    if os.path.exists(full_path) and (not os.path.isdir(full_path) or os.listdir(full_path)):
        return (f"❌ '{full_path}' sudah ada dan tidak kosong. Pilih nama lain atau hapus folder itu dulu "
                f"supaya tidak ada file yang tertimpa.")

    if tailwind is None:
        tailwind = kind in ('next', 'next-js')          # create-next-app always shipped Tailwind in earlier versions
    tailwind = bool(tailwind)
    unsupported = tailwind and kind not in TAILWIND_KINDS and kind not in TAILWIND_BUILTIN
    tailwind = tailwind and kind in TAILWIND_KINDS
    plan = _plan_project(kind, name, cwd, full_path, tailwind)
    if unsupported:
        plan['notes'].append(f"Tailwind CSS tidak diterapkan otomatis untuk project {kind}.")
    if kind in TAILWIND_KINDS:
        plan['notes'].append("Tailwind CSS v4 " + ("dipasang dan dikonfigurasi otomatis." if tailwind else "tidak dipasang."))
    details = {"Tipe Project": kind, "Nama": name, "Target Path": full_path}
    if tailwind:
        details["Tailwind CSS"] = "ya, dipasang dan dikonfigurasi otomatis"
    commands = plan['steps'] + plan['late_steps']
    if commands:
        details["Perintah"] = "\n".join(_display_command(args) for _, args, _ in commands)
    if not _confirm_permission("Inisialisasi Project Baru", details, kind="command" if commands else "edit"):
        return "Inisialisasi project dibatalkan oleh pengguna."

    spinner = Spinner(f"Menyiapkan project {kind} '{name}'...")
    spinner.start()
    try:
        os.makedirs(cwd, exist_ok=True)
        if plan['make_folder']:
            os.makedirs(full_path, exist_ok=True)
        _write_files(full_path, plan['before'])
        for label, args, step_cwd in plan['steps']:
            spinner.set_message(label + "...")
            code, output = _run_step(args, step_cwd, DEFAULT_TIMEOUT)
            if code != 0:
                return (f"❌ Gagal pada langkah: {label} (kode keluar {code})\n{_tail(output)}\n\n"
                        f"Perintah: {_display_command(args)}\n"
                        f"Folder '{name}' mungkin setengah jadi; hapus lalu ulangi bila perlu.")
        _write_files(full_path, plan['after'])
        for patch in plan['post']:
            note = patch(full_path)
            if note:
                plan['notes'].append("Perlu dicek: " + note)
        for label, args, step_cwd in plan['late_steps']:
            spinner.set_message(label + "...")
            code, output = _run_step(args, step_cwd, DEFAULT_TIMEOUT)
            if code != 0:
                return (f"❌ Gagal pada langkah: {label} (kode keluar {code})\n{_tail(output)}\n\n"
                        f"Perintah: {_display_command(args)}\n"
                        f"Project sudah dibuat di '{full_path}', hanya langkah Tailwind yang gagal; ulangi perintah itu di folder project.")
        absent = [f for f in plan['verify'] if not os.path.exists(os.path.join(full_path, f))]
        if absent:
            return (f"❌ Perintah selesai tetapi {', '.join(absent)} tidak ditemukan di '{full_path}', "
                    f"jadi project belum terbentuk dengan benar.")
        extra = "".join(f"\n   ℹ {note}" for note in plan['notes'])
        return f"✅ Project {kind} '{name}' berhasil dibuat di {full_path}{extra}\n   " + "\n   ".join(plan['next'])
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            raise
        return f"❌ Error saat membuat project: {e}"
    finally:
        spinner.stop()


# ─── System Time & Date Tool ──────────────────────────────────────────────────
def get_system_time():
    """Mendapatkan informasi tanggal, waktu, dan zona waktu dari laptop pengguna."""
    now = datetime.datetime.now()
    days_id = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    months_id = {
        "January": "Januari", "February": "Februari", "March": "Maret",
        "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
        "August": "Agustus", "September": "September", "October": "Oktober",
        "November": "November", "December": "Desember"
    }
    
    day_en = now.strftime("%A")
    month_en = now.strftime("%B")
    
    day_id = days_id.get(day_en, day_en)
    month_id = months_id.get(month_en, month_en)
    
    date_str = f"{day_id}, {now.strftime('%d')} {month_id} {now.strftime('%Y')}"
    time_str = now.strftime("%H:%M:%S")
    tz_str = time.strftime("%Z") or time.tzname[0]
    
    return (
        f"📅 Tanggal : {date_str}\n"
        f"⏰ Waktu   : {time_str}\n"
        f"🌐 Timezone: {tz_str}"
    )

# ─── Memory Tools ─────────────────────────────────────────────────────────────
def tool_save_memory(content: str, mode: str = "append"):
    """Menyimpan catatan atau fakta ke file memori ~/.amagi_memory.md."""
    if not content:
        return "Error: Konten memori tidak boleh kosong."
    return save_memory(content, mode=mode)

def tool_read_memory():
    """Membaca isi file memori ~/.amagi_memory.md."""
    content = read_memory()
    return content if content.strip() else "(File memori kosong)"

def tool_clear_memory():
    """Mereset file memori."""
    return clear_memory()

# ─── Reminder Tools ───────────────────────────────────────────────────────────
def tool_set_reminder(message: str, time_input: str = None, delay_seconds: int = None):
    """Menambahkan pengingat baru dan mengaktifkan notifikasi laptop."""
    if not message:
        return "Error: Pesan pengingat tidak boleh kosong."
    try:
        rem = add_reminder(message=message, time_input=time_input, delay_seconds=delay_seconds)
        daemon_status = "Aktif (Background Daemon Running)" if is_daemon_running() else "Aktif"
        return (
            f"✅ Pengingat berhasil disetel!\n"
            f"   ● Pesan   : {rem['message']}\n"
            f"   ● Waktu   : {rem['target_time_str']}\n"
            f"   ● Status  : Pending ({daemon_status})\n"
            f"   ● Notif   : Amagi akan bangun dan memunculkan notifikasi di laptop Anda secara otomatis."
        )
    except Exception as e:
        return f"❌ Gagal menyetel pengingat: {e}"

def tool_list_reminders(status: str = None):
    """Mendaftar pengingat yang ada."""
    reminders = list_reminders(status_filter=status)
    if not reminders:
        return "Belum ada pengingat tersimpan."
    
    output = ["📋 Daftar Pengingat Amagi AI:"]
    for i, r in enumerate(reminders, 1):
        st = r.get("status", "pending").upper()
        output.append(f" {i}. [{st}] {r['message']} → {r['target_time_str']} (ID: {r['id']})")
    return "\n".join(output)

def tool_cancel_reminder(reminder_id: str):
    """Membatalkan pengingat."""
    success = cancel_reminder(reminder_id)
    if success:
        return f"✅ Pengingat ID '{reminder_id}' berhasil dibatalkan."
    return f"❌ Pengingat ID '{reminder_id}' tidak ditemukan atau sudah tidak aktif."




# ─── Todo List ────────────────────────────────────────────────────────────────
class TodoList:
    """Session checklist the model keeps up to date on multi-step tasks."""

    def __init__(self):
        self.items = []

    def update(self, raw):
        from styling import normalize_todos
        try:
            self.items = normalize_todos(raw)
        except ValueError as error:
            return f"Error: {error}"
        done = sum(1 for item in self.items if item['status'] == 'completed')
        active = [item['content'] for item in self.items if item['status'] == 'in_progress']
        message = f"Daftar tugas diperbarui: {done}/{len(self.items)} selesai."
        return message + (f" Sedang dikerjakan: {active[0]}" if active else "")

    def clear(self):
        self.items = []
