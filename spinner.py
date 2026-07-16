import sys
import threading
import time
from styling import COLOR_LYRA, COLOR_DIM, RESET, BOLD, DIM

class Spinner:
    """Animated spinner yang berjalan di background thread."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message="Lyra sedang berpikir..."):
        self.message    = message
        self.stop_event = threading.Event()
        self.thread     = None
        self._i         = 0

    def _spin(self):
        elapsed = 0.0
        start   = time.time()
        while not self.stop_event.is_set():
            elapsed = time.time() - start
            frame   = self.FRAMES[self._i % len(self.FRAMES)]
            elapsed_str = f"{elapsed:.0f}s" if elapsed >= 1.0 else ""
            line = (
                f"\r  {COLOR_LYRA}{BOLD}{frame}{RESET} "
                f"{DIM}{self.message}{RESET}"
                f"  {COLOR_DIM}{elapsed_str}{RESET}"
            )
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(0.08)
            self._i += 1

    def start(self):
        self.stop_event.clear()
        self._i    = 0
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=1.0)
            # Bersihkan baris spinner
            sys.stdout.write("\r" + " " * (len(self.message) + 30) + "\r")
            sys.stdout.flush()
