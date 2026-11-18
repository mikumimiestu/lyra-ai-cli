"""A stand-in for the Telegram Bot API, just enough for the bridge: getMe, getUpdates (long poll), sendMessage,
editMessageText, answerCallbackQuery and sendChatAction. Nothing here ever talks to the real Telegram."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeTelegram:
    TOKEN = '123456789:AAFakeTokenForTestsOnly_abcdefghijklmn0123'
    BOT = 'lyra_test_bot'

    def __init__(self, max_wait=0.25):
        self.max_wait = max_wait
        self.updates = []
        self.calls = []
        self.mode = 'ok'                    # ok | conflict
        self._update_id = 1
        self._message_id = 100
        self._cond = threading.Condition()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def reply(self, payload, status=200):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get('Content-Length') or 0)
                payload = json.loads(self.rfile.read(length) or b'{}')
                parts = self.path.strip('/').split('/')
                token, method = parts[0][3:], parts[-1]
                if token != fake.TOKEN:
                    return self.reply({'ok': False, 'error_code': 401, 'description': 'Unauthorized'}, 401)
                with fake._cond:
                    fake.calls.append((method, payload))
                if method == 'getMe':
                    return self.reply({'ok': True, 'result': {'id': 42, 'is_bot': True, 'username': fake.BOT}})
                if method == 'getUpdates':
                    if fake.mode == 'conflict':
                        return self.reply({'ok': False, 'error_code': 409, 'description': 'Conflict: terminated by other getUpdates'}, 409)
                    return self.reply({'ok': True, 'result': fake._get_updates(payload)})
                if method == 'sendMessage':
                    with fake._cond:
                        fake._message_id += 1
                        mid = fake._message_id
                    return self.reply({'ok': True, 'result': {'message_id': mid, 'chat': {'id': payload.get('chat_id')},
                                                              'text': payload.get('text')}})
                return self.reply({'ok': True, 'result': True})

        class Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        self.server = Quiet(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    # -- Bot API side -------------------------------------------------------
    def _get_updates(self, payload):
        offset, wait = payload.get('offset', 0), min(float(payload.get('timeout', 0)), self.max_wait)
        with self._cond:
            if offset == -1:
                return self.updates[-1:]
            found = [u for u in self.updates if u['update_id'] >= offset]
            if not found and wait:
                self._cond.wait(wait)
                found = [u for u in self.updates if u['update_id'] >= offset]
            return found

    # -- test side ------------------------------------------------------------
    def _push(self, update):
        with self._cond:
            update['update_id'] = self._update_id
            self._update_id += 1
            self.updates.append(update)
            self._cond.notify_all()
        return update['update_id']

    def say(self, text, chat=555, sender=None, chat_type='private', age=0):
        return self._push({'message': {'message_id': 1, 'date': int(time.time()) - age, 'text': text,
                                       'chat': {'id': chat, 'type': chat_type}, 'from': {'id': chat if sender is None else sender}}})

    def press(self, data, chat=555, sender=None):
        return self._push({'callback_query': {'id': 'cb-' + str(self._update_id), 'data': data,
                                              'from': {'id': chat if sender is None else sender},
                                              'message': {'message_id': 1, 'chat': {'id': chat}}}})

    def calls_to(self, method):
        with self._cond:
            return [payload for name, payload in self.calls if name == method]

    def sent(self, chat=None):
        return [p['text'] for p in self.calls_to('sendMessage') if chat is None or p.get('chat_id') == chat]

    def keyboards(self):
        return [p['reply_markup']['inline_keyboard'][0] for p in self.calls_to('sendMessage') if p.get('reply_markup')]

    def wait_for(self, predicate, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if predicate():
                return True
            time.sleep(0.02)
        return predicate()

    def close(self):
        self.server.shutdown()
