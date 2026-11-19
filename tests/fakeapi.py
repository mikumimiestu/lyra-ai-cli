"""A fake OpenAI-style streaming model API for tests (works on every OS; no pty needed)."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeApi:
    """OpenAI-style streaming endpoint. The last user message picks the scenario."""

    def __init__(self):
        self.requests = []
        self.custom = []          # (predicate(last), tokens) pairs checked before the built-in scenarios
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
        for predicate, tokens in self.custom:
            if predicate(last):
                return tokens
        if 'TRANSKRIP PERCAKAPAN' in last:
            return [('Ringkasan: pengguna menguji Lyra.', 0.01)]
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
