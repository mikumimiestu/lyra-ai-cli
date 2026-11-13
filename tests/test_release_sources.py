"""/update and the installers: download from the main server with SHA256SUMS, fall back to GitHub, never half-update."""
import hashlib
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import config

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = 'https://astbyte.my.id/'
GITHUB = config.GITHUB_UPDATE_URL


def release(version='9.9.9', tamper=None):
    files = {name: f'# {name} {version}\n'.encode() for name in config.FILES_TO_UPDATE}
    files['version.txt'] = version.encode()
    sums = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n' for name, data in files.items())
    if tamper:
        files[tamper] = b'# malicious\n'
    return files, sums


class FakeServer:
    def __init__(self, sources):
        self.sources = sources            # base -> (files, sums or None) | None (unreachable)
        self.requested = []

    def get(self, url, timeout=0):
        self.requested.append(url)
        for base, data in self.sources.items():
            if url.startswith(base):
                if data is None:
                    raise ConnectionError('down')
                files, sums = data
                name = url[len(base):]
                body = sums.encode() if name == 'SHA256SUMS' and sums else files.get(name)
                if body is None:
                    return Mock(status_code=404, content=b'', text='')
                return Mock(status_code=200, content=body, text=body.decode())
        raise ConnectionError('unknown host')


class UpdateTests(unittest.TestCase):
    def update(self, sources):
        folder = tempfile.mkdtemp(prefix='lyra-rel-')
        self.addCleanup(__import__('shutil').rmtree, folder, True)
        server = FakeServer(sources)
        with patch('requests.get', side_effect=server.get), patch.object(config, 'missing_packages', return_value=[]), \
             patch.dict(os.environ, {'LYRA_UPDATE_URL': ''}):
            result = config.perform_update(target_dir=folder)
        return result, folder, server

    def test_main_server_is_used_and_verified(self):
        (ok, message), folder, server = self.update({PRIMARY: release(), GITHUB: release('1.0.0')})
        self.assertTrue(ok, message)
        self.assertIn('astbyte.my.id', message)
        self.assertIn('terverifikasi', message)
        self.assertEqual(Path(folder, 'version.txt').read_text(), '9.9.9')
        self.assertFalse(any(url.startswith(GITHUB) for url in server.requested))

    def test_tampered_file_is_rejected_and_github_is_used(self):
        (ok, message), folder, _ = self.update({PRIMARY: release(tamper='tools.py'), GITHUB: (release('1.0.0')[0], None)})
        self.assertTrue(ok, message)
        self.assertIn('tanpa checksum', message)
        self.assertEqual(Path(folder, 'version.txt').read_text(), '1.0.0')
        self.assertNotIn('malicious', Path(folder, 'tools.py').read_text())

    def test_tampered_file_with_no_fallback_updates_nothing(self):
        (ok, message), folder, _ = self.update({PRIMARY: release(tamper='tools.py'), GITHUB: None})
        self.assertFalse(ok)
        self.assertIn('checksum', message)
        self.assertEqual(os.listdir(folder), [])

    def test_unreachable_main_server_falls_back_to_github(self):
        (ok, message), folder, _ = self.update({PRIMARY: None, GITHUB: (release('2.0.0')[0], None)})
        self.assertTrue(ok, message)
        self.assertEqual(Path(folder, 'version.txt').read_text(), '2.0.0')

    def test_missing_sha256sums_on_main_server_is_not_trusted_blindly(self):
        files, _ = release()
        (ok, message), folder, _ = self.update({PRIMARY: (files, None), GITHUB: None})
        self.assertFalse(ok)
        self.assertEqual(os.listdir(folder), [])

    def test_file_missing_from_a_release_never_leaves_a_mixed_install(self):
        files, sums = release()
        del files['memory.py']
        (ok, _), folder, _ = self.update({PRIMARY: (files, sums), GITHUB: None})
        self.assertFalse(ok)
        self.assertEqual(os.listdir(folder), [])

    def test_override_url_replaces_the_main_server(self):
        with patch.dict(os.environ, {'LYRA_UPDATE_URL': 'https://mirror.example/cli'}):
            self.assertEqual(config.update_sources()[0], ('https://mirror.example/cli/', True))
        with patch.dict(os.environ, {'LYRA_UPDATE_URL': ''}):
            self.assertEqual(config.update_sources()[0], (PRIMARY, True))

    def test_version_check_uses_main_server_then_github(self):
        server = FakeServer({PRIMARY: (release('9.9.9')[0], None), GITHUB: (release('1.0.0')[0], None)})
        with patch('requests.get', side_effect=server.get), patch.dict(os.environ, {'LYRA_UPDATE_URL': ''}):
            self.assertEqual(config.check_remote_version(), (True, '9.9.9'))
        server = FakeServer({PRIMARY: None, GITHUB: (release('9.9.8')[0], None)})
        with patch('requests.get', side_effect=server.get), patch.dict(os.environ, {'LYRA_UPDATE_URL': ''}):
            self.assertEqual(config.check_remote_version(), (True, '9.9.8'))
        server = FakeServer({PRIMARY: None, GITHUB: None})
        with patch('requests.get', side_effect=server.get), patch.dict(os.environ, {'LYRA_UPDATE_URL': ''}):
            self.assertEqual(config.check_remote_version(), (False, config.VERSION))

    def test_publish_script_ships_every_file_the_updater_downloads(self):
        text = (ROOT / 'deploy' / 'publish.sh').read_text(encoding='utf-8')
        listed = set(re.search(r'^FILES=\((.*)\)', text, re.M).group(1).split()) | {'version.txt'}
        self.assertTrue(set(config.FILES_TO_UPDATE) <= listed, set(config.FILES_TO_UPDATE) - listed)

    def test_deploy_scripts_have_valid_syntax(self):
        for name in ('publish.sh', 'setup-vps.sh'):
            self.assertEqual(subprocess.run(['bash', '-n', str(ROOT / 'deploy' / name)]).returncode, 0, name)


def stub(directory, name, body):
    path = Path(directory, name)
    if path.exists() or path.is_symlink():
        path.unlink()
    path.write_text('#!/bin/bash\n' + body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class InstallShDownloadTests(unittest.TestCase):
    FILES = ['app.py', 'styling.py', 'spinner.py', 'tools.py', 'config.py', 'memory.py', 'reminder.py', 'version.txt']

    def setUp(self):
        self.bin = tempfile.mkdtemp(prefix='lyra-dl-stubs-')
        self.out = tempfile.mkdtemp(prefix='lyra-dl-out-')
        self.addCleanup(__import__('shutil').rmtree, self.bin, True)
        self.addCleanup(__import__('shutil').rmtree, self.out, True)
        for tool in ('awk', 'cut', 'rm', 'shasum', 'sha256sum', 'mkdir', 'cat', 'tr'):
            for folder in ('/usr/bin', '/bin'):
                if os.path.exists(f'{folder}/{tool}'):
                    os.symlink(f'{folder}/{tool}', os.path.join(self.bin, tool))
                    break
        self.data = Path(self.bin, 'server')
        for host in ('main', 'github'):
            Path(self.data, host).mkdir(parents=True)
            for name in self.FILES:
                Path(self.data, host, name).write_text(f'# {name} from {host}\n')
        self.sums()
        # curl stub: URL -> file under server/<host>/; a missing file or host marked down fails like curl -f.
        stub(self.bin, 'curl', '''
dest=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) dest="$2"; shift 2;; -*) shift;; *) url="$1"; shift;; esac; done
case "$url" in https://astbyte.my.id/*) host=main;; https://raw.githubusercontent.com/*) host=github;; *) exit 6;; esac
[ -e "%s/down-$host" ] && exit 7
file="%s/$host/${url##*/}"
[ -f "$file" ] || exit 22
cp "$file" "$dest"
''' % (self.data, self.data))
        stub(self.bin, 'cp', 'exec /bin/cp "$@"')

    def sums(self):
        lines = []
        for name in self.FILES:
            digest = hashlib.sha256(Path(self.data, 'main', name).read_bytes()).hexdigest()
            lines.append(f'{digest}  {name}')
        Path(self.data, 'main', 'SHA256SUMS').write_text('\n'.join(lines) + '\n')

    def run_download(self):
        script = f'source "{ROOT / "install.sh"}"\ndownload_release "{self.out}"'
        return subprocess.run(['/bin/bash', '-c', script], env={'PATH': self.bin, 'AMAGI_INSTALL_SOURCE_ONLY': '1'},
                              capture_output=True, text=True, timeout=30)

    def test_main_server_with_matching_checksums(self):
        result = self.run_download()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Terverifikasi', result.stdout)
        self.assertIn('from main', Path(self.out, 'app.py').read_text())

    def test_tampered_file_falls_back_to_github(self):
        Path(self.data, 'main', 'tools.py').write_text('# evil\n')
        result = self.run_download()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Checksum tools.py tidak cocok', result.stderr)
        self.assertIn('from github', Path(self.out, 'tools.py').read_text())

    def test_main_server_down_falls_back_to_github(self):
        Path(self.data, 'down-main').write_text('')
        result = self.run_download()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('from github', Path(self.out, 'app.py').read_text())

    def test_everything_down_fails(self):
        Path(self.data, 'down-main').write_text('')
        Path(self.data, 'down-github').write_text('')
        self.assertNotEqual(self.run_download().returncode, 0)

    def test_file_not_listed_in_sums_is_rejected(self):
        sums = Path(self.data, 'main', 'SHA256SUMS')
        sums.write_text(''.join(l + '\n' for l in sums.read_text().splitlines() if not l.endswith('memory.py')))
        result = self.run_download()
        self.assertIn('memory.py tidak ada di SHA256SUMS', result.stderr)
        self.assertIn('from github', Path(self.out, 'memory.py').read_text())


class InstallPs1DownloadTests(unittest.TestCase):
    text = (ROOT / 'install.ps1').read_text(encoding='utf-8')

    def test_downloads_verified_then_falls_back(self):
        self.assertIn('https://astbyte.my.id', self.text)
        self.assertIn('Get-FileHash', self.text)
        self.assertIn('SHA256SUMS', self.text)
        self.assertIn('raw.githubusercontent.com/$GITHUB_REPO/main', self.text)
        self.assertLess(self.text.index('Get-Release $BASE_URL'), self.text.index('raw.githubusercontent.com/$GITHUB_REPO/main" $staging'))

    def test_usage_comment_points_to_the_new_address(self):
        self.assertIn('iwr -useb https://astbyte.my.id/install.ps1 | iex', self.text)


if __name__ == '__main__':
    unittest.main()
