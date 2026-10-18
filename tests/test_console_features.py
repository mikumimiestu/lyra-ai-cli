import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import styling
import tools
from prompt_toolkit.document import Document


class FileContextTests(unittest.TestCase):
    def test_explicit_files_support_quotes_and_deduplication(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'app.py').write_text('print(42)')
            Path(folder, 'notes file.md').write_text('catatan')
            message = styling.prepare_user_message('baca @app.py @app.py @"notes file.md"', folder)
            self.assertEqual(message.count('[Referensi file: app.py]'), 1)
            self.assertIn('print(42)', message)
            self.assertIn('catatan', message)
            self.assertEqual(styling.prepare_user_message('email me@example.com', folder), 'email me@example.com')

    def test_missing_binary_and_large_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'binary').write_bytes(b'a\x00b')
            Path(folder, 'large').write_bytes(b'x' * (128 * 1024 + 1))
            for filename in ['missing', 'binary', 'large']:
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    styling.prepare_user_message('@' + filename, folder)

    def test_completer_finds_files_without_crawling_hidden_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'notes file.md').write_text('hello')
            Path(folder, '.env').write_text('not suggested')
            Path(folder, 'src').mkdir()
            completer = styling.WorkspaceCompleter(lambda: folder)
            matches = list(completer.get_completions(Document('read @no'), None))
            self.assertEqual([match.text for match in matches], ['@"notes file.md"'])
            self.assertEqual(list(completer.get_completions(Document('read @.e'), None)), [])
            directory = list(completer.get_completions(Document('@sr'), None))
            self.assertEqual(directory[0].text, '@src' + os.sep)

    def test_invalid_reference_never_reaches_api(self):
        import app
        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(app, 'load_config', return_value={}), \
             patch.object(app, 'get_api_key', return_value='test-only'), \
             patch.object(app, 'ensure_daemon_running'), \
             patch.object(app, 'check_remote_version', return_value=(False, '2.3.1')), \
             patch.object(app, 'TerminalInput') as editor, \
             patch.object(app.requests, 'post') as request:
            editor.return_value.read.side_effect = ['explain @does-not-exist-for-lyra-test', EOFError()]
            app.main()
        request.assert_not_called()


class PreviewTests(unittest.TestCase):
    def test_diff_precedes_confirmation_and_decline_preserves_file(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder, 'demo.py')
            filename.write_text('old\n')
            output = io.StringIO()
            def decline(*args):
                self.assertIn('-old', output.getvalue())
                self.assertIn('+new', output.getvalue())
                return False
            with contextlib.redirect_stdout(output), patch.object(tools, '_confirm_permission', side_effect=decline):
                result = tools.write_file(str(filename), 'new\n')
            self.assertIn('dibatalkan', result)
            self.assertEqual(filename.read_text(), 'old\n')

    def test_approved_edit_writes_exact_content(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder, 'demo.py')
            with contextlib.redirect_stdout(io.StringIO()), patch.object(tools, '_confirm_permission', return_value=True):
                result = tools.write_file(str(filename), 'new\n')
            self.assertIn('Berhasil', result)
            self.assertEqual(filename.read_text(), 'new\n')


class ConsoleTests(unittest.TestCase):
    def test_ascii_mode_has_readable_symbols(self):
        with patch.dict(os.environ, {'LYRA_ASCII': '1'}):
            self.assertFalse(styling.unicode_terminal())
            self.assertEqual(styling.ui_symbol('✓', 'OK'), 'OK')
            self.assertNotIn('·', styling.toolbar_text('Lyra Orpheus 6', 'medium', '/work'))

    def test_fitting_uses_display_width_for_cjk_and_narrow_screens(self):
        for width in [8, 20, 40]:
            result = styling.fit_console_text('a非常长的路径/folder/日本語.txt', width)
            self.assertLessEqual(styling.str_width(result), width)

    def test_grouping_does_not_call_every_command_a_test(self):
        self.assertEqual(styling.activity_group('read_file', {}), 'Eksplorasi')
        self.assertEqual(styling.activity_group('write_file', {}), 'Perubahan')
        self.assertEqual(styling.activity_group('execute_command', {'command': 'python -m pytest'}), 'Pengujian')
        self.assertEqual(styling.activity_group('execute_command', {'command': 'git status'}), 'Terminal')

    def test_activity_exit_failure_and_detail_retention(self):
        log = styling.ActivityLog()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            log.start('execute_command', {'command': 'pytest'})
            log.finish('execute_command', {'command': 'pytest'}, 'Exit Code: 1\nfailed')
            for i in range(25):
                log.finish('read_file', {'filepath': str(i)}, 'x' * 20000)
            log.show_details()
        self.assertIn('! Jalankan', output.getvalue())
        self.assertEqual(len(log.entries), 20)
        self.assertTrue(all(len(result) <= 12000 for _, result in log.entries))
        self.assertIn('detail dipotong', output.getvalue())

    def test_unicode_composer_accepts_input_in_a_narrow_terminal(self):
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        from prompt_toolkit.data_structures import Size
        class NarrowOutput(DummyOutput):
            def get_size(self):
                return Size(rows=12, columns=32)
        with create_pipe_input() as pipe, patch.object(styling, 'unicode_terminal', return_value=True):
            editor = styling.TerminalInput(lambda: dict(model='Lyra Orpheus 6', effort='medium', directory='/work'),
                                          input_stream=pipe, output_stream=NarrowOutput())
            pipe.send_text('hello\x1b\rworld\r')
            self.assertEqual(editor.read(), 'hello\nworld')

    def test_real_renderer_never_reports_a_small_window_on_large_terminal(self):
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output.vt100 import Vt100_Output
        from prompt_toolkit.data_structures import Size
        screen = io.StringIO()
        output = Vt100_Output(screen, get_size=lambda: Size(rows=40, columns=120), enable_cpr=False)
        with create_pipe_input() as pipe, patch.object(styling, 'unicode_terminal', return_value=True):
            editor = styling.TerminalInput(lambda: dict(model='Lyra Orpheus 6', effort='medium', directory='/work'),
                                          input_stream=pipe, output_stream=output)
            pipe.send_text('hello\r')
            self.assertEqual(editor.read(), 'hello')
        self.assertNotIn('Window too small', screen.getvalue())

    def test_real_renderer_handles_resize_without_minimum_height_errors(self):
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output.vt100 import Vt100_Output
        from prompt_toolkit.data_structures import Size
        screen = io.StringIO()
        sizes = [Size(rows=40, columns=120), Size(rows=4, columns=20),
                 Size(rows=7, columns=24), Size(rows=12, columns=32), Size(rows=40, columns=120)]
        current = [0]
        output = Vt100_Output(screen, get_size=lambda: sizes[current[0]], enable_cpr=False)
        with create_pipe_input() as pipe, patch.object(styling, 'unicode_terminal', return_value=True):
            editor = styling.TerminalInput(lambda: dict(model='Lyra Orpheus 6', effort='medium', directory='/work'),
                                          input_stream=pipe, output_stream=output)
            def resize_after_render(application):
                if application.is_done:
                    return
                if current[0] < len(sizes) - 1:
                    current[0] += 1
                    application.invalidate()
                else:
                    pipe.send_text('hello\r')
            editor.session.app.after_render += resize_after_render
            self.assertEqual(editor.read(), 'hello')
        self.assertEqual(current[0], len(sizes) - 1)
        self.assertNotIn('Window too small', screen.getvalue())

    def test_ascii_editor_accepts_input_without_unicode_frame(self):
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        with create_pipe_input() as pipe, patch.dict(os.environ, {'LYRA_ASCII': '1'}), contextlib.redirect_stdout(io.StringIO()):
            editor = styling.TerminalInput(lambda: dict(model='Lyra Orpheus 6', effort='medium', directory='/work'),
                                          input_stream=pipe, output_stream=DummyOutput())
            pipe.send_text('hello\r')
            self.assertEqual(editor.read(), 'hello')

    def test_branch_is_shown_only_when_available(self):
        self.assertIn('/ main', styling.toolbar_text('Lyra Orpheus 6', 'medium', '/work', branch='main'))
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(styling.workspace_branch(folder))


if __name__ == '__main__':
    unittest.main()
