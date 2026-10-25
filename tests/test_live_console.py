import contextlib
import io
import os
import sys
import unittest
from unittest.mock import Mock, patch

import app
import spinner as sp
import styling


class FakeTerminal:
    """Stands in for the real terminal: records what the live console prints above its live area."""

    def __init__(self):
        self.printed = []


class LiveStateTests(unittest.TestCase):
    def setUp(self):
        self.live = sp.LiveState()
        self.printed = []
        self.live.print_above = self.printed.append

    def test_stdout_proxy_forwards_whole_lines_and_holds_the_tail(self):
        out = sp.LiveStdout(self.live)
        out.write('satu')
        self.assertEqual(self.printed, [])
        out.write(' dua\ntiga\nempat')
        self.assertEqual(self.printed, ['satu dua\ntiga\n'])
        out.write('\n')
        self.assertEqual(self.printed[-1], 'empat\n')
        self.assertTrue(out.isatty())

    def test_stream_commits_finished_lines_and_keeps_the_partial_one_live(self):
        self.live.write_stream('Halo')
        self.assertEqual((self.printed, self.live.partial), ([], 'Halo'))
        self.live.write_stream(' dunia\nbaris dua')
        self.assertEqual(self.printed, ['Halo dunia\n'])
        self.assertEqual(self.live.partial, 'baris dua')
        self.live.flush_stream()
        self.assertEqual(self.printed[-1], 'baris dua\n')
        self.assertEqual(self.live.partial, '')

    def test_read_marks_the_worker_busy_and_eof_ends_the_session(self):
        self.live.submit('halo')
        self.assertEqual(self.live.read(), 'halo')
        self.assertTrue(self.live.busy)
        self.live.submit_eof()
        with self.assertRaises(EOFError):
            self.live.read()
        self.assertFalse(self.live.busy)

    def test_cancel_only_applies_to_a_running_turn_and_closes_the_connection(self):
        self.live.request_cancel()
        self.assertFalse(self.live.cancel.is_set())
        self.live.busy = True
        self.live.response = Mock()
        self.live.request_cancel()
        self.live.response.close.assert_called_once()
        with self.assertRaises(KeyboardInterrupt):         # TurnCancelled is a KeyboardInterrupt
            self.live.check_cancel()
        self.live.check_cancel()                           # the flag is consumed
        self.assertTrue(issubclass(sp.TurnCancelled, KeyboardInterrupt))

    def test_proxy_mirrors_the_real_terminal_encoding_and_never_crashes_on_it(self):
        class AsciiTerminal(io.StringIO):
            encoding = 'ascii'

            def write(self, text):
                text.encode('ascii')            # a real ASCII terminal raises UnicodeEncodeError here
                return super().write(text)
        ascii_out = AsciiTerminal()
        self.live.real_stdout = ascii_out
        self.assertEqual(sp.LiveStdout(self.live).encoding, 'ascii')
        sp.write_safely(ascii_out, 'panah › dan ↓\n')
        self.assertEqual(ascii_out.getvalue(), 'panah ? dan ?\n')

    def test_status_attaches_and_detaches(self):
        status = Mock()
        status.live_lines.return_value = 'menunggu'
        self.live.attach_status(status)
        self.assertTrue(self.live.status_visible())
        self.assertEqual(self.live.status_text(), 'menunggu')
        self.live.detach_status(Mock())                    # someone else's status is left alone
        self.assertTrue(self.live.status_visible())
        self.live.detach_status(status)
        self.assertEqual(self.live.status_text(), '')

    def test_output_goes_straight_to_the_terminal_when_the_ui_is_not_running(self):
        live = sp.LiveState()
        out = io.StringIO()
        live.real_stdout = out
        live.print_above('langsung\n')
        self.assertEqual(out.getvalue(), 'langsung\n')

    def test_live_mode_needs_a_real_posix_terminal(self):
        with patch.dict(os.environ, {'LYRA_CLASSIC': '1'}):
            self.assertFalse(sp.live_supported())
        with patch.object(sys.stdout, 'isatty', return_value=False):
            self.assertFalse(sp.live_supported())
        with patch.object(sp.os, 'name', 'nt'):
            self.assertFalse(sp.live_supported())


class LiveIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, sp.LIVE, 'active', False)
        self.addCleanup(sp.LIVE.detach_status, sp.LIVE._status)

    def test_spinner_reports_to_the_live_console_instead_of_writing(self):
        sp.LIVE.active = True
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            indicator = sp.Spinner('Menunggu...', tip=True)
            indicator.start()
            self.assertIs(sp.LIVE._status, indicator)
            indicator.set_message('Menulis jawaban...')
            self.assertIn('Menulis jawaban', styling.strip_ansi(sp.LIVE.status_text()))
            self.assertIn('Tips:', styling.strip_ansi(sp.LIVE.status_text()))
            indicator.stop()
        self.assertIsNone(sp.LIVE._status)
        self.assertEqual(output.getvalue(), '')

    def test_key_watcher_stays_off_while_the_live_console_owns_the_keyboard(self):
        sp.LIVE.active = True
        self.assertFalse(sp.EscapeWatcher(force=False)._enabled())

    def test_cancelled_stream_closes_the_response_and_raises(self):
        response = Mock(status_code=200)
        sp.LIVE.cancel.set()
        response.iter_lines.return_value = iter([b'data: {"choices":[{"delta":{"content":"hai"}}]}'])
        progress = Mock()
        with contextlib.redirect_stdout(io.StringIO()), patch.object(app.requests, 'post', return_value=response), \
             patch.object(app, 'Spinner', return_value=progress), self.assertRaises(sp.TurnCancelled):
            app.stream_ai_response({}, {})
        response.close.assert_called_once()
        progress.stop.assert_called()
        sp.LIVE.cancel.clear()


    def test_restart_hands_the_terminal_back_before_replacing_the_process(self):
        events = []
        sp.LIVE.active = True

        def shutdown():
            events.append('shutdown')
            sp.LIVE.active = False
        with patch.object(sp.LIVE, 'shutdown', side_effect=shutdown), patch.object(app.os, 'name', 'posix'), \
             patch.object(app.os, 'execv', side_effect=lambda *a: events.append('exec')), contextlib.redirect_stdout(io.StringIO()):
            app.restart_application()
        self.assertEqual(events, ['shutdown', 'exec'])


class CleanExitTests(unittest.TestCase):
    def test_clear_terminal_only_acts_on_a_real_terminal(self):
        pipe = io.StringIO()
        with contextlib.redirect_stdout(pipe):
            self.assertFalse(styling.clear_terminal())
        self.assertEqual(pipe.getvalue(), '')
        tty = io.StringIO()
        tty.isatty = lambda: True
        with contextlib.redirect_stdout(tty), patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            self.assertTrue(styling.clear_terminal())
        self.assertEqual(tty.getvalue(), '\033[2J\033[H')
        with contextlib.redirect_stdout(tty), patch.dict(os.environ, {'TERM': 'dumb'}):
            self.assertFalse(styling.clear_terminal())

    def test_classic_exit_wipes_the_screen_then_says_goodbye(self):
        order = []
        with patch.object(app, 'clear_terminal', side_effect=lambda: order.append('clear')), \
             patch('builtins.print', side_effect=lambda *a, **k: order.append(a[0])):
            app.end_session(None, 'sampai jumpa')
        self.assertEqual(order, ['clear', 'sampai jumpa'])

    def test_live_exit_defers_the_goodbye_until_the_ui_is_gone(self):
        live = sp.LiveState()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            app.end_session(live, 'sampai jumpa')
        self.assertEqual(live.exit_message, 'sampai jumpa')
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
