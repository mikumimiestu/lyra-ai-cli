"""install.sh: finding Python and offering to install it. Everything runs against stub commands in a
temporary PATH, so no package manager, sudo or Python is ever touched for real."""
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASH = '/bin/bash'


def write_exe(directory, name, body):
    path = Path(directory, name)
    if path.is_symlink() or path.exists():
        path.unlink()                      # never write through a symlink to a real tool
    path.write_text('#!/bin/bash\n' + body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class InstallShTests(unittest.TestCase):
    def setUp(self):
        self.bin = tempfile.mkdtemp(prefix='lyra-stubs-')
        self.log = Path(self.bin, 'calls.log')
        self.addCleanup(__import__('shutil').rmtree, self.bin, True)
        for tool in ('chmod', 'mkdir', 'touch'):          # the only real tools the stubs lean on
            for folder in ('/bin', '/usr/bin'):
                if os.path.exists(f'{folder}/{tool}'):
                    os.symlink(f'{folder}/{tool}', os.path.join(self.bin, tool))
                    break

    def run_script(self, snippet, env=None):
        full = {'PATH': self.bin, 'HOME': self.bin, 'AMAGI_INSTALL_SOURCE_ONLY': '1', 'LOG': str(self.log), 'AMAGI_PYTHON_PATHS': ''}
        full.update(env or {})
        script = f'source "{ROOT / "install.sh"}"\n{snippet}\n'
        return subprocess.run([BASH, '-c', script], env=full, capture_output=True, text=True, timeout=30)

    def good_python(self, name='python3', version_ok=True):
        write_exe(self.bin, name, f'[ "$1" = "-c" ] && exit {0 if version_ok else 1}\necho stub')

    def test_sourcing_installs_nothing_and_defines_functions(self):
        result = self.run_script('type ensure_python find_python install_python >/dev/null && echo defined')
        self.assertEqual(result.stdout.strip(), 'defined', result.stderr)

    def test_usable_python_is_found_without_any_prompt(self):
        self.good_python()
        result = self.run_script('ensure_python; echo "bin=$PYTHON_BIN"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'bin={self.bin}/python3', result.stdout)

    def test_too_old_or_broken_python_does_not_count(self):
        self.good_python(version_ok=False)
        self.assertNotEqual(self.run_script('find_python').returncode, 0)

    def test_a_working_python_later_in_the_list_is_used(self):
        self.good_python('python3', version_ok=False)
        self.good_python('python3.12')
        result = self.run_script('find_python')
        self.assertEqual(result.stdout.strip(), f'{self.bin}/python3.12')

    def linux_stubs(self, manager='apt-get'):
        write_exe(self.bin, 'uname', 'echo Linux')
        write_exe(self.bin, 'id', 'echo 1000')
        write_exe(self.bin, 'sudo', '"$@"')
        # The fake package manager "installs" Python by creating the stub, and records its arguments.
        write_exe(self.bin, manager, f'echo "{manager} $*" >> "$LOG"\n'
                  f'[ "$1" = "update" ] && exit 0\n'
                  f'printf \'#!/bin/bash\\n[ "$1" = "-c" ] && exit 0\\n\' > "{self.bin}/python3"; chmod +x "{self.bin}/python3"')

    def test_linux_apt_installs_python_with_venv_and_pip_after_consent(self):
        self.linux_stubs('apt-get')
        result = self.run_script('ensure_python; echo "bin=$PYTHON_BIN"', {'AMAGI_ASSUME_YES': '1'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('apt-get install -y python3 python3-venv python3-pip', self.log.read_text())
        self.assertIn(f'bin={self.bin}/python3', result.stdout)

    def test_other_linux_package_managers(self):
        for manager, expected in [('dnf', 'dnf install -y python3 python3-pip'),
                                  ('pacman', 'pacman -S --noconfirm python python-pip'),
                                  ('zypper', 'zypper --non-interactive install python3 python3-pip'),
                                  ('apk', 'apk add python3 py3-pip')]:
            with self.subTest(manager=manager):
                for old in os.listdir(self.bin):
                    if old not in ('chmod', 'mkdir', 'touch'):
                        os.remove(os.path.join(self.bin, old))
                self.linux_stubs(manager)
                result = self.run_script('ensure_python', {'AMAGI_ASSUME_YES': '1'})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(expected, self.log.read_text())

    def test_declining_installs_nothing_and_stops(self):
        self.linux_stubs()
        reply = Path(self.bin, 'tty')
        reply.write_text('n\n')
        result = self.run_script('ensure_python', {'AMAGI_TTY': str(reply)})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertIn('python.org/downloads', result.stdout)

    def test_enter_alone_means_yes(self):
        self.linux_stubs()
        reply = Path(self.bin, 'tty')
        reply.write_text('\n')
        result = self.run_script('ensure_python', {'AMAGI_TTY': str(reply)})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.log.exists())

    def test_without_a_terminal_it_refuses_instead_of_installing_silently(self):
        self.linux_stubs()
        result = self.run_script('ensure_python', {'AMAGI_TTY': '/nonexistent/tty'})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertIn('AMAGI_ASSUME_YES=1', result.stdout)

    def test_failed_installation_is_reported(self):
        write_exe(self.bin, 'uname', 'echo Linux')
        write_exe(self.bin, 'id', 'echo 0')
        write_exe(self.bin, 'apt-get', '[ "$1" = "update" ] && exit 0\nexit 100')
        result = self.run_script('ensure_python', {'AMAGI_ASSUME_YES': '1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('gagal', result.stdout)

    def test_macos_prefers_homebrew(self):
        write_exe(self.bin, 'uname', 'echo Darwin')
        write_exe(self.bin, 'brew', f'echo "brew $*" >> "$LOG"\n'
                  f'printf \'#!/bin/bash\\n[ "$1" = "-c" ] && exit 0\\n\' > "{self.bin}/python3"; chmod +x "{self.bin}/python3"')
        result = self.run_script('ensure_python', {'AMAGI_ASSUME_YES': '1'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('brew install python@3.12', self.log.read_text())

    def test_macos_without_homebrew_uses_the_official_pkg(self):
        write_exe(self.bin, 'uname', 'echo Darwin')
        write_exe(self.bin, 'id', 'echo 1000')
        write_exe(self.bin, 'sudo', '"$@"')
        write_exe(self.bin, 'mktemp', f'mkdir -p "{self.bin}/dl"; echo "{self.bin}/dl"')
        write_exe(self.bin, 'rm', 'exit 0')
        write_exe(self.bin, 'curl', 'echo "curl $*" >> "$LOG"; touch "$4"')
        write_exe(self.bin, 'installer', f'echo "installer $*" >> "$LOG"\n'
                  f'printf \'#!/bin/bash\\n[ "$1" = "-c" ] && exit 0\\n\' > "{self.bin}/python3"; chmod +x "{self.bin}/python3"')
        result = self.run_script('ensure_python', {'AMAGI_ASSUME_YES': '1'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.log.read_text()
        self.assertIn('https://www.python.org/ftp/python/3.12.8/python-3.12.8-macos11.pkg', calls)
        self.assertIn('installer -pkg', calls)

    def test_installer_uses_the_found_python_for_the_venv(self):
        text = (ROOT / 'install.sh').read_text(encoding='utf-8')
        self.assertIn('"$PYTHON_BIN" -m venv', text)
        self.assertNotIn('\npython3 -m venv', text)


class InstallPs1Tests(unittest.TestCase):
    """PowerShell is not available on every machine, so these only check the script's structure."""
    text = (ROOT / 'install.ps1').read_text(encoding='utf-8')

    def test_installs_python_with_winget_then_python_org(self):
        self.assertIn('winget install --id Python.Python.3.12', self.text)
        self.assertIn('https://www.python.org/ftp/python/$PY_FULL/python-$PY_FULL-$arch.exe', self.text)
        self.assertIn('InstallAllUsers=0', self.text)          # per user, no administrator rights
        self.assertIn('PrependPath=1', self.text)

    def test_store_alias_and_old_versions_are_not_accepted(self):
        self.assertIn('WindowsApps', self.text)
        self.assertIn('sys.version_info >= (3, 7)', self.text)

    def test_asks_before_installing_and_refreshes_path_after(self):
        self.assertIn('Confirm-PythonInstall', self.text)
        self.assertIn('AMAGI_ASSUME_YES', self.text)
        self.assertIn('Update-SessionPath', self.text)

    def test_py_launcher_gets_its_flag_when_used_for_venv(self):
        self.assertIn('@pythonArgs -m venv', self.text)
        self.assertIn('@("-3")', self.text)

    def test_braces_and_parentheses_balance(self):
        code = re.sub(r'"(?:`.|[^"`])*"|\'[^\']*\'', '', self.text)
        code = re.sub(r'#.*', '', code)
        for open_, close in ('{}', '()'):
            self.assertEqual(code.count(open_), code.count(close), open_)


if __name__ == '__main__':
    unittest.main()
