"""One-line terminal progress with a real elapsed clock and safe cleanup."""
import os
import sys
import threading
import time
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
        full = f' ({seconds} {"·" if unicode else "/"} Ctrl+C batal)'
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
