"""A stand-in for the Telegram Bot API, just enough for the bridge: getMe, getUpdates (long poll), sendMessage,
editMessageText, answerCallbackQuery and sendChatAction. Nothing here ever talks to the real Telegram."""
import email
import email.policy
import json
import threading
import time
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeTelegram:
    TOKEN = '123456789:AAFakeTokenForTestsOnly_abcdefghijklmn0123'
    BOT = 'lyra_test_bot'

    def __init__(self, max_wait=0.25):
        self.max_wait = max_wait
        self.updates = []
        self.calls = []
        self.mode = 'ok'                    # ok | conflict
        self.files = {}                     # file_id -> (file_path, bytes) the bot may download
        self.uploads = []                   # what the bot sent with sendDocument / sendPhoto
        self.send_fails = False             # make uploads fail
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

            def do_GET(self):
                parts = unquote(self.path).strip('/').split('/', 2)          # file/bot<token>/<path>
                if len(parts) < 3 or parts[0] != 'file' or parts[1][3:] != fake.TOKEN:
                    return self.reply({'ok': False, 'error_code': 404, 'description': 'Not Found'}, 404)
                for path, data in fake.files.values():
                    if path == parts[2]:
                        self.send_response(200)
                        self.send_header('Content-Length', str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                self.reply({'ok': False, 'error_code': 404, 'description': 'Not Found'}, 404)

            def do_POST(self):
                length = int(self.headers.get('Content-Length') or 0)
                raw = self.rfile.read(length) or b'{}'
                content_type = self.headers.get('Content-Type') or ''
                parts = self.path.strip('/').split('/')
                token, method = parts[0][3:], parts[-1]
                if content_type.startswith('multipart/'):
                    message = email.message_from_bytes(b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + raw,
                                                      policy=email.policy.default)
                    payload, upload = {}, {'method': method}
                    for part in message.iter_parts():
                        name = part.get_param('name', header='content-disposition')
                        if part.get_filename():
                            upload.update(field=name, filename=part.get_filename(), content=part.get_payload(decode=True))
                        else:
                            payload[name] = part.get_payload(decode=True).decode()
                    upload['fields'] = payload
                else:
                    payload, upload = json.loads(raw), None
                if token != fake.TOKEN:
                    return self.reply({'ok': False, 'error_code': 401, 'description': 'Unauthorized'}, 401)
                with fake._cond:
                    fake.calls.append((method, payload))
                if upload is not None:
                    if fake.send_fails:
                        return self.reply({'ok': False, 'error_code': 400, 'description': 'Bad Request: chat not found'}, 400)
                    fake.uploads.append(upload)
                    return self.reply({'ok': True, 'result': {'message_id': 900 + len(fake.uploads)}})
                if method == 'getFile':
                    entry = fake.files.get(payload.get('file_id'))
                    if not entry:
                        return self.reply({'ok': False, 'error_code': 400, 'description': 'Bad Request: wrong file_id'}, 400)
                    return self.reply({'ok': True, 'result': {'file_id': payload['file_id'], 'file_path': entry[0]}})
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

    def send_document(self, name, content, caption=None, chat=555, sender=None, declared_size=None, age=0):
        file_id = f'doc-{len(self.files) + 1}'
        self.files[file_id] = (f'documents/{file_id}.bin', content)         # the name only travels in file_name, as in the real API
        message = {'message_id': 1, 'date': int(time.time()) - age, 'chat': {'id': chat, 'type': 'private'},
                   'from': {'id': chat if sender is None else sender},
                   'document': {'file_id': file_id, 'file_name': name, 'file_size': declared_size if declared_size is not None else len(content)}}
        if caption:
            message['caption'] = caption
        return self._push({'message': message})

    def send_photo(self, content, caption=None, chat=555):
        file_id = f'photo-{len(self.files) + 1}'
        self.files[file_id] = (f'photos/{file_id}.jpg', content)
        message = {'message_id': 1, 'date': int(time.time()), 'chat': {'id': chat, 'type': 'private'}, 'from': {'id': chat},
                   'photo': [{'file_id': 'small', 'file_size': 10}, {'file_id': file_id, 'file_size': len(content)}]}
        if caption:
            message['caption'] = caption
        return self._push({'message': message})

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
