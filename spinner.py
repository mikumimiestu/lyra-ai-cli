import sys
import threading
import time
from styling import COLOR_LYRA, RESET, DIM

class Spinner:
    def __init__(self, message="Lyra sedang berpikir..."):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None

    def _spin(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r  {COLOR_LYRA}{frames[i % len(frames)]}{RESET} {DIM}{self.message}{RESET}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.thread:
            self.stop_event.set()
            self.thread.join()
            # Clear the spinner line fully
            sys.stdout.write("\r" + " " * (len(self.message) + 15) + "\r")
            sys.stdout.flush()
