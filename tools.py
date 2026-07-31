import os
import subprocess
import shlex
from styling import (
    BOLD, RED, GREEN, YELLOW, COLOR_USER, COLOR_LYRA, COLOR_DIM, RESET, DIM, CYAN,
    render_permission_box
)
from spinner import Spinner

# ─── Timeout yang lebih lama untuk operasi berat ─────────────────────────────
DEFAULT_TIMEOUT = 600   # 10 menit — cukup untuk npm/composer install besar

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

def _run_cmds_silent(cmds, cwd=None, timeout=30):
    """Menjalankan sekumpulan shell command secara senyap, kembalikan gabungan output."""
    results = []
    for c in cmds:
        res = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if out:
            results.append(out)
        if err:
            results.append(err)
    return "\n".join(results) if results else "OK"


def init_project(project_type, project_name, target_dir=None):
    """
    Memulai project baru (React/Vite, Next.js, Vue, Svelte, Express, Node.js,
    FastAPI, Django, Flask, Laravel, PHP Native, dll.) secara NON-INTERAKTIF.
    Semua perintah menggunakan flag --yes / --no-interaction agar tidak macet.
    """
    project_type = project_type.lower().strip()
    cwd = target_dir or os.getcwd()
    full_path = os.path.join(cwd, project_name)

    # ── Konfirmasi kepada pengguna ────────────────────────────────────────────
    details = {
        "Tipe Project": project_type,
        "Nama"        : project_name,
        "Target Path" : full_path,
    }
    if not _confirm_permission("Inisialisasi Project Baru", details):
        return "Inisialisasi project dibatalkan oleh pengguna."

    spinner = Spinner(f"Menyiapkan project {project_type} '{project_name}'...")
    spinner.start()

    try:
        # ── JavaScript / TypeScript ───────────────────────────────────────────

        if project_type in ("react", "react-ts", "react-js"):
            template = "react-ts" if project_type != "react-js" else "react"
            cmd = (
                f"npx -y create-vite@latest {project_name} --template {template}"
                f" && cd {project_name} && npm install --silent"
            )
            result = execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ React ({template}) project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && npm run dev"
            )

        if project_type in ("next", "nextjs", "next-ts", "next-js"):
            ts_flag = "" if project_type == "next-js" else "--ts"
            cmd = (
                f"npx -y create-next-app@latest {project_name}"
                f" {ts_flag} --tailwind --eslint --app --src-dir"
                f" --import-alias '@/*' --use-npm --no-git"
                f" && cd {project_name} && npm install --silent"
            )
            result = execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ Next.js project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && npm run dev"
            )

        if project_type in ("vue", "vue-ts", "vue-js"):
            template = "vue-ts" if project_type != "vue-js" else "vue"
            cmd = (
                f"npx -y create-vite@latest {project_name} --template {template}"
                f" && cd {project_name} && npm install --silent"
            )
            result = execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ Vue 3 ({template}) project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && npm run dev"
            )

        if project_type in ("svelte", "svelte-ts"):
            template = "svelte-ts" if "ts" in project_type else "svelte"
            cmd = (
                f"npx -y create-vite@latest {project_name} --template {template}"
                f" && cd {project_name} && npm install --silent"
            )
            result = execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ Svelte project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && npm run dev"
            )

        if project_type in ("node", "nodejs"):
            cmds_init = [
                f"mkdir -p {project_name}/src",
                f"cd {project_name} && npm init -y",
            ]
            index_js = (
                "const http = require('http');\n\n"
                "const PORT = process.env.PORT || 3000;\n\n"
                "const server = http.createServer((req, res) => {\n"
                "  res.writeHead(200, { 'Content-Type': 'application/json' });\n"
                "  res.end(JSON.stringify({ message: 'Hello from Node.js!' }));\n"
                "});\n\n"
                "server.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n"
            )
            readme = f"# {project_name}\n\nA Node.js project.\n\n## Run\n\n```bash\nnode src/index.js\n```\n"
            _run_cmds_silent(cmds_init, cwd=cwd, timeout=60)
            with open(os.path.join(full_path, "src", "index.js"), "w") as f:
                f.write(index_js)
            with open(os.path.join(full_path, "README.md"), "w") as f:
                f.write(readme)
            spinner.stop()
            return (
                f"✅ Node.js project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && node src/index.js"
            )

        if project_type in ("express", "express-ts", "express-js"):
            use_ts = "ts" in project_type
            cmds_init = [f"mkdir -p {project_name}/src/routes {project_name}/src/middleware"]
            _run_cmds_silent(cmds_init, cwd=cwd, timeout=30)

            pkg = {
                "name": project_name, "version": "1.0.0", "main": "src/index.js",
                "scripts": {"start": "node src/index.js", "dev": "nodemon src/index.js"},
                "dependencies": {"express": "^4.18.2", "cors": "^2.8.5", "dotenv": "^16.0.3"},
                "devDependencies": {"nodemon": "^3.0.0"},
            }
            if use_ts:
                pkg["main"] = "dist/index.js"
                pkg["scripts"] = {
                    "start": "node dist/index.js",
                    "dev": "ts-node-dev src/index.ts",
                    "build": "tsc",
                }
                pkg["devDependencies"].update({
                    "typescript": "^5.0.0", "ts-node-dev": "^2.0.0",
                    "@types/express": "^4.17.21", "@types/cors": "^2.8.13",
                    "@types/node": "^20.0.0",
                })

            import json
            with open(os.path.join(full_path, "package.json"), "w") as f:
                json.dump(pkg, f, indent=2)

            ext = "ts" if use_ts else "js"
            index_content = (
                ("import express, { Request, Response } from 'express';\n"
                 "import cors from 'cors';\n"
                 "import dotenv from 'dotenv';\n"
                 "dotenv.config();\n\n")
                if use_ts else
                ("const express = require('express');\n"
                 "const cors = require('cors');\n"
                 "require('dotenv').config();\n\n")
            ) + (
                "const app = express();\n"
                "const PORT = process.env.PORT || 3000;\n\n"
                "app.use(cors());\n"
                "app.use(express.json());\n\n"
                "app.get('/', (req, res) => {\n"
                "  res.json({ message: 'Hello from Express!' });\n"
                "});\n\n"
                f"app.listen(PORT, () => console.log(`Server running on port ${{PORT}}`));\n"
            )
            with open(os.path.join(full_path, "src", f"index.{ext}"), "w") as f:
                f.write(index_content)
            with open(os.path.join(full_path, ".env"), "w") as f:
                f.write("PORT=3000\n")
            with open(os.path.join(full_path, ".gitignore"), "w") as f:
                f.write("node_modules/\n.env\ndist/\n")
            with open(os.path.join(full_path, "README.md"), "w") as f:
                f.write(f"# {project_name}\n\nExpress.js {'TypeScript' if use_ts else 'JavaScript'} API.\n\n## Run\n\n```bash\nnpm install\nnpm run dev\n```\n")

            install_cmd = execute_command(f"cd {project_name} && npm install --silent", timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{install_cmd}\n\n"
                f"✅ Express.js ({'TS' if use_ts else 'JS'}) project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name} && npm run dev"
            )

        # ── Python ─────────────────────────────────────────────────────────────

        if project_type in ("fastapi", "fast-api"):
            dirs = [
                f"{full_path}/app/routers",
                f"{full_path}/app/models",
                f"{full_path}/app/schemas",
                f"{full_path}/app/core",
            ]
            for d in dirs:
                os.makedirs(d, exist_ok=True)

            files = {
                "app/main.py": (
                    'from fastapi import FastAPI\nfrom app.routers import items\n\n'
                    'app = FastAPI(title="My FastAPI App", version="1.0.0")\n\n'
                    'app.include_router(items.router, prefix="/api")\n\n'
                    '@app.get("/")\nasync def root():\n    return {"message": "Hello from FastAPI!"}\n'
                ),
                "app/routers/__init__.py": "",
                "app/routers/items.py": (
                    'from fastapi import APIRouter\n\nrouter = APIRouter()\n\n'
                    '@router.get("/items")\nasync def get_items():\n    return [{"id": 1, "name": "Item One"}]\n'
                ),
                "app/models/__init__.py": "",
                "app/schemas/__init__.py": "",
                "app/core/__init__.py": "",
                "app/core/config.py": (
                    'from pydantic_settings import BaseSettings\n\n'
                    'class Settings(BaseSettings):\n    app_name: str = "My FastAPI App"\n    debug: bool = True\n\nsettings = Settings()\n'
                ),
                "app/__init__.py": "",
                "requirements.txt": "fastapi\nuvicorn[standard]\npydantic-settings\npython-dotenv\n",
                ".env": "DEBUG=true\n",
                ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n",
                "README.md": (
                    f"# {project_name}\n\nA FastAPI project.\n\n"
                    "## Setup\n\n```bash\npython3 -m venv venv\nsource venv/bin/activate\n"
                    "pip install -r requirements.txt\n```\n\n"
                    "## Run\n\n```bash\nuvicorn app.main:app --reload\n```\n"
                ),
            }
            for rel_path, content in files.items():
                fpath = os.path.join(full_path, rel_path)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(content)

            spinner.stop()
            return (
                f"✅ FastAPI project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name}\n"
                f"   python3 -m venv venv && source venv/bin/activate\n"
                f"   pip install -r requirements.txt\n"
                f"   uvicorn app.main:app --reload"
            )

        if project_type in ("django",):
            result = execute_command(
                f"django-admin startproject {project_name} . && python manage.py migrate",
                timeout=DEFAULT_TIMEOUT, cwd=full_path
            )
            os.makedirs(full_path, exist_ok=True)
            with open(os.path.join(full_path, "requirements.txt"), "w") as f:
                f.write("Django>=4.2\npython-dotenv\n")
            with open(os.path.join(full_path, ".gitignore"), "w") as f:
                f.write("__pycache__/\n*.pyc\n.env\nvenv/\ndb.sqlite3\n")
            with open(os.path.join(full_path, "README.md"), "w") as f:
                f.write(
                    f"# {project_name}\n\nA Django project.\n\n"
                    "## Setup\n\n```bash\npython3 -m venv venv\nsource venv/bin/activate\n"
                    "pip install -r requirements.txt\npython manage.py migrate\n```\n\n"
                    "## Run\n\n```bash\npython manage.py runserver\n```\n"
                )
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ Django project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name}\n"
                f"   python3 -m venv venv && source venv/bin/activate\n"
                f"   pip install -r requirements.txt\n"
                f"   python manage.py runserver"
            )

        if project_type in ("flask",):
            dirs = [
                f"{full_path}/app/routes",
                f"{full_path}/app/templates",
                f"{full_path}/app/static",
            ]
            for d in dirs:
                os.makedirs(d, exist_ok=True)

            files = {
                "app/__init__.py": (
                    'from flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n\n'
                    '    from app.routes.main import main\n    app.register_blueprint(main)\n\n'
                    '    return app\n'
                ),
                "app/routes/__init__.py": "",
                "app/routes/main.py": (
                    'from flask import Blueprint, jsonify\n\nmain = Blueprint("main", __name__)\n\n'
                    '@main.route("/")\ndef index():\n    return jsonify({"message": "Hello from Flask!"})\n'
                ),
                "run.py": "from app import create_app\n\napp = create_app()\n\nif __name__ == '__main__':\n    app.run(debug=True)\n",
                "requirements.txt": "flask\npython-dotenv\n",
                ".env": "FLASK_DEBUG=true\n",
                ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n",
                "README.md": (
                    f"# {project_name}\n\nA Flask project.\n\n"
                    "## Setup\n\n```bash\npython3 -m venv venv\nsource venv/bin/activate\n"
                    "pip install -r requirements.txt\n```\n\n"
                    "## Run\n\n```bash\npython run.py\n```\n"
                ),
            }
            for rel_path, content in files.items():
                fpath = os.path.join(full_path, rel_path)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(content)

            spinner.stop()
            return (
                f"✅ Flask project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name}\n"
                f"   python3 -m venv venv && source venv/bin/activate\n"
                f"   pip install -r requirements.txt\n"
                f"   python run.py"
            )

        # ── PHP / Laravel ──────────────────────────────────────────────────────

        if project_type in ("laravel",):
            cmd = f"composer create-project --prefer-dist laravel/laravel {project_name} --no-interaction"
            result = execute_command(cmd, timeout=DEFAULT_TIMEOUT, cwd=cwd)
            spinner.stop()
            return (
                f"{result}\n\n"
                f"✅ Laravel project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name}\n"
                f"   cp .env.example .env && php artisan key:generate\n"
                f"   php artisan serve"
            )

        if project_type in ("php", "php-native", "php-mvc"):
            dirs = [
                f"{full_path}/public",
                f"{full_path}/src/Controllers",
                f"{full_path}/src/Models",
                f"{full_path}/views/layouts",
                f"{full_path}/config",
                f"{full_path}/routes",
            ]
            for d in dirs:
                os.makedirs(d, exist_ok=True)

            files = {
                "public/index.php": (
                    '<?php\n\ndefine("ROOT", dirname(__DIR__));\n\nrequire_once ROOT . "/config/app.php";\nrequire_once ROOT . "/routes/web.php";\n'
                ),
                "config/app.php": (
                    '<?php\n\n// Load .env manually\nif (file_exists(ROOT . "/.env")) {\n'
                    '    $lines = file(ROOT . "/.env", FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);\n'
                    '    foreach ($lines as $line) {\n        if (strpos($line, "=") !== false) {\n'
                    '            [$key, $val] = explode("=", $line, 2);\n'
                    '            $_ENV[trim($key)] = trim($val);\n        }\n    }\n}\n\n'
                    'define("APP_NAME", $_ENV["APP_NAME"] ?? "My PHP App");\n'
                    'define("APP_DEBUG", ($_ENV["APP_DEBUG"] ?? "true") === "true");\n'
                ),
                "routes/web.php": (
                    '<?php\n\n$uri = parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH);\n\n'
                    'if ($uri === "/") {\n    require_once ROOT . "/src/Controllers/HomeController.php";\n'
                    '    $ctrl = new HomeController();\n    $ctrl->index();\n} else {\n'
                    '    http_response_code(404);\n    echo "404 Not Found";\n}\n'
                ),
                "src/Controllers/HomeController.php": (
                    '<?php\n\nclass HomeController {\n    public function index(): void {\n'
                    '        require_once ROOT . "/views/layouts/main.php";\n    }\n}\n'
                ),
                "views/layouts/main.php": (
                    '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n'
                    f'  <title>{project_name}</title>\n</head>\n<body>\n'
                    f'  <h1>Welcome to {project_name}!</h1>\n  <p>PHP Native MVC is running.</p>\n'
                    '</body>\n</html>\n'
                ),
                ".env": f'APP_NAME="{project_name}"\nAPP_DEBUG=true\n',
                ".gitignore": ".env\nvendor/\n",
                "README.md": (
                    f"# {project_name}\n\nA PHP Native MVC project.\n\n"
                    "## Run\n\n```bash\ncd public && php -S localhost:8000\n```\n"
                ),
            }
            for rel_path, content in files.items():
                fpath = os.path.join(full_path, rel_path)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w") as f:
                    f.write(content)

            spinner.stop()
            return (
                f"✅ PHP Native MVC project '{project_name}' berhasil dibuat!\n"
                f"   cd {project_name}/public && php -S localhost:8000"
            )

        spinner.stop()
        return (
            f"Tipe project '{project_type}' belum didukung secara built-in.\n"
            f"Tipe yang tersedia: react, react-ts, react-js, next, nextjs, next-ts, vue, vue-ts,\n"
            f"                    svelte, svelte-ts, node, nodejs, express, express-ts,\n"
            f"                    fastapi, django, flask, laravel, php, php-native, php-mvc"
        )

    except Exception as e:
        spinner.stop()
        return f"❌ Error saat membuat project: {str(e)}"

