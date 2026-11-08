import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app
import spinner as sp
import styling
import tools


class ParseTests(unittest.TestCase):
    def parse(self, *argv):
        return app.parse_cli_args(list(argv))

    def test_known_flags(self):
        self.assertTrue(self.parse('--version')[0]['version'])
        self.assertTrue(self.parse('-V')[0]['version'])
        self.assertTrue(self.parse('-h')[0]['help'])
        self.assertTrue(self.parse('--continue')[0]['continue'])
        self.assertTrue(self.parse('-c')[0]['continue'])
        self.assertTrue(self.parse('--daemon')[0]['daemon'])
        self.assertTrue(self.parse('daemon')[0]['daemon'])        # how the reminder daemon is spawned

    def test_print_takes_an_optional_question(self):
        opts, error = self.parse('-p', 'apa kabar')
        self.assertEqual((opts['print_given'], opts['print'], error), (True, 'apa kabar', None))
        opts, _ = self.parse('--print=halo dunia')
        self.assertEqual((opts['print_given'], opts['print']), (True, 'halo dunia'))
        opts, _ = self.parse('-p')                                   # question may come from stdin
        self.assertEqual((opts['print_given'], opts['print']), (True, None))
        opts, _ = self.parse('-p', '-c')
        self.assertEqual((opts['print'], opts['continue']), (None, True))

    def test_unknown_options_and_stray_words_are_errors(self):
        for argv in (['--bogus'], ['-z'], ['hello'], ['-c', 'oops']):
            opts, error = self.parse(*argv)
            self.assertIn('tidak dikenal', error, argv)
        self.assertIn('amagi -p', self.parse('hello')[1])           # nudges towards -p for plain words
        self.assertNotIn('amagi -p', self.parse('--bogus')[1])


class MainFlagTests(unittest.TestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch.object(sys, 'argv', ['amagi', *argv]), \
             patch.object(app, 'load_config', side_effect=AssertionError('flags must not touch the config')), \
             patch.object(app, 'run_print_mode', return_value=0) as printer:
            try:
                app.main()
            except SystemExit as exit_:
                code = exit_.code
        return out.getvalue(), err.getvalue(), code, printer

    def test_version_and_help_exit_without_side_effects(self):
        out, _, code, _ = self.run_main('--version')
        self.assertEqual((out.strip(), code), ('Lyra CLI v' + app.VERSION, None))
        out, _, code, _ = self.run_main('--help')
        for expected in ('amagi -p', '--continue', 'stdout', 'stderr', 'Kode keluar', '/help <perintah>', 'ASTBYTE_API_KEY'):
            self.assertIn(expected, out)

    def test_unknown_option_exits_with_status_two(self):
        out, err, code, _ = self.run_main('--bogus')
        self.assertEqual((out, code), ('', 2))
        self.assertIn('--bogus', err)

    def test_print_flag_hands_the_question_over(self):
        _, _, code, printer = self.run_main('-p', 'apa itu docker?')
        printer.assert_called_once_with('apa itu docker?')
        self.assertEqual(code, 0)


class PrintModeTests(unittest.TestCase):
    CONFIG = {'api_key': 'k', 'model_index': 2, 'reasoning_effort': 'medium'}

    def run_mode(self, question, replies, stdin_text='', config=None, env=None):
        """replies: list of (status, text, tool_text) returned by the stubbed API, in order."""
        sent = []

        def fake(headers, data):
            sent.append(json.loads(json.dumps(data)))
            return replies[min(len(sent), len(replies)) - 1]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            stack.enter_context(patch.dict(os.environ, dict({'ASTBYTE_API_KEY': ''}, **(env or {}))))
            stack.enter_context(patch.object(app, 'load_config', return_value=dict(self.CONFIG if config is None else config)))
            stack.enter_context(patch.object(app, 'save_config'))
            stack.enter_context(patch.object(app, 'get_current_system_prompt', return_value='sistem'))
            stack.enter_context(patch.object(app, '_collect_stream', side_effect=fake))
            stack.enter_context(patch.dict(app.BILLING_STATE, {'balance': False, 'notified': False}))
            code = app.run_print_mode(question, stdin_text=stdin_text)
        return code, out.getvalue(), err.getvalue(), sent

    def test_answer_goes_to_stdout_only(self):
        code, out, err, sent = self.run_mode('apa kabar?', [(200, 'Baik, terima kasih.', '')])
        self.assertEqual((code, out, err), (0, 'Baik, terima kasih.\n', ''))
        self.assertEqual(sent[0]['model'], 'lyra-orpheus-6')
        self.assertIn('MODE NON-INTERAKTIF', sent[0]['messages'][0]['content'])
        self.assertEqual(sent[0]['messages'][1]['content'], 'apa kabar?')

    def test_stdin_is_added_as_context_and_can_be_the_whole_question(self):
        _, _, _, sent = self.run_mode('ringkas', [(200, 'ok', '')], stdin_text='isi berkas\nbaris dua')
        self.assertIn('[Masukan dari stdin]\nisi berkas\nbaris dua', sent[0]['messages'][1]['content'])
        self.assertTrue(sent[0]['messages'][1]['content'].startswith('ringkas'))
        code, out, _, sent = self.run_mode(None, [(200, 'ok', '')], stdin_text='hanya stdin')
        self.assertEqual(code, 0)
        self.assertIn('hanya stdin', sent[0]['messages'][1]['content'])
        big = 'x' * (app.PRINT_MODE_STDIN_LIMIT + 10)
        _, _, _, sent = self.run_mode('q', [(200, 'ok', '')], stdin_text=big)
        self.assertIn('[dipotong]', sent[0]['messages'][1]['content'])

    def test_missing_question_or_login_is_a_usage_error(self):
        code, out, err, sent = self.run_mode('  ', [(200, 'x', '')])
        self.assertEqual((code, out, sent), (2, '', []))
        self.assertIn('Tidak ada pertanyaan', err)
        code, out, err, sent = self.run_mode('halo', [(200, 'x', '')], config={})
        self.assertEqual((code, out, sent), (2, '', []))
        self.assertIn('Belum masuk', err)
        code, *_ = self.run_mode('halo', [(200, 'x', '')], config={}, env={'ASTBYTE_API_KEY': 'dari-env'})
        self.assertEqual(code, 0)

    def call(self, name, **arguments):
        return '<tool_call>' + json.dumps({'name': name, 'arguments': arguments}) + '</tool_call>'

    def test_read_tools_run_and_their_result_reaches_the_model(self):
        with patch.object(app, 'read_file', return_value='isi README') as reader:
            code, out, _, sent = self.run_mode('baca README', [(200, 'Saya baca.', self.call('read_file', filepath='README.md')),
                                                                (200, 'Isinya README.', '')])
        self.assertEqual((code, out), (0, 'Isinya README.\n'))
        reader.assert_called_once_with('README.md')
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[1]['messages'][-1]['content'], "[Hasil Tool 'read_file']\nisi README")

    def test_writing_and_running_are_refused(self):
        for name, arguments in (('write_file', {'filepath': 'x', 'content': 'y'}), ('edit_file', {'filepath': 'x', 'old': 'a', 'new': 'b'}),
                                ('execute_command', {'command': 'rm -rf /'}), ('save_memory', {'content': 'x'})):
            with self.subTest(name), patch.object(app, 'write_file') as w, patch.object(app, 'edit_file') as e, \
                 patch.object(app, 'execute_command') as x, patch.object(app, 'tool_save_memory') as m:
                code, out, _, sent = self.run_mode('ubah', [(200, '', self.call(name, **arguments)), (200, 'Tidak bisa.', '')])
            for spy in (w, e, x, m):
                spy.assert_not_called()
            self.assertEqual((code, out), (0, 'Tidak bisa.\n'))
            self.assertIn('Ditolak', sent[1]['messages'][-1]['content'])

    def test_failures_use_stderr_and_nonzero_codes(self):
        cases = [((401, 'x', ''), 1, '[401]'), ((500, 'galat server', ''), 1, 'galat server'), ((0, 'Error: putus', ''), 1, 'putus'),
                 ((200, '   ', ''), 1, 'tanpa jawaban')]
        for reply, expected, text in cases:
            code, out, err, _ = self.run_mode('halo', [reply])
            self.assertEqual((code, out), (expected, ''), reply)
            self.assertIn(text, err)
        quota = (429, json.dumps({'error': {'message': 'Kuota habis.', 'resets_in_seconds': 3600}}), '')
        with patch.object(app, 'uses_account_login', return_value=True):
            code, _, err, _ = self.run_mode('halo', [quota])
        self.assertEqual(code, 1)
        self.assertIn('Kuota habis.', err)

    def test_runaway_tool_loops_stop_and_interrupts_return_130(self):
        loop = (200, '', self.call('get_system_time'))
        code, out, err, sent = self.run_mode('halo', [loop])
        self.assertEqual((code, out), (1, ''))
        self.assertEqual(len(sent), app.PRINT_MODE_MAX_STEPS)
        self.assertIn('Terlalu banyak langkah', err)
        with patch.object(app, '_collect_stream', side_effect=KeyboardInterrupt), \
             patch.object(app, 'load_config', return_value=dict(self.CONFIG)), patch.object(app, 'get_current_system_prompt', return_value='s'):
            self.assertEqual(app.run_print_mode('halo', stdin_text=''), 130)

    def test_balance_billing_is_mentioned_once_on_stderr(self):
        def fake_collect(headers, data):
            app.BILLING_STATE['balance'] = True
            return 200, 'jawab', ''
        with patch.object(app, '_collect_stream', side_effect=fake_collect), patch.dict(app.BILLING_STATE, {'balance': False, 'notified': False}), \
             patch.object(app, 'load_config', return_value=dict(self.CONFIG)), patch.object(app, 'get_current_system_prompt', return_value='s'), \
             contextlib.redirect_stdout(io.StringIO()):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                app.run_print_mode('halo', stdin_text='')
        self.assertEqual(err.getvalue().count('saldo developer'), 1)


class RealProcessTests(unittest.TestCase):
    """The actual command, as a separate process, against the fake streaming API."""

    def setUp(self):
        try:
            from ptyrun import FakeApi, run_cli
        except ImportError:
            self.skipTest('needs tests/ptyrun.py')
        self.api, self.run = FakeApi(), run_cli
        self.addCleanup(self.api.close)

    def test_version_help_and_errors(self):
        done = self.run(['--version'], self.api.url)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, 'Lyra CLI v' + app.VERSION))
        done = self.run(['--help'], self.api.url)
        self.assertIn('amagi -p', done.stdout)
        done = self.run(['--nope'], self.api.url)
        self.assertEqual((done.returncode, done.stdout), (2, ''))
        self.assertIn('--nope', done.stderr)
        self.assertEqual(self.api.requests, [])

    def test_print_mode_answers_reads_files_and_pipes(self):
        self.api.custom.append((lambda last: last == 'Lyra, cek folder', [('<tool_call>{"name": "get_system_time", "arguments": {}}</tool_call>', 0.01)]))
        done = self.run(['-p', 'halo'], self.api.url)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('Halo! Ini', done.stdout)
        self.assertNotIn('\x1b', done.stdout)                        # plain text, safe to pipe
        self.assertNotIn('●', done.stdout)
        done = self.run(['-p', 'ringkas'], self.api.url, stdin='teks dari pipa')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('teks dari pipa', json.dumps(self.api.requests[-1]['messages']))
        done = self.run(['-p', 'Lyra, cek folder'], self.api.url)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('Selesai membaca', done.stdout)                 # a read tool ran, then the final answer

    def test_nothing_is_saved_or_started_in_print_mode(self):
        done = self.run(['-p', 'halo'], self.api.url)
        self.assertEqual(done.returncode, 0)
        from ptyrun import SESSIONS_FOR_TESTS
        self.assertEqual([n for n in os.listdir(SESSIONS_FOR_TESTS) if n.endswith('.json')], [])


class QuotaFooterTests(unittest.TestCase):
    def setUp(self):
        self.monitor = app.QuotaMonitor()
        self.login = patch.object(app, 'uses_account_login', return_value=True)
        self.login.start()
        self.addCleanup(self.login.stop)
        patcher = patch.dict(app.BILLING_STATE, {'balance': False, 'notified': False})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_percent_text_and_missing_data(self):
        self.assertEqual(self.monitor.footer({}), (None, None))
        self.monitor.update({'limit': 20000, 'used': 7600, 'remaining': 12400})
        self.assertEqual(self.monitor.footer({}), ('sisa kuota 62%', 62))
        self.monitor.update({'limit': 20000, 'remaining': -5})
        self.assertEqual(self.monitor.footer({})[1], 0)
        self.monitor.update({'limit': 0, 'remaining': 0})
        self.assertEqual(self.monitor.footer({}), (None, None))

    def test_balance_billing_replaces_the_percentage(self):
        self.monitor.update({'limit': 100, 'remaining': 0})
        app.BILLING_STATE['balance'] = True
        self.assertEqual(self.monitor.footer({}), ('saldo developer', 20))

    def test_nothing_is_shown_without_an_account_login(self):
        self.monitor.update({'limit': 100, 'remaining': 50})
        self.login.stop()
        with patch.object(app, 'uses_account_login', return_value=False):
            self.assertEqual(self.monitor.footer({}), (None, None))
            self.monitor.refresh({})
            self.assertIsNone(self.monitor.data)
        self.login.start()

    def test_refresh_runs_in_the_background_and_is_throttled(self):
        import threading
        gate, calls = threading.Event(), []

        def slow(config):
            calls.append(1)
            gate.wait(2)
            return {'limit': 100, 'remaining': 40}
        with patch.object(app, 'fetch_quota', side_effect=slow):
            self.monitor.refresh({}, force=True)                     # returns at once while the fetch is blocked
            self.monitor.refresh({}, force=True)                     # already running: ignored
            gate.set()
            for _ in range(50):
                if self.monitor.data:
                    break
                __import__('time').sleep(0.02)
            self.assertEqual(self.monitor.data['remaining'], 40)
            self.monitor.refresh({})                                 # inside the throttle window: no new request
            __import__('time').sleep(0.05)
        self.assertEqual(len(calls), 1)

    def test_failed_refresh_keeps_the_last_reading(self):
        self.monitor.update({'limit': 100, 'remaining': 70})
        with patch.object(app, 'fetch_quota', return_value=None):
            self.monitor.refresh({}, force=True)
            __import__('time').sleep(0.1)
        self.assertEqual(self.monitor.remaining_percent(), 70)


class FooterRenderTests(unittest.TestCase):
    def editor(self, context, live=None):
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        pipe = stack.enter_context(create_pipe_input())
        return styling.TerminalInput(lambda: context, input_stream=pipe, output_stream=DummyOutput(), live=live)

    BASE = dict(model='Lyra Orpheus 6', effort='medium', directory='/work', approval='ask')

    def test_quota_text_sits_next_to_the_context_figure(self):
        text = styling.strip_ansi(self.editor(dict(self.BASE, context_pct=12, quota='sisa kuota 62%', quota_pct=62))._toolbar().value)
        self.assertIn('ctx ~12% · sisa kuota 62%', text)
        self.assertNotIn('quota_pct', text)
        self.assertNotIn('kuota', styling.strip_ansi(self.editor(dict(self.BASE, context_pct=12))._toolbar().value))

    @unittest.skipUnless(styling.USE_COLOR, 'colours need a terminal')
    def test_low_quota_turns_the_footer_yellow_then_red(self):
        for pct, colour in ((62, styling.COLOR_DIM), (25, styling.YELLOW), (10, styling.RED)):
            raw = self.editor(dict(self.BASE, quota='x', quota_pct=pct))._toolbar().value
            self.assertTrue(raw.startswith('  ' + colour), (pct, raw[:20]))

    def test_queued_messages_are_counted_in_the_second_line(self):
        live = sp.LiveState()
        editor = self.editor(dict(self.BASE), live=live)
        self.assertNotIn('antre', styling.strip_ansi(editor._toolbar().value))
        live.inbox.put('satu')
        live.inbox.put('dua')
        second = styling.strip_ansi(editor._toolbar().value).splitlines()[1]
        self.assertIn('tanya dulu (Shift+Tab ganti) · 2 pesan antre', second)      # narrow footers keep this, drop the hints

    def test_toolbar_text_accepts_a_quota_label(self):
        self.assertIn('sisa kuota 5%', styling.toolbar_text('Lyra Orpheus 6', 'medium', '/w', quota='sisa kuota 5%'))


class HelpTopicTests(unittest.TestCase):
    def render(self, topic=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            app.render_help(topic)
        return styling.strip_ansi(out.getvalue())

    def test_every_listed_command_has_details(self):
        for name, description in styling.COMMANDS:
            info = styling.COMMAND_DETAILS.get(name)
            self.assertIsNotNone(info, name)
            for key in ('usage', 'desc', 'examples') if name not in ('/cd', '/ls') else ('usage', 'desc', 'examples'):
                self.assertTrue(info.get(key), (name, key))
            self.assertTrue(info['usage'].startswith(name), name)
        self.assertEqual(set(styling.COMMAND_ALIASES.values()) - set(styling.COMMAND_DETAILS), set())

    def test_names_and_aliases_resolve(self):
        for text, expected in (('model', '/model'), ('/model', '/model'), ('MODE', '/mode'), ('/mem', '/memory'), ('jam', '/time'),
                               ('/effort', '/reasoning'), ('quota', '/kuota'), ('/', '/help'), ('v', '/version'), ('todo', '/todos')):
            self.assertEqual(styling.resolve_command(text), expected, text)
        for text in ('', 'zzz', '/modl'):
            self.assertIsNone(styling.resolve_command(text))

    def test_topic_page_shows_usage_examples_aliases_and_notes(self):
        page = self.render('mode')
        for expected in ('/mode', 'Pemakaian   /mode [ask|edit|all]', 'Contoh', '/mode edit', 'Catatan', 'meminta izin'):
            self.assertIn(expected, page)
        self.assertIn('Alias       /mem', self.render('/memory'))
        self.assertLess(max(len(line) for line in self.render('compact').splitlines()), 120)

    def test_unknown_topic_suggests_close_commands(self):
        page = self.render('modl')
        self.assertIn("Tidak ada perintah bernama 'modl'", page)
        self.assertIn('/model', page)
        self.assertNotIn('Maksudmu', self.render('zzzzz'))

    def test_plain_help_lists_commands_and_points_to_topics(self):
        page = self.render()
        for name, _ in styling.COMMANDS:
            self.assertIn(name, page)
        self.assertIn('/help <perintah>', page)

    def test_help_command_in_the_session_loop(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(sys, 'argv', ['amagi']), patch.object(app, 'load_config', return_value={}), \
             patch.object(app, 'get_api_key', return_value='x'), patch.object(app, 'ensure_daemon_running'), \
             patch.object(app, 'check_remote_version', return_value=(False, app.VERSION)), \
             patch.object(app, 'TerminalInput') as editor, patch.object(app.requests, 'post') as post:
            editor.return_value.read.side_effect = ['/help undo', '/help', '/', '/help modl', EOFError()]
            app.main()
        plain = styling.strip_ansi(out.getvalue())
        self.assertIn('Pemakaian   /undo [list]', plain)
        self.assertIn('Perintah Lyra', plain)
        self.assertIn("Tidak ada perintah bernama 'modl'", plain)
        post.assert_not_called()                                     # help never reaches the model

    def test_completer_offers_command_names_after_help(self):
        from prompt_toolkit.document import Document
        completer = styling.WorkspaceCompleter(lambda: '.')
        names = [c.text for c in completer.get_completions(Document('/help mo'), None)]
        self.assertEqual(sorted(names), ['mode', 'model'])
        self.assertEqual([c.text for c in completer.get_completions(Document('/help '), None)][:1], ['undo'])
        self.assertEqual(list(completer.get_completions(Document('/help mode x'), None)), [])


if __name__ == '__main__':
    unittest.main()
