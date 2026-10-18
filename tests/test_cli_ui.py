import contextlib
import io
import os
import unittest
from unittest.mock import patch

import styling as cli_ui
import styling
from config import VERSION, FILES_TO_UPDATE
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput


class EditorTests(unittest.TestCase):
    def make_editor(self, pipe):
        return cli_ui.TerminalInput(lambda: dict(model='Lyra Orpheus 6', effort='medium',
                                                directory='/work', supports_reasoning=True),
                                    input_stream=pipe, output_stream=DummyOutput())

    def test_filtered_command_completions(self):
        completer = cli_ui.SlashCompleter()
        results = list(completer.get_completions(Document('/rem'), None))
        self.assertEqual([item.text for item in results], ['/reminder'])
        self.assertEqual(list(completer.get_completions(Document('/run echo'), None)), [])
        self.assertEqual(list(completer.get_completions(Document('explain /rem'), None)), [])

    def test_enter_sends_and_alt_enter_adds_newline(self):
        with create_pipe_input() as pipe:
            editor = self.make_editor(pipe)
            pipe.send_text('first\x1b\rsecond\r')
            self.assertEqual(editor.read(), 'first\nsecond')

    def test_bracketed_paste_stays_one_message(self):
        with create_pipe_input() as pipe:
            editor = self.make_editor(pipe)
            pipe.send_text('\x1b[200~def demo():\n    return 1\x1b[201~\r')
            self.assertEqual(editor.read(), 'def demo():\n    return 1')

    def test_tab_accepts_completion(self):
        with create_pipe_input() as pipe:
            editor = self.make_editor(pipe)
            pipe.send_text('/rem\t\r')
            self.assertEqual(editor.read(), '/reminder')

    def test_cancel_discards_draft_and_eof_exits(self):
        with create_pipe_input() as pipe:
            editor = self.make_editor(pipe)
            pipe.send_text('discard\x03')
            with self.assertRaises(KeyboardInterrupt):
                editor.read()
            pipe.send_text('next\r')
            self.assertEqual(editor.read(), 'next')
            pipe.send_text('\x04')
            with self.assertRaises(EOFError):
                editor.read()

    def test_history_is_memory_only(self):
        with create_pipe_input() as pipe:
            editor = self.make_editor(pipe)
            self.assertEqual(type(editor.session.history).__name__, 'InMemoryHistory')

    def test_noninteractive_fallback(self):
        with patch.object(cli_ui.sys.stdin, 'isatty', return_value=False), patch('builtins.input', return_value='/help'):
            editor = cli_ui.TerminalInput(lambda: {})
            self.assertIsNone(editor.session)
            self.assertEqual(editor.read(), '/help')

    def test_toolbar_uses_live_context_and_model_capabilities(self):
        with patch.dict(os.environ, {'HOME': '/home/test'}):
            text = cli_ui.toolbar_text('Lyra Luma 5.5', 'medium', '/home/test/work', False)
            self.assertIn('~/work', text)
            self.assertIn('tanpa reasoning', text)
            self.assertNotIn('medium', text)
            self.assertEqual(cli_ui.short_path('/home/test2/work'), '/home/test2/work')

    def test_activity_never_leaks_file_contents_or_escape_sequences(self):
        self.assertEqual(cli_ui.tool_activity('write_file', {'filepath': 'demo.py', 'content': 'secret'}), 'Tulis file · demo.py')
        self.assertNotIn('\x1b', cli_ui.tool_activity('execute_command', {'command': 'echo\x1b[31m\nhi'}))


class AppTests(unittest.TestCase):
    def test_welcome_is_compact_and_uses_current_version(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(styling, 'get_terminal_width', return_value=60):
            styling.print_logo()
            styling.render_header('Lyra Orpheus 6', 'medium', '/work')
        plain = styling.strip_ansi(output.getvalue())
        self.assertIn('v' + VERSION, plain)
        self.assertNotIn('2.1.1', plain)
        self.assertNotIn('██', plain)
        self.assertNotIn('Perintah Utama:', plain)
        self.assertLess(len(plain.splitlines()), 14)

    def test_main_commands_and_eof_without_api_or_daemon(self):
        import app
        output = io.StringIO()
        with contextlib.redirect_stdout(output), \
             patch.object(app, 'load_config', return_value={}), \
             patch.object(app, 'get_api_key', return_value='test-only'), \
             patch.object(app, 'ensure_daemon_running') as daemon, \
             patch.object(app, 'check_remote_version', return_value=(False, VERSION)), \
             patch.object(app, 'TerminalInput') as editor, \
             patch.object(app.requests, 'post') as request:
            editor.return_value.read.side_effect = [KeyboardInterrupt(), '/version', '/', EOFError()]
            app.main()
        self.assertIn('Input dibatalkan', output.getvalue())
        self.assertIn(VERSION, output.getvalue())
        self.assertIn('/reminder', output.getvalue())
        self.assertIn('Sampai nanti', output.getvalue())
        request.assert_not_called()
        daemon.assert_called_once()
        self.assertIn('styling.py', FILES_TO_UPDATE)

    def test_stream_keeps_markdown_and_response_text(self):
        import app
        import json
        from unittest.mock import Mock
        response = Mock(status_code=200)
        events = [
            {'choices': [{'delta': {'content': 'Halo.\n'}}]},
            {'choices': [{'delta': {'content': '```python\nprint(1)\n```\n'}}]},
        ]
        response.iter_lines.return_value = [('data: ' + json.dumps(event)).encode() for event in events] + [b'data: [DONE]']
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(app.requests, 'post', return_value=response), patch.object(app, 'Spinner'):
            code, text = app.stream_ai_response({}, {'reasoning_effort': 'medium'}, app.MODELS[2])
        self.assertEqual(code, 200)
        self.assertIn('Halo.', text)
        self.assertIn('print(1)', output.getvalue())
        self.assertIn('Lyra', output.getvalue())

    def test_permissions_still_require_explicit_yes(self):
        import tools
        with contextlib.redirect_stdout(io.StringIO()), patch('builtins.input', return_value='n'), \
             patch.object(tools.subprocess, 'run') as execute:
            result = tools.execute_command('echo test')
        self.assertIn('dibatalkan', result)
        execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
