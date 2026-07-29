import os
import subprocess
import shlex
from styling import (
    BOLD, RED, GREEN, YELLOW, COLOR_USER, COLOR_LYRA, COLOR_DIM, RESET, DIM, CYAN,
    render_permission_box
)
from spinner import Spinner

# ─── Timeout yang lebih lama untuk operasi berat ─────────────────────────────
DEFAULT_TIMEOUT = 300   # 5 menit (dari 60 detik)

def _confirm_permission(action_title, details):
    """Meminta izin eksekusi pengguna dengan UI box yang elegan."""
    try:
        render_permission_box(action_title, details)
        answer = input(f"  {BOLD}{YELLOW}Izinkan eksekusi ini? (y/n) ❯ {RESET}").strip().lower()
        print()
        return answer == 'y'
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
        if not _confirm_permission("Konfirmasi Tulis File", details):
            return "Aksi menulis file dibatalkan oleh pengguna."

        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ Berhasil menulis ke '{filepath}'."
    except Exception as e:
        return f"Error menulis file: {str(e)}"

def create_directory(dirpath):
    """Membuat direktori hanya jika diizinkan pengguna."""
    try:
        abs_path = os.path.abspath(dirpath)
        details = {
            "Operasi": "Membuat Folder",
            "Path": abs_path
        }
        if not _confirm_permission("Konfirmasi Buat Folder", details):
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

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
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

def init_project(project_type, project_name, target_dir=None):
    """
    Memulai project baru (React, Next.js, PHP, Laravel, dll.)
    """
    project_type = project_type.lower()
    if target_dir:
        full_path = os.path.join(target_dir, project_name)
    else:
        full_path = project_name

    templates = {
        "react":     f"npx create-react-app {project_name}",
        "next":      f"npx create-next-app@latest {project_name} --ts --tailwind --eslint --app --no-git",
        "nextjs":    f"npx create-next-app@latest {project_name} --ts --tailwind --eslint --app --no-git",
        "vite":      f"npm create vite@latest {project_name} -- --template react-ts",
        "vue":       f"npm create vue@latest {project_name}",
        "laravel":   f"composer create-project laravel/laravel {project_name}",
        "php":       None,
        "express":   f"npx express-generator {project_name}",
        "fastapi":   None,
        "django":    f"django-admin startproject {project_name}",
        "flutter":   f"flutter create {project_name}",
        "node":      f"mkdir -p {project_name} && cd {project_name} && npm init -y",
    }

    if project_type in templates:
        cmd = templates[project_type]
        if cmd:
            return execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=target_dir)
        elif project_type == "php":
            details = {
                "Project": f"{project_type} native ({project_name})",
                "Target": full_path
            }
            if not _confirm_permission("Konfirmasi Inisialisasi Project", details):
                return "Inisialisasi project dibatalkan oleh pengguna."

            spinner = Spinner("Membuat struktur PHP...")
            spinner.start()
            cmds = [
                f"mkdir -p {full_path}/public {full_path}/src {full_path}/views",
                f"echo '<?php echo \"Hello World!\"; ?>' > {full_path}/public/index.php",
                f"echo '# {project_name} PHP Project' > {full_path}/README.md",
            ]
            results = []
            for c in cmds:
                res = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30)
                results.append(f"$ {c}\n{res.stdout or ''}{res.stderr or ''}")
            spinner.stop()
            return "\n".join(results)
        elif project_type == "fastapi":
            details = {
                "Project": f"{project_type} ({project_name})",
                "Target": full_path
            }
            if not _confirm_permission("Konfirmasi Inisialisasi Project", details):
                return "Inisialisasi project dibatalkan oleh pengguna."

            spinner = Spinner("Membuat struktur FastAPI...")
            spinner.start()
            cmds = [
                f"mkdir -p {full_path}/app",
                f"echo 'from fastapi import FastAPI\\n\\napp = FastAPI()\\n\\n@app.get(\"/\")\\ndef root():\\n    return {{\"message\": \"Hello World\"}}' > {full_path}/app/main.py",
                f"echo 'fastapi\\nuvicorn[standard]' > {full_path}/requirements.txt",
                f"echo '# {project_name} FastAPI Project' > {full_path}/README.md",
            ]
            results = []
            for c in cmds:
                res = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30)
                results.append(f"$ {c}\n{res.stdout or ''}{res.stderr or ''}")
            spinner.stop()
            return "\n".join(results)

    return f"Tipe project '{project_type}' belum didukung secara built-in. Perintah apa yang ingin dijalankan?"

