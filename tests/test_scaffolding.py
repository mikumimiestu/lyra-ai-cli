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


class ScaffoldBase(unittest.TestCase):
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


class ScaffoldingTests(ScaffoldBase):

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


VITE_REACT = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
"""


class TailwindTests(ScaffoldBase):
    def read(self, *parts):
        return open(os.path.join(self.dir, *parts), encoding='utf-8').read()

    def vite_runner(self, calls, config=VITE_REACT, css='src/index.css'):
        def run(args, cwd, timeout):
            calls.append((list(args), cwd))
            if 'create-vite@latest' in args:
                root = os.path.join(cwd, args[args.index('create-vite@latest') + 1])
                os.makedirs(os.path.join(root, 'src'))
                open(os.path.join(root, 'package.json'), 'w').close()
                open(os.path.join(root, 'vite.config.ts'), 'w').write(config)
                open(os.path.join(root, *css.split('/')), 'w').write('body { margin: 0 }\n')
            return 0, ''
        return run

    def test_vite_react_gets_plugin_import_and_css(self):
        calls = []
        result = self.make('react', 'app1', self.vite_runner(calls), tailwind=True)
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn('Tailwind CSS v4 dipasang', result)
        self.assertEqual(calls[2][0][1:4], ['install', 'tailwindcss', '@tailwindcss/vite'])
        config = self.read('app1', 'vite.config.ts')
        self.assertIn("import tailwindcss from '@tailwindcss/vite'", config)
        self.assertIn('tailwindcss(),', config)
        self.assertIn('react()', config)
        self.assertEqual(self.read('app1', 'src', 'index.css'), '@import "tailwindcss";\n')
        self.assertIn('Tailwind CSS', self.confirm.call_args[0][1])

    def test_vite_patch_is_idempotent_and_handles_missing_plugins(self):
        calls = []
        self.make('vue', 'app2', self.vite_runner(calls, "import { defineConfig } from 'vite'\nexport default defineConfig({})\n", 'src/style.css'), tailwind=True)
        config = self.read('app2', 'vite.config.ts')
        self.assertIn('plugins: [tailwindcss()]', config)
        before = config
        self.assertIsNone(tools._patch_vite_config(os.path.join(self.dir, 'app2')))
        self.assertEqual(self.read('app2', 'vite.config.ts'), before)

    def test_unrecognised_vite_config_warns_instead_of_failing(self):
        calls = []
        result = self.make('svelte', 'app3', self.vite_runner(calls, 'module.exports = {}\n', 'src/app.css'), tailwind=True)
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn('Perlu dicek', result)

    def test_no_tailwind_leaves_vite_untouched(self):
        calls = []
        self.make('react', 'app4', self.vite_runner(calls), tailwind=False)
        self.assertEqual(len(calls), 2)
        self.assertNotIn('tailwind', self.read('app4', 'vite.config.ts'))

    def test_next_flag_follows_choice(self):
        calls = []
        self.make('next', 'n1', fake_runner(calls), tailwind=False)
        self.assertIn('--no-tailwind', calls[0][0])
        calls = []
        self.make('next', 'n2', fake_runner(calls))
        self.assertIn('--tailwind', calls[0][0])

    def test_flask_php_django_use_tailwind_cli(self):
        for kind, css in [('flask', ('app', 'static', 'src', 'input.css')), ('php', ('src', 'input.css'))]:
            calls = []
            result = self.make(kind, 't_' + kind, fake_runner(calls), tailwind=True)
            self.assertTrue(result.startswith('✅'), result)
            self.assertEqual(self.read('t_' + kind, *css), '@import "tailwindcss";\n')
            self.assertEqual([c[0][1] for c in calls], ['install', 'run'])
            self.assertIn('@tailwindcss/cli', calls[0][0])
        self.assertIn('tailwind.css', self.read('t_flask', 'app', 'templates', 'base.html'))
        self.assertIn('/css/tailwind.css', self.read('t_php', 'views', 'layouts', 'main.php'))

    def test_django_tailwind_patches_settings_and_urls(self):
        calls = []
        def runner(args, cwd, timeout):
            calls.append(list(args))
            if 'startproject' in args:
                os.makedirs(os.path.join(cwd, 'shop'))
                open(os.path.join(cwd, 'manage.py'), 'w').close()
                open(os.path.join(cwd, 'shop', 'settings.py'), 'w').write("TEMPLATES = [{\n 'DIRS': [],\n}]\n")
                open(os.path.join(cwd, 'shop', 'urls.py'), 'w').write("from django.urls import path\nurlpatterns = [\n]\n")
            return 0, ''
        result = self.make('django', 'shop', runner, tailwind=True)
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn("BASE_DIR / 'templates'", self.read('shop', 'shop', 'settings.py'))
        self.assertIn('STATICFILES_DIRS', self.read('shop', 'shop', 'settings.py'))
        self.assertIn('TemplateView', self.read('shop', 'shop', 'urls.py'))
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'shop', 'templates', 'home.html')))
        self.assertEqual(calls[-1][1:], ['run', 'build:css'])

    def test_laravel_and_unsupported_kinds_explain(self):
        def laravel(args, cwd, timeout):
            os.makedirs(os.path.join(cwd, 'lv'))
            open(os.path.join(cwd, 'lv', 'artisan'), 'w').close()
            return 0, ''
        self.assertIn('sudah memakai Tailwind', self.make('laravel', 'lv', laravel, tailwind=True))
        self.assertIn('tidak diterapkan', self.make('fastapi', 'fa', fake_runner([]), tailwind=True))

    def test_tailwind_failure_is_reported_but_project_remains(self):
        calls = []
        result = self.make('flask', 'tf', fake_runner(calls, fail_on='install'), tailwind=True)
        self.assertIn('hanya langkah Tailwind yang gagal', result)
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'tf', 'run.py')))


if __name__ == '__main__':
    unittest.main()
