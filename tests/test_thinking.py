import contextlib
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

import app
import spinner as progress_module
import styling
import tools


def event(**delta):
    return ('data: ' + json.dumps({'choices': [{'delta': delta}]})).encode()


class ResponseTests(unittest.TestCase):
    def run_stream(self, lines, status=200):
        response = Mock(status_code=status, text='upstream error')
        response.iter_lines.return_value = lines
        progress = Mock()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(app.requests, 'post', return_value=response), \
             patch.object(app, 'Spinner', return_value=progress):
            result = app.stream_ai_response({}, {'reasoning_effort': 'medium'}, app.MODELS[2])
        response.close.assert_called_once()
        self.assertTrue(progress.stop.called)
        return result, output.getvalue(), progress

    def test_explicit_reasoning_hidden_even_when_answer_in_same_delta(self):
        result, output, progress = self.run_stream([
            event(reasoning_content='PRIVATE REASONING\n', content='Hello\n'), b'data: [DONE]'])
        self.assertEqual(result, (200, 'Hello\n'))
        self.assertIn('Hello', output)
        self.assertNotIn('PRIVATE REASONING', output)
        progress.set_message.assert_any_call('Memproses permintaan...')

    def test_tagged_reasoning_is_hidden_at_every_possible_split(self):
        content = '<think>PRIVATE\nREASONING</think>Hello\n'
        for split in range(1, len(content)):
            with self.subTest(split=split):
                result, output, _ = self.run_stream([event(content=content[:split]), event(content=content[split:])])
                self.assertEqual(result, (200, 'Hello\n'))
                self.assertNotIn('PRIVATE', output)
                self.assertNotIn('REASONING', output)
                self.assertNotIn('<think>', output)

    def test_tool_protocol_kept_for_dispatch_but_hidden_from_display(self):
        call = '<tool_call>{"name":"read_file","arguments":{"filepath":"app.py"}}</tool_call>'
        for split in range(1, len('<tool_call>')):
            with self.subTest(split=split):
                result, output, _ = self.run_stream([event(content=call[:split]), event(content=call[split:])])
                self.assertEqual(result, (200, call))
                self.assertNotIn('tool_call', output)
                self.assertNotIn('read_file', output)

    def test_tool_text_inside_hidden_reasoning_cannot_be_dispatched(self):
        result, output, _ = self.run_stream([event(content='<think><tool_call>hidden</tool_call></think>Hello')])
        self.assertEqual(result, (200, 'Hello'))
        self.assertNotIn('hidden', output)

    def test_reasoning_only_and_unclosed_thinking_are_not_success(self):
        for lines in [[event(reasoning='private')], [event(content='<think>private')]]:
            result, output, _ = self.run_stream(lines)
            self.assertEqual(result[0], 0)
            self.assertNotIn('private', output)
            self.assertNotIn('Selesai', output)

    def test_spinner_active_until_real_answer_and_stopped_before_render(self):
        response = Mock(status_code=200)
        progress = Mock()
        def lines():
            yield event(reasoning='private')
            self.assertFalse(progress.stop.called)
            yield event(content='Hello\n')
            self.assertTrue(progress.stop.called)
        response.iter_lines.side_effect = lines
        original = app.format_markdown_line
        def format_after_stop(*args):
            self.assertTrue(progress.stop.called)
            return original(*args)
        with contextlib.redirect_stdout(io.StringIO()), patch.object(app.requests, 'post', return_value=response), \
             patch.object(app, 'Spinner', return_value=progress), patch.object(app, 'format_markdown_line', side_effect=format_after_stop):
            self.assertEqual(app.stream_ai_response({}, {}, app.MODELS[2])[0], 200)

    def test_http_error_closes_response_without_success(self):
        result, output, _ = self.run_stream([], status=401)
        self.assertEqual(result, (401, 'upstream error'))
        self.assertNotIn('Selesai', output)

    def test_request_and_stream_interruptions_always_stop_progress(self):
        for error in [RuntimeError('offline'), KeyboardInterrupt()]:
            progress = Mock()
            with self.subTest(error=type(error)), contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(app.requests, 'post', side_effect=error), patch.object(app, 'Spinner', return_value=progress):
                if isinstance(error, KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        app.stream_ai_response({}, {})
                else:
                    self.assertEqual(app.stream_ai_response({}, {})[0], 0)
            self.assertTrue(progress.stop.called)
        response = Mock(status_code=200)
        response.iter_lines.side_effect = KeyboardInterrupt()
        with contextlib.redirect_stdout(io.StringIO()), patch.object(app.requests, 'post', return_value=response), \
             patch.object(app, 'Spinner') as factory, self.assertRaises(KeyboardInterrupt):
            app.stream_ai_response({}, {})
        factory.return_value.stop.assert_called()
        response.close.assert_called_once()


class TurnIntegrationTests(unittest.TestCase):
    def setup_main(self, output):
        stack = contextlib.ExitStack()
        stack.enter_context(contextlib.redirect_stdout(output))
        stack.enter_context(patch.object(app, 'load_config', return_value={}))
        stack.enter_context(patch.object(app, 'get_api_key', return_value='test-only'))
        stack.enter_context(patch.object(app, 'get_current_system_prompt', return_value='test-only'))
        stack.enter_context(patch.object(app, 'ensure_daemon_running'))
        stack.enter_context(patch.object(app, 'check_remote_version', return_value=(False, 'test-only')))
        return stack

    def test_tool_cycle_has_one_final_summary_with_completed_read(self):
        call = '<tool_call>{"name":"read_file","arguments":{"filepath":"app.py"}}</tool_call>'
        first = Mock(status_code=200)
        first.iter_lines.return_value = [event(reasoning='private'), event(content=call)]
        second = Mock(status_code=200)
        second.iter_lines.return_value = [event(content='Jawaban akhir.\n')]
        output = io.StringIO()
        with self.setup_main(output), patch.object(app, 'TerminalInput') as editor, \
             patch.object(app.requests, 'post', side_effect=[first, second]), \
             patch.object(app, 'read_file', return_value='source') as read:
            editor.return_value.read.side_effect = ['baca app.py', EOFError()]
            app.main()
        self.assertEqual(output.getvalue().count('Selesai'), 1)
        self.assertIn('1 file dibaca', output.getvalue())
        self.assertIn('Jawaban akhir.', output.getvalue())
        self.assertNotIn('private', output.getvalue())
        self.assertNotIn('<tool_call>', output.getvalue())
        read.assert_called_once_with('app.py')
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_cancelled_turn_returns_to_input_without_success_summary(self):
        instances = []
        class TrackingSpinner(progress_module.Spinner):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                instances.append(self)
        output = io.StringIO()
        with self.setup_main(output), patch.object(app, 'TerminalInput') as editor, \
             patch.object(app.requests, 'post', side_effect=KeyboardInterrupt()), \
             patch.object(app, 'Spinner', TrackingSpinner):
            editor.return_value.read.side_effect = ['hello', EOFError()]
            app.main()
        self.assertIn('Proses dibatalkan', output.getvalue())
        self.assertNotIn('Selesai', output.getvalue())
        self.assertTrue(instances)
        self.assertTrue(all(not indicator._active for indicator in instances))


class SpinnerTests(unittest.TestCase):
    def test_plain_output_has_no_control_sequences_or_repeated_status(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            indicator = progress_module.Spinner('Waiting')
            indicator.start()
            indicator.start()
            indicator.set_message('Processing')
            indicator.set_message('Processing')
            indicator.stop()
            indicator.stop()
        self.assertEqual(output.getvalue(), '  Waiting\n  Processing\n')
        self.assertNotIn('\x1b', output.getvalue())

    def test_elapsed_uses_monotonic_time_and_width_limit(self):
        with patch.object(progress_module.time, 'monotonic', return_value=100):
            indicator = progress_module.Spinner('Memproses permintaan panjang sekali')
            with contextlib.redirect_stdout(io.StringIO()):
                indicator.start()
        with patch.object(progress_module.time, 'monotonic', return_value=106), \
             patch.object(progress_module, 'get_terminal_width', return_value=24), \
             patch.object(progress_module, 'unicode_terminal', return_value=False):
            self.assertEqual(indicator.elapsed, 6)
            line = styling.strip_ansi(indicator._line())
            self.assertIn('6s', line)
            self.assertLessEqual(styling.str_width(line), 23)
        indicator.stop()

    def test_stop_joins_animation_and_is_idempotent(self):
        class TtyOutput(io.StringIO):
            def isatty(self):
                return True
        output = TtyOutput()
        with contextlib.redirect_stdout(output), patch.dict(os.environ, {'TERM': 'xterm-256color', 'LYRA_NO_ANIMATION': '0'}):
            indicator = progress_module.Spinner('Waiting')
            indicator.start()
            thread = indicator.thread
            indicator.stop()
            snapshot = output.getvalue()
            indicator.stop()
        self.assertFalse(thread.is_alive())
        self.assertEqual(output.getvalue(), snapshot)
        self.assertTrue(snapshot.endswith('\r\x1b[2K'))

    def test_cancelled_command_and_project_do_not_leave_spinner_running(self):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(tools, '_confirm_permission', return_value=True), \
             patch.object(tools, 'Spinner') as factory, patch.object(tools.subprocess, 'run', side_effect=KeyboardInterrupt()), \
             self.assertRaises(KeyboardInterrupt):
            tools.execute_command('echo test')
        factory.return_value.stop.assert_called()
        with contextlib.redirect_stdout(io.StringIO()), patch.object(tools, '_confirm_permission', return_value=True), \
             patch.object(tools, 'Spinner') as factory, patch.object(tools, '_run_cmds_silent', side_effect=KeyboardInterrupt()), \
             self.assertRaises(KeyboardInterrupt):
            tools.init_project('node', 'test-only')
        factory.return_value.stop.assert_called()

    def test_turn_summary_uses_whole_turn_time_and_completed_file_reads(self):
        log = styling.ActivityLog()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('time.monotonic', return_value=100):
            log.begin_turn()
            log.finish('read_file', {'filepath': 'a.py'}, 'contents')
            log.finish('read_file', {'filepath': 'a.py'}, 'contents')
            log.finish('read_file', {'filepath': 'b.py'}, 'Error: unavailable')
        with contextlib.redirect_stdout(output), patch('time.monotonic', return_value=108):
            log.complete_turn()
            log.complete_turn()
        self.assertEqual(output.getvalue().count('Selesai'), 1)
        self.assertIn('8s', output.getvalue())
        self.assertIn('1 file dibaca', output.getvalue())


if __name__ == '__main__':
    unittest.main()
