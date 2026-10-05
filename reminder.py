import os
import sys
import json
import time
import subprocess
import datetime
import re

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)


REMINDERS_FILE_PATH = os.path.expanduser("~/.amagi_reminders.json")
DAEMON_PID_PATH = os.path.expanduser("~/.amagi_daemon.pid")

def load_reminders() -> list:
    """Memuat daftar pengingat dari file JSON."""
    if os.path.exists(REMINDERS_FILE_PATH):
        try:
            with open(REMINDERS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_reminders(reminders: list):
    """Menyimpan daftar pengingat ke file JSON."""
    try:
        with open(REMINDERS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving reminders: {e}")

def send_desktop_notification(title: str, message: str, sound: bool = True):
    """Kirim notifikasi desktop ke laptop pengguna (macOS, Linux, Windows)."""
    system_platform = sys.platform
    
    clean_title = title.replace('"', '\\"').replace("'", "'\\''")
    clean_message = message.replace('"', '\\"').replace("'", "'\\''")

    if system_platform == "darwin":  # macOS
        sound_clause = ' sound name "Glass"' if sound else ""
        applescript = f'display notification "{clean_message}" with title "{clean_title}"{sound_clause}'
        try:
            subprocess.run(["osascript", "-e", applescript], check=False)
        except Exception:
            pass

    elif system_platform.startswith("linux"):
        try:
            subprocess.run(["notify-send", title, message], check=False)
            if sound:
                subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], check=False)
        except Exception:
            pass

    elif system_platform in ("win32", "cygwin"):
        ps_cmd = (
            f'[reflection.assembly]::loadwithpartialname("System.Windows.Forms"); '
            f'$notification = new-object system.windows.forms.notifyicon; '
            f'$notification.icon = [system.drawing.systemicons]::information; '
            f'$notification.visible = $true; '
            f'$notification.showballoontip(10000, "{title}", "{message}", [system.windows.forms.tooltipicon]::info)'
        )
        try:
            subprocess.run(["powershell", "-Command", ps_cmd], check=False)
        except Exception:
            pass

    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass

def parse_time_input(time_input: str) -> float:
    """
    Mengurai input waktu (e.g. '10m', '2h', '30s', '14:30', '2026-10-06 08:00:00')
    menjadi target timestamp (epoch seconds).
    """
    now = time.time()
    time_input = str(time_input).strip()

    # 1. Relatif: 10m, 2h, 30s, 1d
    rel_match = re.match(r"^(\d+)\s*([sSmMhHdD])$", time_input)
    if rel_match:
        amount = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return now + (amount * multiplier[unit])

    # 2. Angka polos dianggap detik jika <= 86400, atau menit
    if time_input.isdigit():
        sec = int(time_input)
        return now + sec

    # 3. Format Jam:Menit (e.g. 14:30 atau 08:15:00)
    if re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", time_input):
        parts = [int(x) for x in time_input.split(":")]
        now_dt = datetime.datetime.now()
        target_dt = now_dt.replace(
            hour=parts[0],
            minute=parts[1],
            second=parts[2] if len(parts) > 2 else 0,
            microsecond=0
        )
        if target_dt.timestamp() <= now:
            target_dt += datetime.timedelta(days=1)
        return target_dt.timestamp()

    # 4. Format Tanggal & Jam lengkap (YYYY-MM-DD HH:MM:SS)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.datetime.strptime(time_input, fmt)
            return dt.timestamp()
        except ValueError:
            pass

    raise ValueError(f"Format waktu '{time_input}' tidak dikenali. Gunakan format '10m', '1h', '14:30', atau 'YYYY-MM-DD HH:MM'.")

def add_reminder(message: str, time_input: str = None, delay_seconds: int = None) -> dict:
    """Menambahkan pengingat baru dan memicu background daemon."""
    now = time.time()
    if delay_seconds is not None and delay_seconds > 0:
        target_ts = now + float(delay_seconds)
    elif time_input:
        target_ts = parse_time_input(time_input)
    else:
        target_ts = now + 300  # Default 5 menit

    target_dt = datetime.datetime.fromtimestamp(target_ts)
    target_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")

    reminders = load_reminders()
    reminder_id = f"rem_{int(now)}_{len(reminders)+1}"
    
    new_rem = {
        "id": reminder_id,
        "message": message,
        "target_timestamp": target_ts,
        "target_time_str": target_str,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
        "sound": True
    }
    
    reminders.append(new_rem)
    save_reminders(reminders)
    
    # Pastikan daemon berjalan di background
    ensure_daemon_running()

    return new_rem

def list_reminders(status_filter: str = None) -> list:
    """Mendaftar seluruh pengingat."""
    reminders = load_reminders()
    if status_filter:
        return [r for r in reminders if r.get("status") == status_filter]
    return reminders

def cancel_reminder(reminder_id: str) -> bool:
    """Membatalkan pengingat yang pending."""
    reminders = load_reminders()
    updated = False
    for r in reminders:
        if r.get("id") == reminder_id and r.get("status") == "pending":
            r["status"] = "cancelled"
            updated = True
            break
    if updated:
        save_reminders(reminders)
    return updated

def is_daemon_running() -> bool:
    """Mengecek apakah background daemon pengingat sedang aktif."""
    if os.path.exists(DAEMON_PID_PATH):
        try:
            with open(DAEMON_PID_PATH, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            pass
    return False

def ensure_daemon_running():
    """Memastikan background daemon berjalan."""
    if not is_daemon_running():
        spawn_daemon()

def spawn_daemon():
    """Jalankan daemon background secara independen dari terminal."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(script_dir, "app.py")
        if not os.path.exists(app_path):
            app_path = os.path.expanduser("~/.amagi-cli/app.py")
            
        python_bin = sys.executable

        if os.name == 'posix':
            subprocess.Popen(
                [python_bin, app_path, "--daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        else:
            subprocess.Popen(
                [python_bin, app_path, "--daemon"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
    except Exception as e:
        print(f"Warning: Gagal menyalakan daemon pengingat latar belakang: {e}")

def run_reminder_daemon_loop():
    """
    Loop utama background daemon Amagi AI ("Amagi Bangun Sendiri").
    Tetap aktif di latar belakang, mengecek pengingat jatuh tempo dan memunculkan notifikasi desktop.
    """
    pid = os.getpid()
    try:
        with open(DAEMON_PID_PATH, "w") as f:
            f.write(str(pid))
    except Exception:
        pass

    while True:
        try:
            reminders = load_reminders()
            now = time.time()
            updated = False

            for r in reminders:
                if r.get("status") == "pending":
                    target_ts = r.get("target_timestamp", 0)
                    if now >= target_ts:
                        # PENGINGAT JATUH TEMPO - BUNCULKAN NOTIFIKASI LAPTOP!
                        msg = r.get("message", "Pengingat dari Amagi AI")
                        send_desktop_notification(
                            title="🔔 Pengingat Amagi AI",
                            message=msg,
                            sound=r.get("sound", True)
                        )
                        r["status"] = "triggered"
                        r["triggered_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        updated = True

            if updated:
                save_reminders(reminders)

            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(10)
