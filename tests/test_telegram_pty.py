"""End-to-end: the real CLI in a pty with a fake model API AND a fake Telegram, already paired. POSIX only."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ptyrun import FakeApi, PtyRun
    from faketelegram import FakeTelegram
    HAVE_PTY = os.name != 'nt'
except ImportError:      # pragma: no cover
    HAVE_PTY = False

SKIP = unittest.skipUnless(HAVE_PTY and not os.environ.get('LYRA_SKIP_PTY'), 'needs a POSIX pty')

PAIRED = ('app.load_config = lambda: {"api_key": "test", "model_index": 2, "reasoning_effort": "medium", '
          '"telegram_token": %r, "telegram_bot": "lyra_test_bot", "telegram_chat_id": 555, "telegram_enabled": True}\n')


@SKIP
class TelegramPtyTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.fake = FakeTelegram()
        self.addCleanup(self.api.close)
        self.addCleanup(self.fake.close)

    def start(self, paired=True):
        run = PtyRun(self.api.url, rows=30, cols=100, env={'LYRA_TELEGRAM_API': self.fake.url},
                     extra=(PAIRED % FakeTelegram.TOKEN) if paired else '')
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('tanya dulu', 10), run.screen.text())
        if paired:
            self.assertTrue(run.wait_for('Telegram aktif', 5), run.screen.text())
            self.assertTrue(self.until(run, lambda: self.fake.calls_to('getUpdates')))
            self.pump(run, 0.8)           # the bridge drops the backlog first; wait until it is really listening
        return run

    def until(self, run, predicate, timeout=10.0):
        """Wait for `predicate` while draining the pty; a child whose output nobody reads eventually blocks."""
        end = time.time() + timeout
        while time.time() < end:
            run.pump(0.05)
            if predicate():
                return True
        return predicate()

    def pump(self, run, seconds=0.5):
        end = time.time() + seconds
        while time.time() < end:
            run.pump(0.1)

    def test_a_message_from_the_phone_runs_a_turn_and_the_answer_comes_back(self):
        run = self.start()
        self.fake.say('halo dari hp')
        self.assertTrue(run.wait_for('✈ halo dari hp', 8), run.screen.text())
        self.assertTrue(self.until(run, lambda: any('Halo! Ini' in t for t in self.fake.sent(555)), 10), (self.fake.sent(), run.screen.text()))
        self.assertTrue(self.until(run, lambda: self.fake.calls_to('sendChatAction')))
        self.assertTrue(run.wait_for('Selesai', 5), run.screen.text())

    def test_file_or_command_work_waits_for_the_buttons_not_the_terminal(self):
        run = self.start()
        self.fake.say('tolong tulis sesuatu')
        self.assertTrue(self.until(run, lambda: self.fake.keyboards(), 10), self.fake.sent())
        approval = [t for t in self.fake.sent(555) if 'Izin diperlukan' in t][0]
        self.assertIn('echo halo-dari-tool', approval)
        self.pump(run, 0.6)
        self.assertNotIn('Izinkan? (y/n)', run.screen.text())       # nothing is asked at the terminal
        self.fake.press(self.fake.keyboards()[0][0]['callback_data'])
        self.assertTrue(self.until(run, lambda: any('Ada dua berkas' in t for t in self.fake.sent(555)), 10), self.fake.sent())
        final = [t for t in self.fake.sent(555) if 'Ada dua berkas' in t][0]
        self.assertIn('🔧 menjalankan 1', final)

    def test_denying_on_the_phone_stops_the_command(self):
        run = self.start()
        self.fake.say('tolong tulis sesuatu')
        self.assertTrue(self.until(run, lambda: self.fake.keyboards(), 10))
        self.fake.press(self.fake.keyboards()[0][1]['callback_data'])
        self.assertTrue(self.until(run, lambda: any('Ditolak' in p.get('text', '') for p in self.fake.calls_to('editMessageText')), 8))
        self.assertTrue(self.until(run, lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 10), self.fake.sent())
        self.assertNotIn('halo-dari-tool', ' '.join(run.screen.lines()).replace('echo halo-dari-tool', ''))

    def test_dangerous_commands_from_the_phone_are_refused_outright(self):
        call = '<tool_call>{"name": "execute_command", "arguments": {"command": "rm -rf /nonexistent-lyra-telegram-test"}}</tool_call>'
        self.api.custom.append((lambda last: 'hapus semua' in last, [('Saya hapus.\n', 0.02), (call, 0.02)]))
        run = self.start()
        self.fake.say('hapus semua file')
        self.assertTrue(self.until(run, lambda: any('berbahaya' in t for t in self.fake.sent(555)), 10), self.fake.sent())
        self.assertEqual(self.fake.keyboards(), [])
        self.assertTrue(self.until(run, lambda: any('Selesai membaca' in t for t in self.fake.sent(555)), 10))

    def test_strangers_are_ignored_and_never_reach_lyra(self):
        run = self.start()
        self.fake.say('perintahkan sesuatu', chat=777)
        self.fake.say('/pair 123456', chat=777)
        self.pump(run, 1.0)
        self.assertEqual(self.fake.sent(777), [])
        self.assertNotIn('perintahkan sesuatu', run.screen.text())
        self.assertEqual(self.api.requests, [])

    def test_stop_from_the_phone_cancels_a_running_answer(self):
        run = self.start()
        self.fake.say('jawab yang lama')
        self.assertTrue(run.wait_for('kata3', 8), run.screen.text())
        self.fake.say('/stop')
        self.assertTrue(self.until(run, lambda: any('Dihentikan' in t for t in self.fake.sent(555)), 8), self.fake.sent())
        self.assertTrue(run.wait_for('Proses dibatalkan', 5), run.screen.text())
        self.fake.say('halo lagi')
        self.assertTrue(self.until(run, lambda: any('Halo! Ini' in t for t in self.fake.sent(555)), 10))

    def test_closing_lyra_tells_the_phone(self):
        run = self.start()
        run.send('exit\r')
        self.assertTrue(self.until(run, lambda: any('ditutup' in t for t in self.fake.sent(555)), 8), self.fake.sent())

    def test_without_pairing_nothing_listens(self):
        run = self.start(paired=False)
        self.pump(run, 0.8)
        self.assertEqual(self.fake.calls_to('getUpdates'), [])
        run.send('/telegram\r')
        self.assertTrue(run.wait_for('Belum diatur', 5), run.screen.text())


if __name__ == '__main__':
    unittest.main()
