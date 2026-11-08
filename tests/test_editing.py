import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import styling
import tools

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


class Base(unittest.TestCase):
    def setUp(self):
        self.addCleanup(tools.APPROVAL.set, 'ask')
        self.addCleanup(tools.UNDO.clear)
        tools.UNDO.clear()
        tools.APPROVAL.set('edits')                     # file changes need no prompt in this mode
        self.folder = tempfile.mkdtemp(prefix='lyra-edit-')
        self.addCleanup(__import__('shutil').rmtree, self.folder, True)

    def path(self, name):
        return os.path.join(self.folder, name)

    def write(self, name, text, newline=None):
        with open(self.path(name), 'w', encoding='utf-8', newline=newline) as handle:
            handle.write(text)
        return self.path(name)


class EditFileTests(Base):
    def test_replaces_exact_text_once_and_keeps_the_rest(self):
        target = self.write('a.py', 'x = 1\ny = 2\nz = 3\n')
        with quiet():
            result = tools.edit_file(target, 'y = 2', 'y = 20')
        self.assertIn('1 penggantian', result)
        self.assertEqual(Path(target).read_text(), 'x = 1\ny = 20\nz = 3\n')

    def test_ambiguous_text_is_refused_unless_replace_all(self):
        target = self.write('a.txt', 'a\nb\na\n')
        with quiet():
            refused = tools.edit_file(target, 'a', 'c')
            self.assertIn('ditemukan 2 kali', refused)
            self.assertEqual(Path(target).read_text(), 'a\nb\na\n')
            done = tools.edit_file(target, 'a', 'c', replace_all=True)
        self.assertIn('2 penggantian', done)
        self.assertEqual(Path(target).read_text(), 'c\nb\nc\n')

    def test_missing_text_gives_a_whitespace_hint_and_changes_nothing(self):
        target = self.write('a.py', 'def f():\n    return 1\n')
        with quiet():
            wrong = tools.edit_file(target, 'return  1', 'return 2')
            hint = tools.edit_file(target, '\treturn 1', 'return 2')
        self.assertIn('tidak ditemukan', wrong)
        self.assertIn('tidak ditemukan', hint)
        self.assertIn('indentasi', hint)
        self.assertEqual(Path(target).read_text(), 'def f():\n    return 1\n')

    def test_argument_and_file_errors(self):
        target = self.write('a.txt', 'abc')
        with quiet():
            self.assertIn('Error', tools.edit_file(target, '', 'x'))
            self.assertIn('Error', tools.edit_file(target, 'abc', 'abc'))
            self.assertIn('Error', tools.edit_file(target, None, 'x'))
            self.assertIn('write_file', tools.edit_file(self.path('nope.txt'), 'a', 'b'))
            self.assertIn('direktori', tools.edit_file(self.folder, 'a', 'b'))
            Path(self.path('bin')).write_bytes(b'\xff\xfe\x00')
            self.assertIn('UTF-8', tools.edit_file(self.path('bin'), 'a', 'b'))

    def test_windows_line_endings_are_preserved(self):
        target = self.write('w.txt', 'satu\r\ndua\r\ntiga\r\n', newline='')
        with quiet():
            tools.edit_file(target, 'satu\ndua', 'SATU\nDUA')
        self.assertEqual(Path(target).read_bytes(), b'SATU\r\nDUA\r\ntiga\r\n')

    def test_declining_leaves_the_file_alone_and_records_nothing(self):
        tools.APPROVAL.set('ask')
        target = self.write('a.txt', 'lama')
        with quiet(), patch('builtins.input', return_value='n'):
            result = tools.edit_file(target, 'lama', 'baru')
        self.assertIn('dibatalkan', result)
        self.assertEqual(Path(target).read_text(), 'lama')
        self.assertEqual(tools.UNDO.items, [])

    def test_ask_mode_prompts_and_edit_modes_do_not(self):
        tools.APPROVAL.set('ask')
        target = self.write('a.txt', 'lama')
        with quiet(), patch('builtins.input', return_value='y') as prompt:
            tools.edit_file(target, 'lama', 'baru')
        prompt.assert_called_once()
        tools.APPROVAL.set('edits')
        with quiet(), patch('builtins.input', side_effect=AssertionError('no prompt')):
            tools.edit_file(target, 'baru', 'lagi')
        self.assertEqual(Path(target).read_text(), 'lagi')

    def test_diff_is_shown_before_writing(self):
        tools.APPROVAL.set('ask')
        target = self.write('a.txt', 'lama\n')
        out = io.StringIO()
        def check(*args, **kwargs):
            self.assertIn('-lama', out.getvalue())
            self.assertIn('+baru', out.getvalue())
            return False
        with contextlib.redirect_stdout(out), patch.object(tools, '_confirm_permission', side_effect=check):
            tools.edit_file(target, 'lama', 'baru')


class SearchTests(Base):
    def make_tree(self):
        self.write('a.py', 'import os\ndef halo():\n    return "Halo"\n')
        self.write('b.txt', 'halo dunia\nHALO lagi\n')
        os.makedirs(self.path('sub'))
        self.write('sub/c.py', 'print("halo")\n')
        for skipped in ('node_modules', '.git', '__pycache__'):
            os.makedirs(self.path(skipped))
            self.write(f'{skipped}/x.py', 'halo tersembunyi\n')
        Path(self.path('bin.dat')).write_bytes(b'halo\x00biner')

    def test_regex_search_reports_file_line_and_text(self):
        self.make_tree()
        result = tools.search('halo', self.folder)
        self.assertIn('a.py:2: def halo():', result)
        self.assertIn('b.txt:1: halo dunia', result)
        self.assertIn(os.path.join('sub', 'c.py') + ':1:', result)
        self.assertNotIn('tersembunyi', result)            # junk folders are skipped
        self.assertNotIn('bin.dat', result)                # binary files are skipped
        self.assertNotIn('HALO lagi', result)              # case sensitive by default

    def test_ignore_case_and_glob_narrow_the_search(self):
        self.make_tree()
        self.assertIn('HALO lagi', tools.search('halo', self.folder, ignore_case=True))
        only_py = tools.search('halo', self.folder, glob='*.py')
        self.assertNotIn('b.txt', only_py)
        self.assertIn('a.py', only_py)

    def test_glob_without_pattern_lists_files(self):
        self.make_tree()
        listing = tools.search('', self.folder, glob='*.py').splitlines()
        self.assertEqual(sorted(listing), sorted(['a.py', os.path.join('sub', 'c.py')]))

    def test_limits_errors_and_single_file(self):
        self.write('many.txt', '\n'.join('baris halo %d' % i for i in range(50)))
        result = tools.search('halo', self.folder, max_results=5)
        self.assertEqual(len([l for l in result.splitlines() if l.startswith('many.txt')]), 5)
        self.assertIn('dipotong di 5 hasil', result)
        self.assertIn('regex tidak valid', tools.search('(', self.folder))
        self.assertIn('Error', tools.search('', self.folder))
        self.assertIn('tidak ditemukan', tools.search('x', self.path('hilang')))
        self.assertIn('Tidak ada hasil', tools.search('tidak-ada-sama-sekali', self.folder))
        self.assertIn('many.txt:3: baris halo 2', tools.search('halo 2$', self.path('many.txt')))

    def test_long_lines_are_trimmed(self):
        self.write('long.txt', 'halo ' + 'x' * 500)
        self.assertLess(len(tools.search('halo', self.folder)), 260)

    def test_activity_labels_and_grouping(self):
        self.assertEqual(styling.activity_group('search', {}), 'Eksplorasi')
        self.assertEqual(styling.activity_group('edit_file', {}), 'Perubahan')
        self.assertEqual(styling.tool_activity('search', {'pattern': 'halo'}), 'Cari · halo')
        self.assertEqual(styling.tool_activity('search', {'glob': '*.py'}), 'Cari · *.py')
        self.assertEqual(styling.tool_activity('edit_file', {'filepath': 'a.py'}), 'Ubah · a.py')


class UndoTests(Base):
    def test_undo_restores_an_edit_and_a_rewrite(self):
        target = self.write('a.txt', 'asli')
        with quiet():
            tools.edit_file(target, 'asli', 'edit')
            tools.write_file(target, 'tulis ulang')
            self.assertEqual(len(tools.UNDO.items), 2)
            self.assertIn('Dikembalikan', tools.undo_last())
            self.assertEqual(Path(target).read_text(), 'edit')
            self.assertIn('Dikembalikan', tools.undo_last())
        self.assertEqual(Path(target).read_text(), 'asli')
        with quiet():
            self.assertIn('Belum ada', tools.undo_last())

    def test_undo_removes_a_file_lyra_created(self):
        target = self.path('baru.txt')
        with quiet():
            tools.write_file(target, 'isi')
            self.assertTrue(os.path.exists(target))
            self.assertIn('Dihapus', tools.undo_last())
        self.assertFalse(os.path.exists(target))

    def test_undo_warns_when_the_file_changed_afterwards_and_asks_first(self):
        target = self.write('a.txt', 'asli')
        with quiet():
            tools.edit_file(target, 'asli', 'lyra')
        Path(target).write_text('diubah pengguna')
        tools.APPROVAL.set('ask')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch('builtins.input', return_value='n'):
            result = tools.undo_last()
        self.assertIn('dibatalkan', result)
        self.assertIn('diubah setelah perubahan Lyra', styling.strip_ansi(out.getvalue()))
        self.assertEqual(Path(target).read_text(), 'diubah pengguna')
        self.assertEqual(len(tools.UNDO.items), 1)           # still undoable
        with quiet(), patch('builtins.input', return_value='y'):
            tools.undo_last()
        self.assertEqual(Path(target).read_text(), 'asli')

    def test_stack_is_bounded_and_oversized_files_are_not_backed_up(self):
        for i in range(tools.MAX_UNDO + 5):
            tools.UNDO.record('/x/%d' % i, b'a', b'b', 'write_file')
        self.assertEqual(len(tools.UNDO.items), tools.MAX_UNDO)
        self.assertEqual(tools.UNDO.items[-1]['path'], '/x/%d' % (tools.MAX_UNDO + 4))
        self.assertFalse(tools.UNDO.record('/big', b'x' * (tools.UNDO_LIMIT_BYTES + 1), b'y', 'write_file'))

    def test_list_shows_newest_first(self):
        with quiet():
            tools.write_file(self.path('one.txt'), '1')
            tools.write_file(self.path('two.txt'), '2')
        lines = tools.describe_undo_stack()
        self.assertTrue(lines[0].startswith('1.') and 'two.txt' in lines[0] and '(baru)' in lines[0])
        self.assertIn('one.txt', lines[1])


if __name__ == '__main__':
    unittest.main()
