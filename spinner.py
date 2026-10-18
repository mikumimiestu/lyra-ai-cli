"""One-line terminal progress with a real elapsed clock and safe cleanup."""
import os
import signal
import sys
import threading
import time
import _thread
from styling import (COLOR_DIM, COLOR_LYRA, RESET, fit_console_text, get_gradient_color,
                     get_terminal_width, rgb_to_ansi, unicode_terminal)


class Spinner:
    FRAMES = ['·', '✢', '✳', '✶', '✻', '✽', '✻', '✶', '✳', '✢']
    ASCII_FRAMES = ['|', '/', '-', '\\']

    def __init__(self, message='Memproses permintaan...'):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None
        self._lock = threading.Lock()
        self._active = False
        self._started = None
        self._i = 0
        self._output = None
        self._animated = False

    @property
    def elapsed(self):
        return max(0, time.monotonic() - self._started) if self._started is not None else 0

    def _line(self):
        unicode = unicode_terminal()
        frames = self.FRAMES if unicode else self.ASCII_FRAMES
        frame = frames[self._i % len(frames)]
        width = max(1, get_terminal_width() - 1)
        seconds = f'{self.elapsed:.0f}s'
        prefix = f'  {frame} '
        full = f' ({seconds} {"·" if unicode else "/"} Esc batal)'
        short = f' ({seconds})'
        suffix = full if width - len(prefix) - len(full) >= 16 else short
        message = fit_console_text(self.message, max(1, width - len(prefix) - len(suffix)))
        # The glyph breathes through the Lyra gradient; the clock stays quiet.
        phase = abs(((self._i % 30) / 15.0) - 1.0)
        color = rgb_to_ansi(*get_gradient_color(phase)) or COLOR_LYRA
        return fit_console_text(f'{prefix}{message}{suffix}', width) if not color else \
            f'{color}{prefix}{message}{RESET}{COLOR_DIM}{suffix}{RESET}'

    def _render(self):
        with self._lock:
            if self._active:
                self._output.write('\r\033[2K' + self._line())
                self._output.flush()
                self._i += 1

    def _spin(self):
        while not self.stop_event.wait(0.1):
            self._render()

    def start(self):
        if self._active:
            return
        self.stop_event.clear()
        self._started = time.monotonic()
        self._active = True
        self._output = sys.stdout
        self._animated = (self._output.isatty() and os.environ.get('TERM') != 'dumb'
                          and os.environ.get('LYRA_NO_ANIMATION', '').lower() not in ('1', 'true', 'yes'))
        if self._animated:
            self._render()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            self._output.write('  ' + fit_console_text(self.message, max(1, get_terminal_width() - 3)) + '\n')
            self._output.flush()

    def set_message(self, message):
        with self._lock:
            if message == self.message:
                return
            self.message = message
            if self._active and not self._animated:
                self._output.write('  ' + fit_console_text(message, max(1, get_terminal_width() - 3)) + '\n')
                self._output.flush()

    def stop(self):
        if not self._active:
            return
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join()
        with self._lock:
            self._active = False
            if self._animated:
                self._output.write('\r\033[2K')
                self._output.flush()
        self.thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def _interrupt_main():
    """Raise KeyboardInterrupt in the main thread, waking it from a blocking socket read."""
    if os.name == 'nt':
        _thread.interrupt_main()
    else:
        os.kill(os.getpid(), signal.SIGINT)


class EscapeWatcher:
    """While a response streams, a lone Esc key press cancels it like Ctrl+C.

    Arrow keys and other escape sequences start with the same byte and are ignored. The terminal is
    put in cbreak mode only for the duration of the `with` block, so prompts are never affected.
    Does nothing unless stdin and stdout are interactive terminals (or `force` is set for tests).
    """

    def __init__(self, on_escape=None, fd=None, force=False):
        self.on_escape = on_escape or _interrupt_main
        self.fd = fd
        self.force = force
        self.fired = False
        self._stop = threading.Event()
        self._thread = None
        self._saved = None

    def _enabled(self):
        if self.force:
            return True
        try:
            return (sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
                    and os.environ.get('LYRA_NO_ESC', '').lower() not in ('1', 'true', 'yes'))
        except (AttributeError, ValueError):
            return False

    def start(self):
        if not self._enabled():
            return
        try:
            if os.name == 'nt':
                self._thread = threading.Thread(target=self._watch_windows, daemon=True)
            else:
                import termios
                import tty
                if self.fd is None:
                    self.fd = sys.stdin.fileno()
                if os.isatty(self.fd):
                    self._saved = termios.tcgetattr(self.fd)
                    tty.setcbreak(self.fd)
                self._thread = threading.Thread(target=self._watch_posix, daemon=True)
            self._thread.start()
        except Exception:
            self._restore()
            self._thread = None

    def _fire(self):
        self.fired = True
        self._stop.set()
        self.on_escape()

    def _watch_posix(self):
        import select
        while not self._stop.is_set():
            try:
                ready, _, _ = select.select([self.fd], [], [], 0.1)
                if not ready:
                    continue
                data = os.read(self.fd, 64)
                if not data:
                    return
                if data == b'\x1b':
                    # A real Esc arrives alone; arrow keys follow it within milliseconds.
                    more, _, _ = select.select([self.fd], [], [], 0.05)
                    if more:
                        os.read(self.fd, 64)
                    else:
                        self._fire()
                        return
            except (OSError, ValueError):
                return

    def _watch_windows(self):
        import msvcrt
        while not self._stop.is_set():
            if msvcrt.kbhit():
                if msvcrt.getwch() == '\x1b':
                    self._fire()
                    return
            else:
                self._stop.wait(0.05)

    def _restore(self):
        if self._saved is not None:
            try:
                import termios
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved)
            except Exception:
                pass
            self._saved = None

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=0.5)
        self._thread = None
        self._restore()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
