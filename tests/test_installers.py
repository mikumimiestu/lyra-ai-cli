import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def declared_modules():
    syntax = ast.parse((ROOT / 'setup.py').read_text(encoding='utf-8'))
    call = next(node.value for node in syntax.body if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call) and node.value.func.id == 'setup')
    modules = next(ast.literal_eval(item.value) for item in call.keywords if item.arg == 'py_modules')
    return {name + '.py' for name in modules} | {'version.txt'}


class InstallerTests(unittest.TestCase):
    def test_powershell_file_list_is_a_flat_list_of_every_module(self):
        text = (ROOT / 'install.ps1').read_text(encoding='utf-8')
        line = next(line for line in text.splitlines() if line.startswith('$FILES'))
        # ",," builds a nested array in PowerShell and breaks Join-Path.
        self.assertNotIn(',,', line.replace(' ', ''))
        self.assertEqual(set(re.findall(r'"([^"]+)"', line)), declared_modules())

    def test_bash_file_list_matches_modules(self):
        text = (ROOT / 'install.sh').read_text(encoding='utf-8')
        line = next(line for line in text.splitlines() if line.startswith('FILES='))
        self.assertEqual(set(re.findall(r'"([^"]+)"', line)), declared_modules())

    def test_updater_covers_every_module(self):
        import config
        self.assertTrue(declared_modules() <= set(config.FILES_TO_UPDATE))


if __name__ == '__main__':
    unittest.main()
