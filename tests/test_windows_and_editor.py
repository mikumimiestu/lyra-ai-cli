import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

import app
import config
import styling


class WindowsColourTests(unittest.TestCase):
    """Windows terminals set neither COLORTERM nor TERM, which used to hide the mascot."""

    def depth(self, env, build=None, name='nt'):
        clean = {key: '' for key in ('COLORTERM', 'TERM', 'TERM_PROGRAM', 'WT_SESSION', 'ConEmuANSI')}
        clean.update(env)
        version = Mock(build=build) if build is not None else None
        with patch.object(styling, 'USE_COLOR', True), patch.object(styling.os, 'name', name), patch.dict(os.environ, clean), \
             patch.object(sys, 'getwindowsversion', create=True, side_effect=(lambda: version) if version else AttributeError):
            return styling.color_depth()

    def test_windows_terminal_and_vscode_and_conemu_are_true_colour(self):
        self.assertEqual(self.depth({'WT_SESSION': 'abc-123'}), 24)
        self.assertEqual(self.depth({'ConEmuANSI': 'ON'}), 24)
        self.assertEqual(self.depth({'TERM_PROGRAM': 'vscode'}), 24)

    def test_the_classic_console_counts_from_windows_10_build_14931(self):
        self.assertEqual(self.depth({}, build=19045), 24)
        self.assertEqual(self.depth({}, build=22631), 24)
        self.assertEqual(self.depth({}, build=14931), 24)
        self.assertEqual(self.depth({}, build=10586), 0)
        self.assertEqual(self.depth({}), 0)                                  # version unknown: stay plain

    def test_colour_off_still_wins_and_other_systems_are_untouched(self):
        with patch.object(styling, 'USE_COLOR', False), patch.object(styling.os, 'name', 'nt'), patch.dict(os.environ, {'WT_SESSION': 'x'}):
            self.assertEqual(styling.color_depth(), 0)
        self.assertEqual(self.depth({'TERM': 'xterm-256color'}, name='posix'), 8)
        self.assertEqual(self.depth({'TERM': 'vt100'}, name='posix'), 0)
        self.assertEqual(self.depth({'WT_SESSION': 'x'}, name='posix'), 0)    # that variable means nothing off Windows

    def test_windows_terminal_header_shows_the_head(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(styling, 'USE_COLOR', True), patch.object(styling.os, 'name', 'nt'), \
             patch.dict(os.environ, {'WT_SESSION': 'x', 'COLORTERM': '', 'TERM': ''}), patch.object(styling, 'get_terminal_width', return_value=100), \
             patch.object(styling, 'terminal_rows', return_value=30), patch.object(styling, 'unicode_terminal', return_value=True):
            styling.render_header('Lyra Eurydice 6', 'medium', '~')
        plain = styling.strip_ansi(out.getvalue())
        self.assertEqual(len([l for l in plain.splitlines() if '▀' in l or '▄' in l]), styling.PET_ROWS)


class HeadOnlySpriteTests(unittest.TestCase):
    def test_the_sprite_is_ten_rows_tall_with_ears_and_a_face(self):
        rows = styling.pet_art(24)
        self.assertEqual(len(rows), 10)
        top = styling.strip_ansi(rows[0]).strip()
        self.assertTrue(top)                                                 # the ear tips are not cropped away
        self.assertEqual({styling.str_width(r) for r in rows}, {styling.PET_COLS})
        used = {ch for row in styling.PET_SPRITE for ch in row}
        self.assertNotIn('k', used)                                          # no black collar: the body is gone
        self.assertIn('p', used)                                             # blush
        self.assertIn('r', used)                                             # mouth

    def test_the_header_is_shorter_than_before(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(styling, 'color_depth', return_value=24), patch.object(styling, 'get_terminal_width', return_value=100), \
             patch.object(styling, 'terminal_rows', return_value=20), patch.object(styling, 'unicode_terminal', return_value=True):
            styling.render_header('Lyra Orpheus 6', 'medium', '/work')
        lines = [l for l in styling.strip_ansi(out.getvalue()).splitlines() if l.strip()]
        self.assertEqual(len(lines), 10)


class PlainInputFallbackTests(unittest.TestCase):
    def editor(self):
        with patch.object(sys.stdin, 'isatty', return_value=False):
            return styling.TerminalInput(lambda: {})

    def test_missing_prompt_toolkit_gets_one_clear_hint_and_no_ascii_frame(self):
        editor = self.editor()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(styling, 'EDITOR_AVAILABLE', False), patch('builtins.input', return_value='halo'):
            self.assertEqual(editor.read(), 'halo')
            self.assertEqual(editor.read(), 'halo')
        plain = styling.strip_ansi(out.getvalue())
        self.assertEqual(plain.count('prompt_toolkit belum terpasang'), 1)       # said once, not on every prompt
        self.assertIn('-m pip install prompt_toolkit', plain)
        self.assertNotIn('+---', plain)
        self.assertNotIn('pesan', plain)

    def test_pipes_with_the_library_installed_stay_quiet(self):
        editor = self.editor()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch('builtins.input', return_value='x'):
            editor.read()
        self.assertNotIn('prompt_toolkit', out.getvalue())


class EditorDependencyTests(unittest.TestCase):
    def check(self, answer, config_data=None, tty=True, available=False, install=(True, 'terpasang')):
        data = dict(config_data or {})
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(app, 'EDITOR_AVAILABLE', available), \
             patch.object(sys.stdin, 'isatty', return_value=tty), patch.object(sys.stdout, 'isatty', return_value=tty), \
             patch('builtins.input', return_value=answer) as ask, patch.object(app, 'install_packages', return_value=install) as pip, \
             patch.object(app, 'restart_application') as restart, patch.object(app, 'save_config') as save, patch.object(app, 'Spinner'):
            app.check_editor_dependency(data)
        return styling.strip_ansi(out.getvalue()), data, ask, pip, restart, save

    def test_yes_installs_the_package_and_restarts(self):
        out, data, ask, pip, restart, _ = self.check('y')
        pip.assert_called_once_with(['prompt_toolkit>=3.0.36,<4'])
        restart.assert_called_once()
        self.assertIn('Editor lengkap belum aktif', out)
        self.assertIn('terpasang', out)
        self.assertNotIn('editor_prompt_declined', data)

    def test_no_is_remembered_and_never_asked_again(self):
        out, data, ask, pip, restart, save = self.check('n')
        pip.assert_not_called()
        restart.assert_not_called()
        self.assertTrue(data['editor_prompt_declined'])
        save.assert_called_once()
        out, data, ask, pip, *_ = self.check('y', config_data={'editor_prompt_declined': True})
        ask.assert_not_called()
        pip.assert_not_called()

    def test_a_failed_install_shows_the_reason_and_the_manual_command(self):
        out, data, ask, pip, restart, _ = self.check('y', install=(False, 'No matching distribution'))
        restart.assert_not_called()
        self.assertIn('Gagal memasang: No matching distribution', out)
        self.assertIn('-m pip install prompt_toolkit', out)

    def test_nothing_is_asked_when_it_is_installed_or_there_is_no_terminal(self):
        for kwargs in (dict(available=True), dict(tty=False)):
            out, data, ask, pip, restart, _ = self.check('y', **kwargs)
            ask.assert_not_called()
            pip.assert_not_called()
            self.assertEqual(out, '')


class PackageRepairTests(unittest.TestCase):
    def test_missing_packages_come_from_what_cannot_be_imported(self):
        with patch('importlib.util.find_spec', side_effect=lambda name: None if name == 'prompt_toolkit' else object()):
            self.assertEqual(config.missing_packages(), ['prompt_toolkit>=3.0.36,<4'])
        with patch('importlib.util.find_spec', return_value=object()):
            self.assertEqual(config.missing_packages(), [])

    def test_install_runs_pip_with_this_interpreter(self):
        with patch.object(subprocess, 'run', return_value=Mock(returncode=0, stdout='', stderr='')) as run:
            self.assertEqual(config.install_packages(['prompt_toolkit>=3.0.36,<4']), (True, 'terpasang'))
        command = run.call_args[0][0]
        self.assertEqual(command[:4], [sys.executable, '-m', 'pip', 'install'])
        self.assertIn('prompt_toolkit>=3.0.36,<4', command)
        with patch.object(subprocess, 'run', return_value=Mock(returncode=1, stdout='', stderr='ruwet\nERROR: tidak ada jaringan\n')):
            self.assertEqual(config.install_packages(['x']), (False, 'ERROR: tidak ada jaringan'))
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('pip', 1)):
            self.assertFalse(config.install_packages(['x'])[0])
        with patch.object(subprocess, 'run', side_effect=OSError('tidak ada pip')):
            self.assertEqual(config.install_packages(['x']), (False, 'tidak ada pip'))

    def update(self, missing, install=(True, 'terpasang')):
        folder = tempfile.mkdtemp(prefix='lyra-update-')
        self.addCleanup(__import__('shutil').rmtree, folder, True)
        with patch('requests.get', return_value=Mock(status_code=200, text='# isi')), patch.object(config, 'missing_packages', return_value=missing), \
             patch.object(config, 'install_packages', return_value=install) as pip:
            result = config.perform_update(target_dir=folder)
        return result, pip

    def test_update_repairs_a_missing_editor_package(self):
        (ok, message), pip = self.update(['prompt_toolkit>=3.0.36,<4'])
        self.assertTrue(ok)
        pip.assert_called_once_with(['prompt_toolkit>=3.0.36,<4'])
        self.assertIn('ikut dipasang', message)

    def test_update_reports_a_failed_repair_without_failing_the_update(self):
        (ok, message), _ = self.update(['prompt_toolkit>=3.0.36,<4'], install=(False, 'offline'))
        self.assertTrue(ok)
        self.assertIn('belum terpasang (offline)', message)

    def test_update_does_not_touch_pip_when_nothing_is_missing(self):
        (ok, message), pip = self.update([])
        pip.assert_not_called()
        self.assertNotIn('paket', message)


if __name__ == '__main__':
    unittest.main()
