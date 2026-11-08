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


# ─── Saved conversations (/resume) ────────────────────────────────────────────
import json
import secrets

DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.amagi_sessions")
MAX_SESSIONS = 30
MAX_SESSION_BYTES = 5 * 1024 * 1024


def sessions_dir() -> str:
    """Where conversations are saved. LYRA_SESSIONS_DIR overrides it (tests, shared machines)."""
    return os.environ.get("LYRA_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR


def history_enabled() -> bool:
    return os.environ.get("LYRA_NO_HISTORY", "").lower() not in ("1", "true", "yes")


def new_session_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def _session_path(session_id: str) -> str:
    safe = "".join(ch for ch in str(session_id) if ch.isalnum() or ch in "-_")
    return os.path.join(sessions_dir(), safe + ".json")


def session_title(messages) -> str:
    """First thing the user asked, without attached file contents."""
    for message in messages:
        content = str(message.get("content", ""))
        if message.get("role") == "user" and not content.startswith("[Hasil Tool") and not content.startswith("[Ringkasan"):
            first = content.split("\n[Referensi file:")[0].strip().splitlines()
            return (first[0] if first else "(tanpa judul)")[:70]
    return "(tanpa judul)"


def save_session(session_id: str, messages, cwd: str, started: float = None) -> bool:
    """Write the conversation (without the system prompt) to ~/.amagi_sessions. Private to the user (0600)."""
    if not history_enabled():
        return False
    turns = [{"role": m["role"], "content": str(m.get("content", ""))} for m in messages if m.get("role") != "system"]
    if not turns:
        return False
    data = {
        "id": session_id, "cwd": cwd, "title": session_title(turns),
        "started": started or time.time(), "updated": time.time(), "messages": turns,
    }
    try:
        payload = json.dumps(data, ensure_ascii=False)
        if len(payload.encode("utf-8")) > MAX_SESSION_BYTES:
            return False
        os.makedirs(sessions_dir(), mode=0o700, exist_ok=True)
        path = _session_path(session_id)
        temp = path + ".tmp"
        descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temp, path)
        _prune_sessions()
        return True
    except (OSError, ValueError):
        return False


def _prune_sessions():
    try:
        files = sorted((os.path.join(sessions_dir(), n) for n in os.listdir(sessions_dir()) if n.endswith(".json")),
                       key=os.path.getmtime, reverse=True)
        for old in files[MAX_SESSIONS:]:
            os.remove(old)
    except OSError:
        pass


def load_session(session_id: str):
    """Return the saved session dict, or None when missing or damaged."""
    try:
        with open(_session_path(session_id), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        messages = data["messages"]
        if not isinstance(messages, list) or not all(
                isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
                for m in messages):
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def list_sessions(limit: int = 20):
    """Most recent first: dicts with id, title, cwd, updated and count. Damaged files are skipped."""
    found = []
    try:
        names = [n for n in os.listdir(sessions_dir()) if n.endswith(".json")]
    except OSError:
        return []
    for name in sorted(names, key=lambda n: os.path.getmtime(os.path.join(sessions_dir(), n)), reverse=True):
        data = load_session(name[:-5])
        if data:
            found.append({"id": data.get("id", name[:-5]), "title": data.get("title", "(tanpa judul)"),
                          "cwd": data.get("cwd", ""), "updated": data.get("updated", 0),
                          "count": len(data["messages"])})
        if len(found) >= limit:
            break
    return found


def delete_all_sessions() -> int:
    removed = 0
    try:
        for name in os.listdir(sessions_dir()):
            if name.endswith(".json") or name.endswith(".tmp"):
                os.remove(os.path.join(sessions_dir(), name))
                removed += 1
    except OSError:
        pass
    return removed


def relative_time(timestamp: float) -> str:
    seconds = max(0, time.time() - float(timestamp or 0))
    if seconds < 90:
        return "baru saja"
    if seconds < 3600:
        return f"{int(seconds // 60)} menit lalu"
    if seconds < 86400:
        return f"{int(seconds // 3600)} jam lalu"
    if seconds < 172800:
        return "kemarin"
    return f"{int(seconds // 86400)} hari lalu"
