import os
import subprocess
from styling import BOLD, RED, RESET

def list_directory(path="."):
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: Path '{path}' tidak ditemukan."
        if not os.path.isdir(abs_path):
            return f"Error: Path '{path}' bukan sebuah direktori."
        
        items = os.listdir(abs_path)
        result = []
        for item in items:
            item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(item_path)
            prefix = "[DIR] " if is_dir else "[FILE]"
            result.append(f"{prefix} {item}")
        return "\n".join(result) if result else "Direktori kosong."
    except Exception as e:
        return f"Error membaca direktori: {str(e)}"

def read_file(filepath):
    try:
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return f"Error: File '{filepath}' tidak ditemukan."
        if os.path.isdir(abs_path):
            return f"Error: '{filepath}' adalah direktori, bukan file."
        
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error membaca file: {str(e)}"

def write_file(filepath, content):
    try:
        abs_path = os.path.abspath(filepath)
        print(f"\n  {BOLD}{RED}⚠️  Persetujuan Menulis File{RESET}")
        print(f"  Lyra ingin menulis ke file: {abs_path}")
        confirm = input(f"  Izinkan menulis ke file? (y/n): ").strip().lower()
        if confirm != 'y':
            return "Aksi menulis file ditolak oleh pengguna."
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Berhasil menulis ke file '{filepath}'."
    except Exception as e:
        return f"Error menulis ke file: {str(e)}"

def execute_command(command):
    try:
        print(f"\n  {BOLD}{RED}⚠️  Persetujuan Eksekusi Terminal{RESET}")
        print(f"  Lyra ingin menjalankan perintah: {command}")
        confirm = input(f"  Izinkan eksekusi perintah terminal? (y/n): ").strip().lower()
        if confirm != 'y':
            return "Aksi eksekusi perintah ditolak oleh pengguna."
        
        # Run the command locally
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except Exception as e:
        return f"Error saat eksekusi perintah terminal: {str(e)}"

# --- OpenAI-Compatible Tools Definition ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Mendaftar file dan folder di dalam suatu direktori lokal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path direktori yang ingin didaftar (default ke direktori saat ini '.')"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Membaca konten teks dari file lokal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path file lengkap yang ingin dibaca."
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Membuat file baru atau menimpa file lokal dengan konten tertentu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path file tujuan penulisan."
                    },
                    "content": {
                        "type": "string",
                        "description": "Konten teks yang ingin ditulis ke file."
                    }
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Menjalankan perintah terminal/shell di komputer lokal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Perintah shell lengkap yang ingin dijalankan."
                    }
                },
                "required": ["command"]
            }
        }
    }
]
