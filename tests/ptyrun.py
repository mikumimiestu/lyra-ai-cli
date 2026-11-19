"""Drive the real CLI inside a pseudo-terminal and read back what it left on the screen (POSIX only)."""
import json
import os
import pty
import select
import signal
import struct
import sys
import termios
import threading
import time
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from vtscreen import Screen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import tempfile
SESSIONS_FOR_TESTS = tempfile.mkdtemp(prefix='lyra-pty-sessions-')


from fakeapi import FakeApi  # noqa: E402  (kept importable from here for the pty tests)


LAUNCHER = r'''
import sys
sys.path.insert(0, {root!r})
import app, tools
app.API_URL = {url!r}
app.load_config = lambda: {{"api_key": "test", "model_index": 2, "reasoning_effort": "medium"}}
app.save_config = lambda config: None
app.ensure_daemon_running = lambda: None
app.check_remote_version = lambda timeout=4.0: (False, app.VERSION)
_real_prompt = app.get_current_system_prompt
app.get_current_system_prompt = lambda: "sistem"
{extra}
app.main()
print("PROCESS-ENDED")
'''


class PtyRun:
    def __init__(self, url, rows=30, cols=100, env=None, extra='', cwd=None):
        self.screen = Screen(rows, cols)
        code = LAUNCHER.format(root=ROOT, url=url, extra=extra)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.environ.setdefault('LYRA_SESSIONS_DIR', SESSIONS_FOR_TESTS)
            os.environ.update(env or {})
            os.environ.pop('LYRA_CLASSIC', None) if not (env and 'LYRA_CLASSIC' in env) else None
            os.chdir(cwd or ROOT)
            os.execvp(sys.executable, [sys.executable, '-c', code])
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        self.raw = ''

    def pump(self, seconds=0.3):
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if not ready:
                continue
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                return False
            if not data:
                return False
            text = data.decode('utf-8', errors='replace')
            self.raw += text
            self.screen.feed(text)
            while self.screen.replies:
                os.write(self.fd, self.screen.replies.pop(0).encode())
        return True

    def send(self, text):
        os.write(self.fd, text.encode() if isinstance(text, str) else text)

    def wait_for(self, needle, timeout=8.0, where=None):
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.1)
            hay = self.screen.text() if where is None else where()
            if needle in hay:
                return True
        return False

    def close(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (OSError, ChildProcessError):
            pass
        try:
            os.close(self.fd)
        except OSError:
            pass


ONESHOT = r'''
import sys
sys.path.insert(0, {root!r})
import app
app.API_URL = {url!r}
app.load_config = lambda: {{"api_key": "test", "model_index": 2, "reasoning_effort": "medium"}}
app.save_config = lambda config: None
app.get_current_system_prompt = lambda: "sistem"
sys.argv = ["amagi"] + {args!r}
app.main()
'''


def run_cli(args, url, stdin=None, timeout=30):
    """Run `amagi <args>` as a real subprocess (no terminal) and return the CompletedProcess."""
    import subprocess
    env = dict(os.environ, LYRA_SESSIONS_DIR=SESSIONS_FOR_TESTS)
    return subprocess.run([sys.executable, '-c', ONESHOT.format(root=ROOT, url=url, args=list(args))],
                          input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=timeout, env=env, cwd=ROOT)
