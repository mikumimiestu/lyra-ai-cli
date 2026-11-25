"""End-to-end: Lyra starts a server in the background, lists it, and stops it on exit (POSIX pty, fake API)."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ptyrun import FakeApi, PtyRun
    HAVE_PTY = os.name != 'nt'
except ImportError:      # pragma: no cover
    HAVE_PTY = False

SKIP = unittest.skipUnless(HAVE_PTY and not os.environ.get('LYRA_SKIP_PTY'), 'needs a POSIX pty')
MARK = 'lyra-uji-latar-7731'
COMMAND = f"{sys.executable} -u -c \"import time; print('siap di http://localhost:8123/', flush=True); time.sleep(90)  # {MARK}\""


@SKIP
class BackgroundPtyTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp(prefix='lyra-proc-pty-')
        patcher = patch.dict(os.environ, {'LYRA_PROC_DIR': folder})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(__import__('shutil').rmtree, folder, True)
        self.api = FakeApi()
        self.addCleanup(self.api.close)
        call = '<tool_call>' + json.dumps({'name': 'start_process', 'arguments': {'command': COMMAND, 'name': 'web'}}) + '</tool_call>'
        self.api.custom.append((lambda last: last == 'nyalakan server', [('Saya nyalakan servernya.\n', 0.02), (call, 0.02)]))

    def alive(self):
        return os.popen(f"pgrep -f {MARK}").read().split()

    def test_server_runs_in_the_background_and_stops_when_lyra_exits(self):
        run = PtyRun(self.api.url, rows=30, cols=100)
        self.addCleanup(run.close)
        self.assertTrue(run.wait_for('tanya dulu', 10), run.screen.text())
        run.send('nyalakan server\r')
        self.assertTrue(run.wait_for('Izinkan?', 8), run.screen.text())
        self.assertTrue(run.screen.find('latar belakang') is not None or 'latar belakang' in run.screen.text())
        run.send('y\r')
        self.assertTrue(run.wait_for('berjalan', 10), run.screen.text())
        self.assertTrue(self.alive())
        run.send('/proses\r')
        self.assertTrue(run.wait_for('Hentikan dengan /proses stop', 6), run.screen.text())
        run.send('exit\r')
        self.assertTrue(run.wait_for('PROCESS-ENDED', 8, where=lambda: run.raw), run.screen.text())
        run.pump(1.0)
        self.assertEqual(self.alive(), [], 'proses latar harus ikut berhenti saat Lyra keluar')


if __name__ == '__main__':
    unittest.main()
