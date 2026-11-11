import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, '.github', 'workflows', 'ci.yml')


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return handle.read()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        try:
            import yaml
        except ImportError:
            self.skipTest('PyYAML not installed')
        with open(WORKFLOW, encoding='utf-8') as handle:
            self.config = yaml.safe_load(handle)

    def test_expected_jobs_exist_and_cover_all_three_systems(self):
        jobs = self.config['jobs']
        self.assertEqual(set(jobs), {'tests', 'compat', 'install-unix', 'install-windows', 'package'})
        self.assertEqual(set(jobs['tests']['strategy']['matrix']['os']), {'ubuntu-latest', 'macos-latest', 'windows-latest'})
        self.assertFalse(jobs['tests']['strategy']['fail-fast'])
        self.assertEqual(jobs['install-windows']['runs-on'], 'windows-latest')

    def test_it_runs_on_pushes_and_pull_requests(self):
        triggers = self.config.get('on', self.config.get(True))        # PyYAML reads the bare word `on` as True
        self.assertIn('push', triggers)
        self.assertIn('pull_request', triggers)

    def test_the_test_job_runs_the_whole_suite(self):
        steps = self.config['jobs']['tests']['steps']
        self.assertTrue(any('unittest discover -s tests' in str(step.get('run', '')) for step in steps))
        self.assertTrue(any('prompt_toolkit' in str(step.get('run', '')) for step in steps))

    def test_every_step_uses_pinned_major_versions_of_official_actions(self):
        for name, job in self.config['jobs'].items():
            for step in job['steps']:
                if 'uses' in step:
                    self.assertRegex(step['uses'], r'^actions/[a-z-]+@v\d+$', (name, step['uses']))

    def test_the_token_is_read_only(self):
        self.assertEqual(self.config['permissions'], {'contents': 'read'})


class InstallerSmokeTests(unittest.TestCase):
    """The commands CI runs after installing must match where the installers put the command."""

    def test_unix_wrapper_location_matches_the_smoke_test(self):
        self.assertIn('"$HOME/.local/bin/amagi"', read('install.sh'))
        self.assertIn('$HOME/.local/bin/amagi', read('.github/workflows/ci.yml'))

    def test_windows_wrapper_location_matches_the_smoke_test(self):
        self.assertRegex(read('install.ps1'), r'Join-Path \$HOME "\.local\\bin"')
        self.assertIn('amagi.cmd', read('install.ps1'))
        self.assertIn(r'%USERPROFILE%\.local\bin\amagi.cmd', read('.github/workflows/ci.yml'))

    def test_installers_run_in_local_mode_when_the_files_are_next_to_them(self):
        self.assertIn('Test-Path "app.py"', read('install.ps1'))
        self.assertIn('[ -f "$file" ]', read('install.sh'))

    def test_the_syntax_check_in_ci_matches_the_documented_minimum(self):
        self.assertIn('feature_version=(3, 7)', read('.github/workflows/ci.yml'))
        self.assertIn('python_requires=">=3.7"', read('setup.py'))


if __name__ == '__main__':
    unittest.main()
