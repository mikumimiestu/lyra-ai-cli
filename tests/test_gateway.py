"""`amagi gateway`: the agent without a screen, driven from Telegram. Unit tests for the lock, parser and service files, plus
end-to-end runs of a real gateway process against a fake model API and a fake Telegram."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app
import spinner
from fakeapi import FakeApi
from faketelegram import FakeTelegram

ROOT = str(Path(__file__).resolve().parents[1])

LAUNCHER = r'''
import sys
sys.path.insert(0, {root!r})
import app
app.API_URL = {url!r}
app.load_config = lambda: {config!r}
app.save_config = lambda config: None
app.ensure_daemon_running = lambda: None
app.check_remote_version = lambda timeout=4.0: (False, app.VERSION)
app.get_current_system_prompt = lambda: "sistem"
app.read_memory = lambda: "- [2026-01-01 10:00] catatan uji dari memori palsu"
app.save_memory = lambda text: "tersimpan: " + text
app.GATEWAY_BEAT = 0.3
sys.argv = ["amagi", "gateway"] + {extra!r}
app.main()
'''


class GatewayDirCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-gw-')
        self.addCleanup(__import__('shutil').rmtree, self.dir, True)
        patcher = patch.dict(os.environ, {'LYRA_GATEWAY_DIR': self.dir})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_lock(self, pid, age=0.0):
        record = {'pid': pid, 'started': time.time(), 'beat': time.time() - age, 'cwd': '/x', 'version': '9'}
        Path(app.gateway_paths()['lock']).write_text(json.dumps(record))


class GatewayUnitTests(GatewayDirCase):
    def test_paths_follow_the_override(self):
        self.assertEqual(os.path.dirname(app.gateway_paths()['lock']), self.dir)
        self.assertTrue(app.gateway_paths()['log'].endswith('.amagi_gateway.log'))

    def test_state_is_only_reported_while_the_heartbeat_is_fresh(self):
        self.assertIsNone(app.gateway_state())
        self.write_lock(123)
        self.assertEqual(app.gateway_state()['pid'], 123)
        self.write_lock(123, age=app.GATEWAY_STALE + 5)
        self.assertIsNone(app.gateway_state())
        Path(app.gateway_paths()['lock']).write_text('bukan json')
        self.assertIsNone(app.gateway_state())

    def test_only_one_gateway_may_hold_the_lock_and_a_dead_one_does_not(self):
        self.write_lock(os.getpid() + 1)                      # somebody else, fresh
        lock = app.GatewayLock('/proyek')
        self.assertFalse(lock.acquire())
        self.write_lock(os.getpid() + 1, age=app.GATEWAY_STALE + 5)     # that gateway crashed long ago
        self.assertTrue(lock.acquire())
        self.addCleanup(lock.release)
        state = app.gateway_state()
        self.assertEqual((state['pid'], state['cwd']), (os.getpid(), '/proyek'))
        lock.release()
        self.assertIsNone(app.gateway_state())
        self.assertFalse(os.path.exists(app.gateway_paths()['lock']))

    def test_the_heartbeat_keeps_the_lock_fresh_and_notices_the_stop_file(self):
        with patch.object(app, 'GATEWAY_BEAT', 0.1):
            lock = app.GatewayLock('/x')
            self.assertTrue(lock.acquire())
            self.addCleanup(lock.release)
            first = app.gateway_state()['beat']
            time.sleep(0.4)
            self.assertGreater(app.gateway_state()['beat'], first)
            Path(app.gateway_paths()['stop']).write_text('stop')
            deadline = time.time() + 3
            while time.time() < deadline and spinner.LIVE.inbox.empty():
                time.sleep(0.05)
            self.assertIs(spinner.LIVE.inbox.get_nowait(), spinner._EOF)
            self.assertFalse(os.path.exists(app.gateway_paths()['stop']))

    def test_a_leftover_stop_file_does_not_kill_a_new_gateway(self):
        Path(app.gateway_paths()['stop']).write_text('stop')
        lock = app.GatewayLock('/x')
        self.assertTrue(lock.acquire())
        self.addCleanup(lock.release)
        self.assertFalse(os.path.exists(app.gateway_paths()['stop']))

    def test_input_returns_messages_and_ends_on_eof_or_ctrl_c(self):
        live = spinner.LiveState()
        reader = app.GatewayInput(live)
        live.submit(app.RemoteText('halo'))
        item = reader.read()
        self.assertEqual(item, 'halo')
        self.assertTrue(live.busy)
        live.submit_eof()
        with self.assertRaises(EOFError):
            reader.read()
        self.assertFalse(live.busy)
        with patch.object(live.inbox, 'get', side_effect=KeyboardInterrupt):
            with self.assertRaises(EOFError):
                reader.read()
        self.assertIsNone(reader.session)

    def test_the_log_never_gets_colour_codes(self):
        import io
        sink = io.StringIO()
        log = app.PlainLog(sink)
        log.write('\x1b[1mtebal\x1b[0m biasa\n')
        self.assertEqual(sink.getvalue(), 'tebal biasa\n')
        self.assertFalse(log.isatty())

    def test_start_requirements_are_explained(self):
        self.assertIn('/telegram setup', app.gateway_problem({}))
        self.assertIn('login', app.gateway_problem({'telegram_token': 't', 'telegram_chat_id': 1}))
        self.assertIsNone(app.gateway_problem({'telegram_token': 't', 'telegram_chat_id': 1, 'api_key': 'k'}))
        self.assertIsNone(app.gateway_problem({'telegram_token': 't', 'telegram_chat_id': 1, 'auth_method': 'account', 'cli_token': 'x'}))
        self.assertTrue(app.has_credentials({'api_key': 'k'}))
        self.assertFalse(app.has_credentials({'api_key': '  '}) and not os.getenv('ASTBYTE_API_KEY'))

    def test_command_line_parsing(self):
        self.assertEqual(app.parse_cli_args(['gateway'])[0]['gateway'], '')
        for sub in ('status', 'stop', 'install', 'run'):
            self.assertEqual(app.parse_cli_args(['gateway', sub])[0]['gateway'], sub)
        options, error = app.parse_cli_args(['gateway', '--cwd', '/proyek'])
        self.assertEqual((options['gateway'], options['cwd'], error), ('', '/proyek', None))
        self.assertEqual(app.parse_cli_args(['gateway', '--cwd=/a b'])[0]['cwd'], '/a b')
        self.assertIn('tidak dikenal', app.parse_cli_args(['gateway', 'nonsense'])[1])
        self.assertIsNone(app.parse_cli_args(['-p', 'tanya'])[0]['gateway'])
        self.assertIn('tidak dikenal', app.parse_cli_args(['--gateway'])[1])

    def test_help_mentions_the_gateway(self):
        self.assertIn('amagi gateway', app.CLI_HELP)
        self.assertIn('LYRA_GATEWAY_DIR', app.CLI_HELP)

    def test_service_files_per_operating_system(self):
        path, content, commands = app.gateway_service_plan('darwin')
        self.assertTrue(path.endswith('id.astbyte.amagi-gateway.plist'))
        for needle in ('RunAtLoad', 'KeepAlive', '<string>gateway</string>', sys.executable):
            self.assertIn(needle, content)
        self.assertIn('launchctl load', commands[0])
        path, content, commands = app.gateway_service_plan('linux')
        self.assertTrue(path.endswith('amagi-gateway.service'))
        self.assertIn(f'ExecStart={sys.executable}', content)
        self.assertIn('gateway', content)
        self.assertIn('Restart=on-failure', content)
        self.assertTrue(any('enable-linger' in c for c in commands))
        path, content, commands = app.gateway_service_plan('win32')
        self.assertIsNone(path)
        self.assertIn('schtasks /Create', commands[0])
        self.assertIn('ONLOGON', commands[0])
        self.assertIn('gateway', commands[0])

    def test_install_prints_the_plan_and_only_writes_after_a_yes(self):
        import contextlib
        import io
        target = os.path.join(self.dir, 'unit.service')
        plan = (target, 'ISI-LAYANAN\n', ['systemctl --user enable --now amagi-gateway'])
        out = io.StringIO()
        with patch.object(app, 'gateway_service_plan', return_value=plan), contextlib.redirect_stdout(out), \
             patch.object(sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='n'):
            self.assertEqual(app.gateway_command('install'), 0)
        self.assertFalse(os.path.exists(target))
        self.assertIn('ISI-LAYANAN', out.getvalue())
        self.assertIn('systemctl --user enable', out.getvalue())
        with patch.object(app, 'gateway_service_plan', return_value=plan), contextlib.redirect_stdout(io.StringIO()), \
             patch.object(sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='y'):
            app.gateway_command('install')
        self.assertEqual(Path(target).read_text(), 'ISI-LAYANAN\n')

    def test_status_and_stop_without_a_gateway(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(app.gateway_command('status'), 1)
            self.assertEqual(app.gateway_command('stop'), 1)
        self.assertIn('tidak berjalan', out.getvalue())
        self.write_lock(4242)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(app.gateway_command('status'), 0)
        self.assertIn('pid 4242', out.getvalue())

    def test_unknown_subcommand(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(app.gateway_command('terbang'), 2)


class GatewayProcessTests(GatewayDirCase):
    """A real `amagi gateway` process (no terminal at all) talking to fake services."""

    def setUp(self):
        super().setUp()
        self.api = FakeApi()
        self.fake = FakeTelegram()
        self.addCleanup(self.api.close)
        self.addCleanup(self.fake.close)
        self.work = tempfile.mkdtemp(prefix='lyra-gw-work-')
        self.addCleanup(__import__('shutil').rmtree, self.work, True)
        self.processes = []
        self.addCleanup(self.kill_all)

    def kill_all(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(5)
            for stream in (process.stdout, process.stderr):
                if stream:
                    stream.close()

    def start(self, paired=True, extra=None, wait=True, env=None):
        config = {'api_key': 'test', 'model_index': 2, 'reasoning_effort': 'medium'}
        if paired:
            config.update({'telegram_token': FakeTelegram.TOKEN, 'telegram_bot': FakeTelegram.BOT,
                           'telegram_chat_id': 555, 'telegram_enabled': True})
        script = os.path.join(self.dir, f'launch{len(self.processes)}.py')
        Path(script).write_text(LAUNCHER.format(root=ROOT, url=self.api.url, config=config, extra=extra or []))
        env = dict(os.environ, LYRA_TELEGRAM_API=self.fake.url, LYRA_GATEWAY_DIR=self.dir,
                   LYRA_SESSIONS_DIR=os.path.join(self.dir, 'sessions'), LYRA_INBOX_DIR=os.path.join(self.dir, 'masuk'),
                   PYTHONIOENCODING='utf-8', **(env or {}))
        process = subprocess.Popen([sys.executable, script], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env, cwd=self.work)
        self.processes.append(process)
        if wait:
            self.assertTrue(self.fake.wait_for(lambda: app.gateway_state() is not None, 15), self.output(process))
            self.assertTrue(self.fake.wait_for(lambda: self.fake.calls_to('getUpdates'), 10), self.output(process))
            time.sleep(0.7)               # the bridge drops its backlog first
        return process

    def output(self, process):
        if process.poll() is not None:
            return process.stdout.read() + process.stderr.read()
        return '(still running)'

    def log(self):
        try:
            return Path(app.gateway_paths()['log']).read_text(encoding='utf-8')
        except OSError:
            return ''

    def ask(self, text, expect, timeout=12):
        before = len(self.fake.sent(555))
        self.fake.say(text)
        self.assertTrue(self.fake.wait_for(lambda: any(expect in t for t in self.fake.sent(555)[before:]), timeout),
                        (text, self.fake.sent(555)[before:], self.log()[-600:]))
        return [t for t in self.fake.sent(555)[before:] if expect in t][0]

    def test_a_message_from_the_phone_is_answered_and_the_log_stays_clean(self):
        process = self.start()
        self.ask('halo dari hp', 'Halo! Ini')
        log = self.log()
        self.assertIn('gateway mulai', log)
        self.assertNotIn('\x1b', log)
        self.assertNotIn(FakeTelegram.TOKEN, log)
        state = app.gateway_state()
        self.assertEqual(os.path.realpath(state['cwd']), os.path.realpath(self.work))
        self.assertIsNone(process.poll())

    def test_work_that_needs_permission_waits_for_the_buttons(self):
        self.start()
        self.fake.say('tolong tulis sesuatu')
        self.assertTrue(self.fake.wait_for(lambda: self.fake.keyboards(), 12), self.log()[-500:])
        self.assertIn('echo halo-dari-tool', [t for t in self.fake.sent(555) if 'Izin diperlukan' in t][0])
        self.fake.press(self.fake.keyboards()[0][0]['callback_data'])
        self.assertTrue(self.fake.wait_for(lambda: any('Ada dua berkas' in t for t in self.fake.sent(555)), 12))
        self.assertIn('🔧 menjalankan 1', [t for t in self.fake.sent(555) if 'Ada dua berkas' in t][0])

    def test_phone_commands_work_without_any_terminal(self):
        self.start()
        self.assertIn('mode gateway', self.ask('/status', 'mode gateway'))
        self.assertIn('API key', self.ask('/kuota', 'API key'))
        self.assertIn('Orpheus', self.ask('/model', 'Model:'))
        self.assertIn('✓ Model:', self.ask('/model 1', '✓ Model:'))
        self.ask('/model 3', '✓ Model:')                        # a model that supports reasoning
        self.assertIn('✓ Penalaran: low', self.ask('/reasoning low', '✓ Penalaran'))
        self.assertIn('Pilihan: low atau medium', self.ask('/reasoning ekstrem', 'Pilihan'))
        self.assertIn('Nomor model tidak valid', self.ask('/model 99', 'tidak valid'))
        self.assertIn(os.path.realpath(self.work), os.path.realpath(self.ask('/pwd', '📁').replace('📁 ', '')))
        sub = os.path.join(self.work, 'sub')
        os.mkdir(sub)
        Path(sub, 'isi.txt').write_text('x')
        self.ask('/cd sub', 'Folder aktif')
        self.assertIn('isi.txt', self.ask('/ls', 'isi.txt'))
        self.assertIn('Folder tidak ditemukan', self.ask('/cd tidak-ada', 'tidak ditemukan'))
        self.ask('/todos', 'Belum ada daftar tugas')
        self.assertIn('catatan uji dari memori palsu', self.ask('/memori', 'Memori ('))
        self.assertIn('tersimpan: beli susu', self.ask('/ingat beli susu', 'tersimpan'))
        self.ask('/undo', 'Belum ada perubahan')
        self.ask('/compact', 'masih pendek')
        self.ask('/waktu', '202')
        self.ask('/versi', f'v{app.VERSION}')
        self.ask('/login', 'hanya tersedia di terminal')

    def test_new_starts_a_fresh_conversation(self):
        self.start()
        self.ask('halo', 'Halo! Ini')
        self.ask('/new', '🆕')
        self.ask('/compact', 'masih pendek')                  # nothing is left to summarise after /new
        self.ask('halo lagi', 'Halo! Ini')
        sessions = os.listdir(os.path.join(self.dir, 'sessions'))
        self.assertGreaterEqual(len(sessions), 2)

    def test_stop_command_ends_the_gateway_cleanly_and_tells_the_phone(self):
        process = self.start()
        out = []
        threading.Thread(target=lambda: out.append(app.gateway_command('stop')), daemon=True).start()
        self.assertTrue(self.fake.wait_for(lambda: process.poll() is not None, 15))
        self.assertEqual(process.returncode, 0)
        self.assertTrue(self.fake.wait_for(lambda: any('Gateway Lyra dihentikan' in t for t in self.fake.sent(555)), 5))
        self.assertIsNone(app.gateway_state())
        self.assertIn('gateway berhenti', self.log())
        self.assertIn('Gateway berhenti.', process.stdout.read())

    @unittest.skipIf(os.name == 'nt', 'SIGINT is POSIX')
    def test_ctrl_c_at_idle_ends_the_gateway(self):
        process = self.start()
        process.send_signal(signal.SIGINT)
        self.assertTrue(self.fake.wait_for(lambda: process.poll() is not None, 10))
        self.assertEqual(process.returncode, 0)

    def test_a_second_gateway_is_refused_and_the_first_keeps_working(self):
        first = self.start()
        second = self.start(wait=False)
        self.assertTrue(self.fake.wait_for(lambda: second.poll() is not None, 15))
        self.assertEqual(second.returncode, 1)
        self.assertIn('sudah berjalan', second.stderr.read())
        self.assertIsNone(first.poll())
        self.ask('halo', 'Halo! Ini')

    def test_without_pairing_it_refuses_to_start(self):
        process = self.start(paired=False, wait=False)
        self.assertTrue(self.fake.wait_for(lambda: process.poll() is not None, 15))
        self.assertEqual(process.returncode, 2)
        self.assertIn('/telegram setup', process.stderr.read())
        self.assertIsNone(app.gateway_state())

    def test_a_crashed_gateways_stale_lock_does_not_block_a_new_one(self):
        self.write_lock(999999, age=app.GATEWAY_STALE + 10)
        process = self.start()
        self.assertEqual(app.gateway_state()['pid'], process.pid)

    def tool_call(self, name, **arguments):
        return '<tool_call>' + json.dumps({'name': name, 'arguments': arguments}) + '</tool_call>'

    def test_a_file_from_the_phone_is_read_by_lyra(self):
        self.start()
        self.fake.send_document('catatan.txt', 'Rapat: anggaran naik 15 persen.\n'.encode(), caption='ringkas ini')
        self.assertTrue(self.fake.wait_for(lambda: self.api.requests, 12), self.log()[-500:])
        sent_to_model = self.api.requests[-1]['messages'][-1]['content']
        self.assertIn('ringkas ini', sent_to_model)
        self.assertIn('Rapat: anggaran naik 15 persen.', sent_to_model)             # the file's text reached the model
        self.assertTrue(self.fake.wait_for(lambda: any('Halo! Ini' in t for t in self.fake.sent(555)), 12))
        self.assertEqual(len(os.listdir(os.path.join(self.dir, 'masuk'))), 1)

    def test_lyra_sends_a_file_to_the_phone_only_after_the_tap(self):
        Path(self.work, 'hasil.txt').write_text('hasil akhir\n')
        call = self.tool_call('send_file', filepath='hasil.txt', caption='Ini hasilnya')
        self.api.custom.append((lambda last: 'kirim berkas' in last, [('Saya kirim.\n', 0.02), (call, 0.02)]))
        self.start()
        self.fake.say('tolong kirim berkas hasil ke hp')
        self.assertTrue(self.fake.wait_for(lambda: self.fake.keyboards(), 12), self.log()[-500:])
        self.assertIn('Kirim File', [t for t in self.fake.sent(555) if 'Izin diperlukan' in t][0])
        self.assertEqual(self.fake.uploads, [])
        self.fake.press(self.fake.keyboards()[0][0]['callback_data'])
        self.assertTrue(self.fake.wait_for(lambda: self.fake.uploads, 12), self.log()[-500:])
        upload = self.fake.uploads[0]
        self.assertEqual((upload['filename'], upload['content'], upload['fields']['caption']), ('hasil.txt', b'hasil akhir\n', 'Ini hasilnya'))
        self.assertTrue(self.fake.wait_for(lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 12))

    def test_a_secret_file_is_refused_without_even_asking_the_phone(self):
        Path(self.work, '.env').write_text('TOKEN=rahasia\n')
        call = self.tool_call('send_file', filepath='.env')
        self.api.custom.append((lambda last: 'kirim rahasia' in last, [('Saya kirim.\n', 0.02), (call, 0.02)]))
        self.start()
        self.fake.say('kirim rahasia ke hp')
        self.assertTrue(self.fake.wait_for(lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 12), self.log()[-500:])
        self.assertEqual(self.fake.keyboards(), [])
        self.assertEqual(self.fake.uploads, [])
        self.assertTrue(any('tidak boleh dikirim' in r['messages'][-1]['content'] for r in self.api.requests))

    def test_lyra_reads_a_web_page_after_the_phone_allows_the_site(self):
        from test_fetch_url import Handler
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        Handler.hits.clear()                                  # the handler's log is shared with the fetch_url tests
        url = f'http://127.0.0.1:{server.server_address[1]}/page'
        call = self.tool_call('fetch_url', url=url)
        self.api.custom.append((lambda last: 'buka halaman' in last, [('Saya buka.\n', 0.02), (call, 0.02)]))
        self.start(env={'LYRA_ALLOW_PRIVATE_URLS': '1'})
        self.fake.say('tolong buka halaman itu')
        self.assertTrue(self.fake.wait_for(lambda: self.fake.keyboards(), 12), self.log()[-500:])
        question = [t for t in self.fake.sent(555) if 'Izin diperlukan' in t][0]
        self.assertIn('Buka Situs', question)
        self.assertIn('127.0.0.1', question)
        self.assertEqual(Handler.hits, [])                                         # not requested before the tap
        self.fake.press(self.fake.keyboards()[0][0]['callback_data'])
        self.assertTrue(self.fake.wait_for(lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 12), self.log()[-500:])
        page_text = self.api.requests[-1]['messages'][-1]['content']
        self.assertIn('Bagian Satu', page_text)
        self.assertIn('tidak tepercaya', page_text)

    def test_the_local_machine_cannot_be_opened_by_default(self):
        call = self.tool_call('fetch_url', url='http://127.0.0.1:8123/admin')
        self.api.custom.append((lambda last: 'buka lokal' in last, [('Saya buka.\n', 0.02), (call, 0.02)]))
        self.start()
        self.fake.say('tolong buka lokal')
        self.assertTrue(self.fake.wait_for(lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 12), self.log()[-500:])
        self.assertEqual(self.fake.keyboards(), [])
        self.assertTrue(any('jaringan lokal' in r['messages'][-1]['content'] or 'Port 8123' in r['messages'][-1]['content']
                            for r in self.api.requests))

    def test_cwd_option_sets_the_working_folder(self):
        folder = os.path.join(self.work, 'proyek')
        os.mkdir(folder)
        self.start(extra=['--cwd', folder])
        self.assertIn('proyek', self.ask('/pwd', '📁'))
        self.assertEqual(os.path.realpath(app.gateway_state()['cwd']), os.path.realpath(folder))
        process = self.start(extra=['--cwd', os.path.join(self.work, 'tidak-ada')], wait=False)
        self.assertTrue(self.fake.wait_for(lambda: process.poll() is not None, 15))
        self.assertEqual(process.returncode, 2)                 # a missing folder is a usage error, checked before the lock


if __name__ == '__main__':
    unittest.main()
