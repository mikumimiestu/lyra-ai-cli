"""Proses latar belakang: server dev yang berjalan terus tanpa menggantung Lyra. Memakai server Python palsu, bukan alat nyata."""
import os
import shlex
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import tools

SERVER = f"{shlex.quote(sys.executable)} -u -c " + shlex.quote(
    "import time; print('Server siap di http://localhost:8123/', flush=True); time.sleep(120)")


@unittest.skipIf(os.name == 'nt', 'diuji di macOS/Linux; Windows memakai taskkill')
class BackgroundProcessTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='lyra-proc-')
        patcher = patch.dict(os.environ, {'LYRA_PROC_DIR': self.folder})
        patcher.start()
        self.addCleanup(patcher.stop)
        confirm = patch.object(tools, '_confirm_permission', lambda *a, **k: True)
        confirm.start()
        self.addCleanup(confirm.stop)
        tools.BACKGROUND.clear()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        tools.stop_all_processes()
        tools.BACKGROUND.clear()
        __import__('shutil').rmtree(self.folder, True)

    def test_start_reports_status_url_and_log_then_stop_kills_it(self):
        started = time.time()
        result = tools.start_process(SERVER, name='web', wait=2)
        self.assertLess(time.time() - started, 5)                 # tidak menunggu proses selesai
        self.assertIn("Proses 'web'", result)
        self.assertIn('berjalan', result)
        self.assertIn('http://localhost:8123/', result)
        self.assertIn('Server siap', result)
        proc = tools.BACKGROUND['web']['proc']
        self.assertIsNone(proc.poll())
        self.assertIn('web', tools.list_processes())
        self.assertIn('Server siap', tools.read_process('web'))
        stopped = tools.stop_process('web')
        self.assertIn('dihentikan', stopped)
        self.assertIsNotNone(proc.poll())

    def test_stopping_also_kills_child_processes(self):
        command = f"sh -c {shlex.quote(SERVER)}; true"
        tools.start_process(command, name='anak', wait=1)
        pid = tools.BACKGROUND['anak']['proc'].pid
        tools.stop_process('anak')
        time.sleep(0.3)
        leftover = os.popen(f"pgrep -f 'time.sleep\\(120\\)'").read().split()
        self.assertEqual(leftover, [])
        self.assertIsNotNone(pid)

    def test_log_is_private_and_a_quick_exit_is_reported(self):
        result = tools.start_process(f"{shlex.quote(sys.executable)} -c \"import sys; print('gagal'); sys.exit(3)\"",
                                     name='cepat', wait=3)
        self.assertIn('selesai (exit 3)', result)
        self.assertIn('gagal', result)
        log = tools.BACKGROUND['cepat']['log']
        self.assertEqual(stat.S_IMODE(os.stat(log).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.folder).st_mode), 0o700)

    def test_declined_permission_starts_nothing(self):
        with patch.object(tools, '_confirm_permission', lambda *a, **k: False):
            self.assertIn('dibatalkan', tools.start_process(SERVER, name='x'))
        self.assertEqual(tools.BACKGROUND, {})

    def test_password_commands_are_refused(self):
        self.assertIn('password', tools.start_process('sudo npm run dev'))
        self.assertIn('Ditolak', tools.start_process('echo x | sudo -S ls'))
        self.assertEqual(tools.BACKGROUND, {})

    def test_limit_of_running_processes(self):
        with patch.object(tools, 'MAX_BACKGROUND', 2):
            tools.start_process(SERVER, name='a', wait=0)
            tools.start_process(SERVER, name='b', wait=0)
            self.assertIn('Hentikan salah satu', tools.start_process(SERVER, name='c', wait=0))

    def test_unknown_name_lists_known_ones_and_single_process_needs_no_name(self):
        tools.start_process(SERVER, name='satu', wait=1)
        self.assertIn('Server siap', tools.read_process())              # satu-satunya proses
        self.assertIn('satu', tools.read_process('tidak-ada'))
        self.assertIn('Tidak ada proses', tools.stop_process('tidak-ada'))

    def test_ansi_and_progress_bars_are_cleaned_from_the_log(self):
        path = os.path.join(self.folder, 'x.log')
        with open(path, 'wb') as handle:
            handle.write(b'\x1b[32mhijau\x1b[0m\nunduh 10%\runduh 100%\nakhir\n')
        tail = tools._log_tail(path)
        self.assertIn('hijau', tail)
        self.assertNotIn('\x1b', tail)
        self.assertIn('unduh 100%', tail)
        self.assertNotIn('unduh 10%', tail)

    def test_execute_command_timeout_points_to_start_process(self):
        with patch.object(tools, '_confirm_permission', lambda *a, **k: True):
            result = tools.execute_command('sleep 5', timeout=1)
        self.assertIn('start_process', result)


if __name__ == '__main__':
    unittest.main()
