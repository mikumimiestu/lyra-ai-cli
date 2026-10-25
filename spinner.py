"""One-line terminal progress with a real elapsed clock and safe cleanup."""
import asyncio
import builtins
import os
import queue
import random
import signal
import sys
import threading
import time
import traceback
import _thread
from styling import (COLOR_DIM, ui_symbol, COLOR_LYRA, RESET, fit_console_text, get_gradient_color,
                     get_terminal_width, rgb_to_ansi, unicode_terminal)


# ─── Live console ─────────────────────────────────────────────────────────────
# The composer stays at the bottom while Lyra works, like Claude Code. The prompt_toolkit application
# owns the terminal for the whole session (main thread) and the agent loop runs in a worker thread.
# Whatever the worker prints is written *above* the live area through run_in_terminal, so finished lines
# scroll into the normal terminal history while the live area (streamed partial line, status line,
# composer, footer) is redrawn at the bottom. Lives in this file so that `/update` from older versions,
# which only fetch the files they already know, still delivers it.


_EOF = object()


class TurnCancelled(KeyboardInterrupt):
    """Esc or Ctrl+C while Lyra was working. Subclasses KeyboardInterrupt so existing handlers apply."""


def live_supported():
    """Live mode needs a POSIX terminal and prompt_toolkit; everything else keeps the classic prompt."""
    if os.name == 'nt' or os.environ.get('LYRA_CLASSIC', '').lower() in ('1', 'true', 'yes'):
        return False
    try:
        from styling import EDITOR_AVAILABLE
        return bool(EDITOR_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb')
    except (AttributeError, ValueError):
        return False


class LiveStdout:
    """Replaces sys.stdout while the live console runs: complete lines go above the live area."""
    encoding = 'utf-8'
    errors = 'replace'

    def __init__(self, live):
        self._live = live
        self._buffer = ''

    def write(self, text):
        if not text:
            return 0
        self._buffer += text
        if '\n' in self._buffer:
            head, _, self._buffer = self._buffer.rpartition('\n')
            self._live.print_above(head + '\n')
        return len(text)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        pass

    def isatty(self):
        return True

    def fileno(self):
        return self._live.real_stdout.fileno()

    def __getattr__(self, name):
        return getattr(self._live.real_stdout, name)


class LiveState:
    def __init__(self):
        self.active = False
        self.app = None
        self.loop = None
        self.editor = None
        self.ready = threading.Event()
        self.inbox = queue.Queue()
        self.busy = False
        self.cancel = threading.Event()
        self.partial = ''
        self.response = None
        self.real_stdout = None
        self.real_input = None
        self.exit_message = None     # shown after the UI is gone, once the screen is wiped
        self._status = None
        self._saved_runner = None
        self._ui_thread = None

    # -- UI side ---------------------------------------------------------
    def attach(self, app, loop):
        import styling
        self.app, self.loop = app, loop
        self.real_stdout = sys.stdout
        self.real_input = builtins.input
        self._ui_thread = threading.current_thread()
        sys.stdout = LiveStdout(self)
        builtins.input = self.input
        self._saved_runner = styling.TERMINAL_RUNNER
        styling.TERMINAL_RUNNER = self.call_in_terminal
        self.active = True

    def detach(self):
        import styling
        if not self.active:
            return
        self.active = False
        sys.stdout = self.real_stdout
        builtins.input = self.real_input
        styling.TERMINAL_RUNNER = self._saved_runner

    def submit(self, text):
        self.inbox.put(text)
        self.invalidate()

    def submit_eof(self):
        self.inbox.put(_EOF)

    def request_cancel(self):
        if not self.busy:
            return
        self.cancel.set()
        response = self.response
        if response is not None:
            try:
                response.close()        # wakes a worker blocked on the network
            except Exception:
                pass
        self.invalidate()

    def invalidate(self):
        app, loop = self.app, self.loop
        if app is not None and loop is not None and self.active:
            try:
                loop.call_soon_threadsafe(app.invalidate)
            except RuntimeError:
                pass

    def shutdown(self):
        app, loop = self.app, self.loop
        if app is None or loop is None or not self.active:
            return

        def stop():
            if app.is_running and not app.future.done():
                app.exit()
        try:
            loop.call_soon_threadsafe(stop)
        except RuntimeError:
            pass

    # -- worker side -----------------------------------------------------
    def read(self):
        self.busy = False
        self.invalidate()
        item = self.inbox.get()
        if item is _EOF:
            raise EOFError
        self.cancel.clear()
        self.busy = True
        self.invalidate()
        return item

    def check_cancel(self):
        if self.cancel.is_set():
            self.cancel.clear()
            raise TurnCancelled()

    def cancel_requested(self):
        return self.cancel.is_set()

    def _run_on_loop(self, make_job, timeout=None):
        """Run an async job on the UI loop from the worker thread and wait for its result."""
        from prompt_toolkit.application.current import set_app

        async def job():
            with set_app(self.app):
                return await make_job()
        return asyncio.run_coroutine_threadsafe(job(), self.loop).result(timeout)

    def _loop_usable(self):
        return bool(self.active and self.loop and self.app and self.app.is_running
                    and threading.current_thread() is not self._ui_thread)

    def print_above(self, text):
        if not self._loop_usable():
            if self.real_stdout is not None:
                self.real_stdout.write(text)
                self.real_stdout.flush()
            else:
                sys.__stdout__.write(text)
                sys.__stdout__.flush()
            return
        from prompt_toolkit.application import run_in_terminal

        def write():
            self.real_stdout.write(text)
            self.real_stdout.flush()
        try:
            self._run_on_loop(lambda: run_in_terminal(write), timeout=15)
        except Exception:
            write()

    def call_in_terminal(self, func):
        """Run blocking terminal code (input(), a menu) with the live area suspended."""
        if not self._loop_usable():
            return func()
        from prompt_toolkit.application import run_in_terminal

        def wrapped():
            saved = sys.stdout
            sys.stdout = self.real_stdout        # menus and input() must draw on the real terminal
            try:
                return func()
            finally:
                sys.stdout = saved
        return self._run_on_loop(lambda: run_in_terminal(wrapped, in_executor=True))

    def input(self, prompt=''):
        return self.call_in_terminal(lambda: self.real_input(prompt))

    # -- streamed answer -------------------------------------------------
    def write_stream(self, text):
        """Finished lines scroll above; the unfinished tail stays in the live area."""
        self.partial += text
        if '\n' in self.partial:
            head, _, self.partial = self.partial.rpartition('\n')
            self.print_above(head + '\n')
        self.invalidate()

    def flush_stream(self):
        if self.partial:
            leftover, self.partial = self.partial, ''
            self.print_above(leftover + '\n')
            self.invalidate()

    # -- status line -----------------------------------------------------
    def attach_status(self, status):
        self._status = status
        self.invalidate()

    def detach_status(self, status):
        if self._status is status:
            self._status = None
            self.invalidate()

    def status_visible(self):
        return self._status is not None

    def status_text(self):
        status = self._status
        return status.live_lines() if status is not None else ''


LIVE = LiveState()


def run_live(target):
    """Run `target(live)` in a worker thread and the live terminal UI in this (main) thread."""
    live = LIVE
    live.ready.clear()
    failure = []

    def worker():
        try:
            target(live)
        except BaseException:                       # never leave the user in a frozen UI
            failure.append(traceback.format_exc())
        finally:
            live.ready.set()
            live.shutdown()

    thread = threading.Thread(target=worker, name='lyra-worker', daemon=True)
    thread.start()
    live.ready.wait()
    editor = live.editor
    if editor is not None and thread.is_alive():
        try:
            editor.run_live()
        finally:
            live.detach()
    thread.join(timeout=3)
    if live.exit_message is not None and not failure:
        from styling import clear_terminal
        clear_terminal()
        sys.stdout.write(live.exit_message)
        sys.stdout.flush()
    if failure:
        sys.stderr.write(failure[0])


TIPS = [
    'ketik @ untuk menyertakan file ke pesan',
    'tekan Esc untuk menghentikan jawaban',
    '/status merangkum sesi dan perkiraan konteks',
    'Alt+Enter atau Ctrl+J menambah baris baru',
    '/todos menampilkan daftar tugas yang sedang berjalan',
    '/details membuka detail aktivitas terakhir',
    '/reasoning mengatur tingkat penalaran',
    '/clear mengosongkan percakapan dan konteks',
]


def format_tokens(chars):
    """Rough token count (about four characters each) for the status line, e.g. 1,1k."""
    count = int(chars // 4)
    return str(count) if count < 1000 else f'{count / 1000:.1f}k'.replace('.', ',')


class Spinner:
    FRAMES = ['·', '✢', '✳', '✶', '✻', '✽', '✻', '✶', '✳', '✢']
    ASCII_FRAMES = ['|', '/', '-', '\\']

    def __init__(self, message='Memproses permintaan...', tip=False):
        self.message = message
        self.tip = tip
        self.chars = 0
        self._tip_start = random.randrange(len(TIPS))
        self.stop_event = threading.Event()
        self.thread = None
        self._lock = threading.Lock()
        self._active = False
        self._started = None
        self._i = 0
        self._output = None
        self._animated = False
        self._live = False

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
        sep = ' · ' if unicode else ' / '
        counted = [seconds] + ([f'{"↓" if unicode else "v"} {format_tokens(self.chars)} token'] if self.chars >= 4 else [])
        options = [' (' + sep.join(counted + ['Esc batal']) + ')', ' (' + sep.join(counted) + ')', f' ({seconds})']
        suffix = next((option for option in options if width - len(prefix) - len(option) >= 16), options[-1])
        message = fit_console_text(self.message, max(1, width - len(prefix) - len(suffix)))
        # The glyph breathes through the Lyra gradient; the clock stays quiet.
        phase = abs(((self._i % 30) / 15.0) - 1.0)
        color = rgb_to_ansi(*get_gradient_color(phase)) or COLOR_LYRA
        return fit_console_text(f'{prefix}{message}{suffix}', width) if not color else \
            f'{color}{prefix}{message}{RESET}{COLOR_DIM}{suffix}{RESET}'

    def add_tokens(self, chars):
        """Count streamed characters (reasoning included) for the live token estimate."""
        self.chars += chars

    def _tip_line(self):
        width = max(1, get_terminal_width() - 1)
        tip = TIPS[(self._tip_start + int(self.elapsed // 10)) % len(TIPS)]
        text = f'  {ui_symbol("⎿", "L")}  Tips: {tip}'
        return f'{COLOR_DIM}{fit_console_text(text, width)}{RESET}'

    def _render(self):
        with self._lock:
            if self._active:
                text = '\r\033[2K' + self._line()
                if self.tip:
                    # Second line holds a rotating tip; the cursor returns to the status line.
                    text += '\n\033[2K' + self._tip_line() + '\033[1A\r'
                self._output.write(text)
                self._output.flush()
                self._i += 1

    def _spin(self):
        while not self.stop_event.wait(0.1):
            self._render()

    def live_lines(self):
        """Status text for the live console, which redraws it about ten times a second."""
        self._i += 1
        return self._line() + ('\n' + self._tip_line() if self.tip else '')

    def start(self):
        if self._active:
            return
        self.stop_event.clear()
        self._started = time.monotonic()
        self._active = True
        if LIVE.active:
            self._live = True
            LIVE.attach_status(self)
            return
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
            if self._active and not self._animated and not self._live:
                self._output.write('  ' + fit_console_text(message, max(1, get_terminal_width() - 3)) + '\n')
                self._output.flush()

    def stop(self):
        if not self._active:
            return
        if self._live:
            self._live = False
            self._active = False
            LIVE.detach_status(self)
            return
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join()
        with self._lock:
            self._active = False
            if self._animated:
                self._output.write('\r\033[2K' + ('\033[1B\033[2K\033[1A\r' if self.tip else ''))
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
        if LIVE.active:
            return False            # the live console already owns the keyboard
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
