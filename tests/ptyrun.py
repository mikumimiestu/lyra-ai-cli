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


class FakeApi:
    """OpenAI-style streaming endpoint. The last user message picks the scenario."""

    def __init__(self):
        self.requests = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def _chunk(self, payload):
                self.wfile.write(f'{len(payload):x}\r\n'.encode() + payload + b'\r\n')
                self.wfile.flush()

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                api.requests.append(body)
                last = body['messages'][-1]['content']
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Transfer-Encoding', 'chunked')
                self.send_header('Connection', 'close')
                self.end_headers()
                for token, delay in api.script(last):
                    chunk = {'choices': [{'delta': {'content': token}}]}
                    try:
                        self._chunk(('data: ' + json.dumps(chunk) + '\n\n').encode())
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    time.sleep(delay)
                try:
                    self._chunk(b'data: [DONE]\n\n')
                    self.wfile.write(b'0\r\n\r\n')
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        self.server = Quiet(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}/v1/chat/completions'

    def script(self, last):
        if last.startswith('[Hasil Tool'):
            return [('Selesai membaca. ', 0.01), ('Ada dua berkas.\n', 0.01)]
        if 'lama' in last:
            return [(f'kata{i} ', 0.12) for i in range(200)]
        if 'alat' in last:
            call = '<tool_call>{"name": "list_directory", "arguments": {"path": "."}}</tool_call>'
            return [('Saya lihat folder dulu.\n', 0.02), (call, 0.02)]
        if 'tulis' in last:
            call = '<tool_call>{"name": "execute_command", "arguments": {"command": "echo halo-dari-tool"}}</tool_call>'
            return [('Saya jalankan perintah.\n', 0.02), (call, 0.02)]
        text = 'Halo! Ini **jawaban** dari Lyra.\n- poin satu\n- poin dua\nBaris terakhir `kode` selesai.\n'
        return [(word + ' ', 0.04) for word in text.replace('\n', ' \n').split(' ')]

    def close(self):
        self.server.shutdown()


LAUNCHER = r'''
import sys
sys.path.insert(0, {root!r})
import app, tools
app.API_URL = {url!r}
app.load_config = lambda: {{"api_key": "test", "model_index": 2, "reasoning_effort": "medium"}}
app.save_config = lambda config: None
app.ensure_daemon_running = lambda: None
app.check_remote_version = lambda timeout=4.0: (False, app.VERSION)
app.get_current_system_prompt = lambda: "sistem"
app.main()
print("PROCESS-ENDED")
'''


class PtyRun:
    def __init__(self, url, rows=30, cols=100, env=None):
        self.screen = Screen(rows, cols)
        code = LAUNCHER.format(root=ROOT, url=url)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.environ.update(env or {})
            os.environ.pop('LYRA_CLASSIC', None) if not (env and 'LYRA_CLASSIC' in env) else None
            os.chdir(ROOT)
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
