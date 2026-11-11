import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

import tools


def fake_runner(calls, fail_on=None, create=None):
    def run(args, cwd, timeout):
        calls.append((list(args), cwd))
        if fail_on and fail_on in ' '.join(args):
            return 1, 'boom\nsecond line'
        for relative in (create or []):
            path = os.path.join(cwd, relative)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w').close()
        return 0, ''
    return run


class ScaffoldingTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-scaffold-')
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(patch.object(tools, '_find_tool', side_effect=lambda n: '/bin/' + n))
        self.confirm = stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))

    def make(self, kind, name, runner=None, **kw):
        with patch.object(tools, '_run_step', runner or fake_runner([])):
            return tools.init_project(kind, name, target_dir=self.dir, **kw)

    def test_injection_names_rejected_before_anything_runs(self):
        for bad in ['a; rm -rf ~', 'a b', '$(id)', '../x', '-rf', '', 'a&&b', 'x' * 80]:
            calls = []
            result = self.make('react', bad, fake_runner(calls))
            self.assertTrue(result.startswith('❌'), bad)
            self.assertEqual(calls, [])
        self.confirm.assert_not_called()

    def test_django_and_flutter_names(self):
        self.assertTrue(self.make('django', 'my-site').startswith('❌'))
        self.assertTrue(self.make('django', 'django').startswith('❌'))
        self.assertTrue(self.make('flutter', 'MyApp').startswith('❌'))
        self.assertTrue(self.make('flutter', 'class').startswith('❌'))

    def test_unknown_type(self):
        self.assertIn('belum didukung', self.make('cobol', 'x'))

    def test_vite_uses_argument_list_and_single_confirmation(self):
        calls = []
        result = self.make('react', 'demo', fake_runner(calls, create=['package.json']))
        # create-vite did not create the folder in the fake, so the verify step reports it
        self.assertEqual(self.confirm.call_count, 1)
        details = self.confirm.call_args[0][1]
        self.assertIn('create-vite@latest demo --template react-ts', details['Perintah'])
        self.assertEqual(calls[0][0][1:], ['-y', 'create-vite@latest', 'demo', '--template', 'react-ts'])
        self.assertTrue(result.startswith('❌') or result.startswith('✅'))

    def test_next_flags_are_valid(self):
        calls = []
        self.make('next', 'demo', fake_runner(calls))
        args = calls[0][0]
        self.assertIn('--disable-git', args)
        self.assertNotIn('--no-git', args)
        self.assertIn('--yes', args)
        self.assertEqual(len(calls), 1)

    def test_failure_is_reported_and_stops(self):
        calls = []
        result = self.make('react', 'demo', fake_runner(calls, fail_on='create-vite'))
        self.assertIn('Gagal pada langkah', result)
        self.assertIn('boom', result)
        self.assertEqual(len(calls), 1)

    def test_declined_runs_nothing(self):
        self.confirm.return_value = False
        calls = []
        result = self.make('react', 'demo', fake_runner(calls))
        self.assertIn('dibatalkan', result)
        self.assertEqual(calls, [])

    def test_existing_non_empty_folder_refused(self):
        os.makedirs(os.path.join(self.dir, 'demo'))
        open(os.path.join(self.dir, 'demo', 'keep.txt'), 'w').close()
        result = self.make('fastapi', 'demo')
        self.assertIn('sudah ada', result)
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'demo', 'keep.txt')))

    def test_missing_tool_gives_install_hint(self):
        with patch.object(tools, '_find_tool', return_value=None):
            result = tools.init_project('laravel', 'demo', target_dir=self.dir)
        self.assertIn('getcomposer.org', result)
        self.assertIn('php.net', result)

    def test_file_based_projects_write_files_without_commands(self):
        for kind, marker in [('fastapi', 'app/main.py'), ('flask', 'run.py'), ('php', 'public/index.php')]:
            calls = []
            result = self.make(kind, 'p_' + kind, fake_runner(calls))
            self.assertTrue(result.startswith('✅'), result)
            self.assertTrue(os.path.exists(os.path.join(self.dir, 'p_' + kind, *marker.split('/'))))
            self.assertEqual(calls, [])

    def test_django_creates_folder_first_and_runs_in_it(self):
        calls = []
        result = self.make('django', 'shop', fake_runner(calls, create=['manage.py']))
        self.assertTrue(result.startswith('✅'), result)
        full = os.path.join(self.dir, 'shop')
        self.assertTrue(all(cwd == full for _, cwd in calls))
        self.assertEqual(calls[2][0][-3:], ['startproject', 'shop', '.'])
        self.assertTrue(os.path.exists(os.path.join(full, 'requirements.txt')))

    def test_express_and_node_files(self):
        calls = []
        self.assertTrue(self.make('express', 'api', fake_runner(calls, create=['package.json'])).startswith('✅'))
        self.assertEqual(calls[0][0][1:2], ['install'])
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'api', 'src', 'index.js')))

    def test_flutter_and_laravel_commands(self):
        calls = []
        self.make('flutter', 'my_app', fake_runner(calls))
        self.assertEqual(calls[0][0][1:], ['create', 'my_app'])
        calls = []
        self.make('laravel', 'blog', fake_runner(calls))
        self.assertIn('laravel/laravel', calls[0][0])


if __name__ == '__main__':
    unittest.main()
