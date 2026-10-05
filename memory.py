import os
import time

MEMORY_FILE_PATH = os.path.expanduser("~/.amagi_memory.md")

def init_memory_file():
    """Memastikan file memori .md ada dengan format header standar."""
    if not os.path.exists(MEMORY_FILE_PATH):
        try:
            initial_content = (
                "# 🧠 Memori Amagi AI\n\n"
                "File ini berisi catatan, fakta, dan informasi penting yang diingat oleh Amagi AI.\n\n"
                "## 📝 Catatan Memori:\n"
            )
            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(initial_content)
        except Exception:
            pass

def read_memory() -> str:
    """Membaca isi file memori .md pengguna."""
    init_memory_file()
    try:
        if os.path.exists(MEMORY_FILE_PATH):
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    except Exception as e:
        return f"Error membaca memori: {e}"
    return ""

def save_memory(content: str, mode: str = "append") -> str:
    """
    Menyimpan atau menambahkan fakta/catatan baru ke file memori ~/.amagi_memory.md.
    mode: 'append' atau 'overwrite'
    """
    init_memory_file()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        if mode == "overwrite":
            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ Memori berhasil diperbarui (overwrite) di {MEMORY_FILE_PATH}."
        else:
            # Mode append: pastikan ada baris baru bertanggal
            entry = f"- [{timestamp}] {content.strip()}\n"
            with open(MEMORY_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"✅ Catatan memori baru berhasil disimpan ke {MEMORY_FILE_PATH}."
    except Exception as e:
        return f"❌ Gagal menyimpan memori: {e}"

def clear_memory() -> str:
    """Mereset file memori .md pengguna ke struktur awal."""
    try:
        initial_content = (
            "# 🧠 Memori Amagi AI\n\n"
            "File ini berisi catatan, fakta, dan informasi penting yang diingat oleh Amagi AI.\n\n"
            "## 📝 Catatan Memori:\n"
        )
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(initial_content)
        return "✅ Memori berhasil dibersihkan."
    except Exception as e:
        return f"❌ Gagal membersihkan memori: {e}"
