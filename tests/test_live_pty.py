"""End-to-end: the real CLI in a pseudo-terminal, with a fake streaming API (POSIX only)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

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
        self.assertIn('Lyra CLI v', ' '.join(history.split()))      # the header scrolled up, not erased
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
                for leftover in ('Halo! Ini', 'Mau ngerjain', '▀', '› halo', 'tanya dulu'):
                    self.assertNotIn(leftover, text)

    def test_plain_ascii_terminals_work_in_both_modes(self):
        """A C locale (no UTF-8) used to crash live mode: the proxy claimed UTF-8 for an ASCII terminal."""
        c_locale = {'LC_ALL': 'C', 'LANG': 'C', 'PYTHONCOERCECLOCALE': '0', 'PYTHONUTF8': '0'}
        for name, env in (('live, C locale', dict(c_locale)), ('classic, C locale', dict(c_locale, LYRA_CLASSIC='1')),
                          ('live, LYRA_ASCII', {'LYRA_ASCII': '1'})):
            with self.subTest(name):
                run = PtyRun(self.api.url, rows=self.ROWS, cols=100, env=env)
                self.addCleanup(run.close)
                self.assertTrue(run.wait_for('Shift+Tab', 10), run.screen.text())
                run.send('halo\r')
                self.assertTrue(run.wait_for('Halo! Ini', 8), run.screen.text())
                self.assertNotIn('Kesalahan', run.screen.text())
                self.assertNotIn('Traceback', run.screen.text())

    def tool_call(self, name, **arguments):
        return [('Saya kerjakan.\n', 0.01), ('<tool_call>' + json.dumps({'name': name, 'arguments': arguments}) + '</tool_call>', 0.01)]

    def test_edit_search_and_undo_work_through_the_live_console(self):
        folder = tempfile.mkdtemp(prefix='lyra-e2e-')
        self.addCleanup(__import__('shutil').rmtree, folder, True)
        target = os.path.join(folder, 'versi.txt')
        with open(target, 'w') as handle:
            handle.write('versi = 1\n')
        self.api.custom += [
            (lambda last: last == 'ubah', self.tool_call('edit_file', filepath=target, old='versi = 1', new='versi = 2')),
            (lambda last: last == 'cari', self.tool_call('search', pattern='versi', path=folder)),
        ]
        run = self.start()
        run.send('cari\r')
        self.assertTrue(run.wait_for('Mencari 1 kali', 8), run.screen.text())      # read-only step collapsed to one line
        run.send('ubah\r')
        self.assertTrue(run.wait_for('Izinkan?', 8), run.screen.text())            # edits still ask in the default mode
        self.assertIn('+versi = 2', run.screen.text())                              # the diff is shown first
        run.send('y\r')
        self.assertTrue(run.wait_for('Berhasil mengubah', 8), run.screen.text())
        run.pump(1.0)
        self.assertEqual(Path(target).read_text(), 'versi = 2\n')
        run.send('/undo\r')
        self.assertTrue(run.wait_for('Izinkan?', 6), run.screen.text())
        run.send('y\r')
        self.assertTrue(run.wait_for('Dikembalikan', 6), run.screen.text())
        self.assertEqual(Path(target).read_text(), 'versi = 1\n')

    def test_compact_summarises_and_resume_flag_continues_the_saved_chat(self):
        run = self.start()
        for text in ('halo', 'halo lagi', 'halo ketiga'):
            run.send(text + '\r')
            self.assertTrue(run.wait_for('Selesai', 8))
            run.pump(0.5)
        run.send('/compact\r')
        self.assertTrue(run.wait_for('Percakapan diringkas', 8), run.screen.text())
        run.send('halo lagi\r')
        run.pump(2.5)
        carried = [m['content'] for m in self.api.requests[-1]['messages']]
        self.assertTrue(any(c.startswith('[Ringkasan') and 'pengguna menguji Lyra' in c for c in carried), carried)

    def test_footer_shows_remaining_quota_and_queued_messages(self):
        extra = (
            'app.load_config = lambda: {"auth_method": "account", "cli_token": "tok", "model_index": 2, "reasoning_effort": "medium"}\n'
            'app.fetch_quota = lambda config: {"limit": 20000, "used": 16000, "remaining": 4000, "tier": "free", "resets_in_seconds": 90}\n')
        run = PtyRun(self.api.url, rows=self.ROWS, cols=140, env={'ASTBYTE_API_KEY': ''}, extra=extra)
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('sisa kuota 20%', 10), run.screen.text())
        self.assertNotIn('antre', run.screen.text())
        run.send('lama\r')
        self.assertTrue(run.wait_for('kata2', 6))
        run.send('satu\r')
        run.pump(0.2)
        run.send('dua\r')
        self.assertTrue(run.wait_for('2 pesan antre', 4), run.screen.text())
        run.send('\x1b')                                    # cancel the long answer; the queue then drains
        self.assertTrue(run.wait_for('Proses dibatalkan', 4))
        run.pump(5.0)
        self.assertNotIn('pesan antre', run.screen.text())
        self.assertEqual(len(self.api.requests), 3)

    def test_long_answers_wrap_at_word_boundaries_and_the_dialog_stays_small(self):
        sentence = ('Cache terbesar yang relatif aman dibersihkan adalah Google Codex pip TypeScript dan node-gyp totalnya sekitar 1,4 GB. '
                    'Cache ini akan dibuat ulang otomatis saat aplikasinya digunakan lagi dan seterusnya sampai baris ini panjang sekali.')
        self.api.custom += [
            (lambda last: last == 'panjang', [(word + ' ', 0.01) for word in sentence.split()] + [('\n', 0.01)]),
            (lambda last: last == 'cache', self.tool_call('execute_command', command="du -sh \"$HOME/Library/Caches\" 2>/dev/null || true; "
                                                           "find \"$HOME/Library/Caches\" -maxdepth 1 | sort -rh | head -20; df -h /")),
        ]
        run = PtyRun(self.api.url, rows=40, cols=60)
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('Shift+Tab', 10))
        run.send('panjang\r')
        self.assertTrue(run.wait_for('seterusnya', 8), run.screen.text())
        run.pump(1.0)
        lines = run.screen.lines()
        start = next(i for i, l in enumerate(lines) if l.startswith('● Cache terbesar'))
        end = max(i for i, l in enumerate(lines) if 'panjang sekali' in l or 'sekali.' in l)
        answer = lines[start:end + 1]
        self.assertGreaterEqual(len(answer), 3)
        self.assertTrue(all(len(l) <= 59 for l in answer), answer)
        self.assertTrue(all(l.startswith('  ') and not l.startswith('   ') for l in answer[1:]), answer)   # hanging indent
        self.assertEqual(' '.join(l.strip().lstrip('●').strip() for l in answer).split(), sentence.split())  # no word cut
        run.send('cache\r')
        self.assertTrue(run.wait_for('Izinkan?', 8), run.screen.text())
        lines = [l for l in run.screen.lines()]
        heading = next(i for i, l in enumerate(lines) if 'Eksekusi Perintah' in l)
        prompt = next(i for i, l in enumerate(lines) if 'Izinkan?' in l)
        self.assertLessEqual(prompt - heading, 7, '\n'.join(lines[heading:prompt + 1]))     # compact: no frame, no filler rows
        self.assertTrue(all('╭' not in l for l in lines[heading:prompt + 1]))               # no frame around the dialog
        self.assertIn('batas', ' '.join(lines[heading:prompt]))
        run.send('n\r')

    def header_of(self, env=None, rows=30, cols=100):
        run = PtyRun(self.api.url, rows=rows, cols=cols, env=env)
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('Shift+Tab', 10), run.screen.text())
        return run.screen.lines()

    def test_header_shows_the_pet_in_colour_terminals_and_plain_text_elsewhere(self):
        def blocks(lines):
            return [l for l in lines if '▀' in l or '▄' in l]

        def squash(line):
            return ' '.join(line.split())
        for name, env in (('true colour', {'COLORTERM': 'truecolor'}), ('256 colours', {'COLORTERM': '', 'TERM_PROGRAM': 'Apple_Terminal'})):
            lines = self.header_of(env)
            self.assertEqual(len(blocks(lines)), 12, (name, lines[:16]))
            title = next(l for l in lines if 'Lyra CLI' in l)
            self.assertTrue('▀' in title or '▄' in title, title)               # beside the pet, not under it
            self.assertIn('v', squash(title))
            self.assertTrue(all(len(l) <= 100 for l in lines))
        lines = self.header_of({'NO_COLOR': '1'})
        self.assertFalse(blocks(lines))
        self.assertTrue(any(squash(l).startswith('✦ Lyra CLI v') for l in lines))
        self.assertFalse(blocks(self.header_of({'COLORTERM': 'truecolor'}, cols=60)))      # too narrow for the pet
        self.assertFalse(blocks(self.header_of({'COLORTERM': 'truecolor'}, rows=18)))      # too short for the pet

    def test_classic_mode_is_still_available(self):
        run = PtyRun(self.api.url, rows=self.ROWS, cols=100, env={'LYRA_CLASSIC': '1'})
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('tanya dulu', 10), run.screen.text())
        run.send('halo\r')
        self.assertTrue(run.wait_for('Halo! Ini', 8), run.screen.text())
        self.assertTrue(run.wait_for('Selesai', 4))


if __name__ == '__main__':
    unittest.main()
