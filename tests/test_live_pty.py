"""End-to-end: the real CLI in a pseudo-terminal, with a fake streaming API (POSIX only)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ptyrun import FakeApi, PtyRun
    HAVE_PTY = os.name != 'nt'
except ImportError:      # pragma: no cover
    HAVE_PTY = False

SKIP = unittest.skipUnless(HAVE_PTY and not os.environ.get('LYRA_SKIP_PTY'), 'needs a POSIX pty')


@SKIP
class LivePtyTests(unittest.TestCase):
    ROWS = 30

    def setUp(self):
        self.api = FakeApi()
        self.addCleanup(self.api.close)

    def start(self, **kwargs):
        run = PtyRun(self.api.url, rows=self.ROWS, cols=100, **kwargs)
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('tanya dulu', 10), run.screen.text())
        return run

    def composer_row(self, run):
        rows = [i for i, line in enumerate(run.screen.lines()) if line.strip() == '›']
        return rows[-1] if rows else None

    def test_composer_stays_at_the_bottom_while_the_answer_streams_above_it(self):
        run = self.start()
        run.send('lama\r')
        self.assertTrue(run.wait_for('kata3', 6), run.screen.text())
        text = run.screen.lines()
        answer, status, composer = (run.screen.find('● kata'), run.screen.find('Menulis jawaban'), self.composer_row(run))
        self.assertTrue(answer < status < composer, (answer, status, composer))
        self.assertIn('Esc batal', text[status])
        self.assertIn('token', text[status])

    def test_typing_while_busy_queues_and_esc_cancels_immediately(self):
        run = self.start()
        run.send('lama\r')
        self.assertTrue(run.wait_for('kata2', 6))
        run.send('halo\r')                       # typed while Lyra is busy: queued
        run.pump(0.3)
        run.send('\x1b')
        self.assertTrue(run.wait_for('Proses dibatalkan', 3), run.screen.text())
        self.assertTrue(run.wait_for('Halo! Ini', 6), run.screen.text())   # the queued message ran afterwards
        self.assertEqual(len(self.api.requests), 2)

    def test_history_scrolls_into_scrollback_instead_of_being_lost(self):
        run = self.start()
        for _ in range(4):
            run.send('halo\r')
            run.pump(2.2)
        history = '\n'.join(run.screen.history())
        self.assertIn('██╗', history)                       # the logo scrolled up, not erased
        self.assertGreaterEqual(history.count('Halo! Ini'), 4)
        self.assertGreater(len(run.screen.scrollback), 10)
        self.assertGreaterEqual(self.composer_row(run), self.ROWS - 9)     # once the screen is full it stays pinned at the bottom

    def test_permission_prompt_and_arrow_menu_work_with_the_live_area_suspended(self):
        run = self.start()
        run.send('tulis\r')
        self.assertTrue(run.wait_for('Izinkan?', 8), run.screen.text())
        run.send('y\r')
        self.assertTrue(run.wait_for('halo-dari-tool', 6), run.screen.text())
        run.send('/model\r')
        self.assertTrue(run.wait_for('Pilih Model AI', 6))
        run.send('\x1b[B\r')
        self.assertTrue(run.wait_for('Pilih Tingkat Penalaran', 6))
        run.send('\r')
        self.assertTrue(run.wait_for('Eurydice 6 · medium', 6), run.screen.text())   # footer follows the new model

    def test_shift_tab_changes_mode_and_exit_leaves_a_clean_terminal(self):
        run = self.start()
        run.send('\x1b[Z')
        self.assertTrue(run.wait_for('auto-setuju edit file', 3))
        run.send('exit\r')
        self.assertTrue(run.wait_for('PROCESS-ENDED', 6, where=lambda: run.raw), run.screen.text())
        self.assertIsNone(self.composer_row(run))             # the composer was erased on exit

    def test_typing_exit_leaves_a_clean_screen_with_one_goodbye_line(self):
        for env in (None, {'LYRA_CLASSIC': '1'}):
            with self.subTest(mode='classic' if env else 'live'):
                run = PtyRun(self.api.url, rows=self.ROWS, cols=100, env=env)
                self.addCleanup(run.close)
                self.assertTrue(run.wait_for('tanya dulu', 10))
                run.send('halo\r')
                self.assertTrue(run.wait_for('Halo! Ini', 8))
                self.assertTrue(run.wait_for('Selesai', 4))
                run.pump(1.0)                                # let the prompt come back before typing
                run.send('exit\r')
                self.assertTrue(run.wait_for('PROCESS-ENDED', 6, where=lambda: run.raw), run.screen.text())
                text = run.screen.text()
                self.assertIn('Selamat tinggal', text)
                for leftover in ('Halo! Ini', '██╗', '› halo', 'tanya dulu'):
                    self.assertNotIn(leftover, text)

    def test_classic_mode_is_still_available(self):
        run = PtyRun(self.api.url, rows=self.ROWS, cols=100, env={'LYRA_CLASSIC': '1'})
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('tanya dulu', 10), run.screen.text())
        run.send('halo\r')
        self.assertTrue(run.wait_for('Halo! Ini', 8), run.screen.text())
        self.assertTrue(run.wait_for('Selesai', 4))


if __name__ == '__main__':
    unittest.main()
