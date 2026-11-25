import sys
import unittest
from unittest.mock import patch

import styling
import tools


class DetectionTests(unittest.TestCase):
    def test_commands_that_ask_for_a_password(self):
        for command in ('sudo apt install x', 'ssh user@host', 'cd /x && sudo make install', 'ls | sudo tee f',
                        'FOO=1 ssh host', 'scp a b:c', 'su', 'passwd'):
            self.assertTrue(tools.command_needs_password(command), command)

    def test_ordinary_commands_do_not(self):
        for command in ('ls -la', 'echo su', 'cat su.txt', 'python3 ssh_check.py', 'git status', 'echo sudo is fun'):
            self.assertFalse(tools.command_needs_password(command), command)

    def test_password_in_the_command_is_refused(self):
        for command in ('echo hunter2 | sudo -S ls', 'sudo -S ls', 'sshpass -p x ssh h', 'cat p | sudo tee f'):
            with patch.object(tools, '_confirm_permission', side_effect=AssertionError('tidak boleh bertanya')):
                self.assertIn('Ditolak', tools.execute_command(command), command)


class RunningTests(unittest.TestCase):
    def run_cmd(self, command, tty, remote=None, runner=None):
        seen = {}

        def confirm(title, details, kind='command'):
            seen.update(details)
            return True

        with patch.object(tools, '_confirm_permission', confirm), \
                patch.object(tools, 'REMOTE_APPROVER', remote), \
                patch.object(sys.stdin, 'isatty', lambda: tty), patch.object(sys.stdout, 'isatty', lambda: tty), \
                patch.object(styling, 'TERMINAL_RUNNER', runner):
            return tools.execute_command(command), seen

    def test_a_password_command_runs_with_the_live_area_suspended_and_a_note(self):
        calls = []

        def runner(function):
            calls.append('suspended')
            return function()

        result, details = self.run_cmd('ssh -V', True, runner=runner)   # meminta password pada umumnya, tapi -V hanya mencetak versi
        self.assertIn('Exit Code:', result)
        self.assertEqual(calls, ['suspended'])
        self.assertIn('Lyra tidak melihatnya', details['Catatan'])

    def test_from_telegram_a_password_command_is_not_run(self):
        result, details = self.run_cmd('sudo true', True, remote=lambda *a: True)
        self.assertIn('diketik langsung di terminal', result)
        self.assertEqual(details, {})

    def test_without_a_terminal_a_password_command_is_not_run(self):
        result, _ = self.run_cmd('ssh host true', False)
        self.assertIn('diketik langsung di terminal', result)

    def test_ordinary_commands_do_not_wait_for_input(self):
        result, details = self.run_cmd('cat', False)          # reads stdin: must get EOF instead of hanging
        self.assertIn('Exit Code: 0', result)
        self.assertNotIn('Catatan', details)

    def test_git_never_asks_for_credentials_without_a_terminal(self):
        result, _ = self.run_cmd('echo $GIT_TERMINAL_PROMPT', False)
        self.assertIn('0', result)


if __name__ == '__main__':
    unittest.main()
