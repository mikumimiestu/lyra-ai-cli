import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

import app
import memory
import styling


class Tree(unittest.TestCase):
    """A scratch home folder with a repository inside it."""

    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp(prefix='lyra-home-'))
        self.addCleanup(shutil.rmtree, self.home, True)
        patcher = patch.dict(os.environ, {'HOME': self.home, 'USERPROFILE': self.home})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = os.path.join(self.home, 'work', 'repo')
        self.sub = os.path.join(self.repo, 'src', 'pkg')
        os.makedirs(self.sub)
        os.makedirs(os.path.join(self.repo, '.git'))

    def write(self, folder, text, name='LYRA.md'):
        path = os.path.join(folder, name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return path


class DiscoveryTests(Tree):
    def test_files_are_collected_from_the_working_folder_up_to_the_repository_root(self):
        top, mid = self.write(self.repo, 'aturan repo'), self.write(os.path.join(self.repo, 'src'), 'aturan src')
        self.write(os.path.join(self.home, 'work'), 'di luar repo')          # above the .git folder: ignored
        self.assertEqual(memory.find_instruction_files(self.sub), [mid, top])  # nearest first

    def test_read_order_puts_the_nearest_file_last(self):
        self.write(self.repo, 'umum')
        self.write(self.sub, 'khusus')
        self.assertEqual([i['text'] for i in memory.read_instructions(self.sub)], ['umum', 'khusus'])

    def test_without_a_repository_the_search_stops_at_the_home_folder(self):
        free = os.path.join(self.home, 'catatan', 'baru')
        os.makedirs(free)
        personal = self.write(self.home, 'preferensi pribadi')
        self.assertEqual(memory.find_instruction_files(free), [personal])
        self.write(os.path.dirname(self.home), 'bukan milikmu')            # above home: never read
        self.assertEqual(memory.find_instruction_files(free), [personal])

    def test_outside_home_and_repositories_only_the_working_folder_counts(self):
        outside = os.path.realpath(tempfile.mkdtemp(prefix='lyra-outside-'))
        self.addCleanup(shutil.rmtree, outside, True)
        inner = os.path.join(outside, 'a', 'b')
        os.makedirs(inner)
        self.write(outside, 'tersembunyi di atas')
        self.assertEqual(memory.find_instruction_files(inner), [])
        mine = self.write(inner, 'di sini')
        self.assertEqual(memory.find_instruction_files(inner), [mine])

    @unittest.skipIf(os.name == 'nt', 'symlinks need privileges on Windows')
    def test_a_symlink_that_leaves_the_project_is_ignored(self):
        secret = os.path.join(self.home, 'rahasia.txt')
        with open(secret, 'w') as handle:
            handle.write('kunci pribadi')
        os.symlink(secret, os.path.join(self.repo, 'LYRA.md'))
        self.assertEqual(memory.find_instruction_files(self.repo), [])
        inside = self.write(self.repo, 'asli', name='catatan.md')
        os.remove(os.path.join(self.repo, 'LYRA.md'))
        os.symlink(inside, os.path.join(self.repo, 'LYRA.md'))
        self.assertEqual(len(memory.find_instruction_files(self.repo)), 1)

    def test_binary_empty_and_unreadable_files_are_skipped(self):
        with open(os.path.join(self.repo, 'LYRA.md'), 'wb') as handle:
            handle.write(b'abc\x00def')
        self.assertEqual(memory.read_instructions(self.repo), [])
        self.write(self.repo, '   \n  ')
        self.assertEqual(memory.read_instructions(self.repo), [])

    def test_size_limits_truncate_and_flag_the_file(self):
        self.write(self.repo, 'x' * (memory.MAX_INSTRUCTION_BYTES + 500))
        (item,) = memory.read_instructions(self.repo)
        self.assertEqual((item['size'], item['truncated']), (memory.MAX_INSTRUCTION_BYTES, True))
        self.assertIn('(dipotong)', memory.instructions_section([item]))

    def test_total_budget_and_file_count_are_capped(self):
        for depth in range(6):
            folder = os.path.join(self.repo, *['d'] * depth)
            os.makedirs(folder, exist_ok=True)
            self.write(folder, 'y' * 15000)
        files = memory.read_instructions(os.path.join(self.repo, *['d'] * 5))
        self.assertLessEqual(len(files), memory.MAX_INSTRUCTION_FILES)
        self.assertLessEqual(sum(i['size'] for i in files), memory.MAX_INSTRUCTION_TOTAL)

    def test_the_digest_changes_with_the_content(self):
        self.write(self.repo, 'satu')
        first = memory.read_instructions(self.repo)[0]['digest']
        self.write(self.repo, 'dua')
        self.assertNotEqual(first, memory.read_instructions(self.repo)[0]['digest'])


class PromptTests(Tree):
    def prompt(self, cwd):
        with patch.object(app.os, 'getcwd', return_value=cwd), patch.object(app, 'read_memory', return_value='')\
                , patch.object(app, 'get_system_time', return_value='sekarang'):
            return app.get_current_system_prompt()

    def test_instructions_enter_the_system_prompt_with_a_safety_note(self):
        self.write(self.repo, 'Selalu jalankan pytest sebelum selesai.')
        text = self.prompt(self.repo)
        self.assertIn('[INSTRUKSI PROJECT (LYRA.md)]', text)
        self.assertIn('Selalu jalankan pytest sebelum selesai.', text)
        self.assertIn('tidak menggantikan aturan konfirmasi dan keamanan', text)
        self.assertLess(text.index('[ISI MEMORI'), text.index('[INSTRUKSI PROJECT'))
        self.assertLess(text.index('[INSTRUKSI PROJECT'), text.index('Untuk memanggil tool'))

    def test_no_file_means_no_section_and_no_wasted_tokens(self):
        text = self.prompt(self.repo)
        self.assertNotIn('INSTRUKSI PROJECT', text)
        self.assertIn('Untuk memanggil tool', text)

    def test_braces_in_the_instructions_do_not_break_the_template(self):
        self.write(self.repo, 'Pakai {nama} dan {{ganda}} di template.')
        self.assertIn('Pakai {nama} dan {{ganda}}', self.prompt(self.repo))

    def test_nearest_file_is_listed_last(self):
        self.write(self.repo, 'AAA-umum')
        self.write(self.sub, 'BBB-khusus')
        text = self.prompt(self.sub)
        self.assertLess(text.index('AAA-umum'), text.index('BBB-khusus'))


class CommandTests(Tree):
    def test_instruksi_lists_files_and_hints_when_none(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            app.handle_instructions_command(self.repo)
        self.assertIn('Ketik /init', styling.strip_ansi(out.getvalue()))
        self.write(self.repo, 'x' * 1500)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            app.handle_instructions_command(self.repo)
        plain = styling.strip_ansi(out.getvalue())
        self.assertIn('LYRA.md', plain)
        self.assertIn('1,5 KB', plain)

    def test_the_load_notice_appears_once_per_version_of_a_file(self):
        seen, out = {}, io.StringIO()
        self.write(self.repo, 'satu')
        with contextlib.redirect_stdout(out):
            app.note_instructions(self.repo, seen)
            app.note_instructions(self.repo, seen)
            self.write(self.repo, 'dua')
            app.note_instructions(self.repo, seen)
        plain = styling.strip_ansi(out.getvalue())
        self.assertEqual(plain.count('Instruksi project dimuat'), 1)
        self.assertEqual(plain.count('Instruksi project diperbarui'), 1)

    def test_init_prompt_creates_or_updates_depending_on_the_file(self):
        fresh = app.build_init_prompt(self.repo)
        self.assertIn('Buat file LYRA.md', fresh)
        self.assertIn(self.repo, fresh)
        self.assertIn('write_file', fresh)
        self.assertIn('jangan mengarang', fresh)
        self.write(self.repo, 'sudah ada')
        again = app.build_init_prompt(self.repo)
        self.assertIn('sudah ada', again)
        self.assertIn('edit_file', again)
        self.assertNotIn('Buat file LYRA.md', again)

    def run_main(self, inputs, cwd):
        sent = []

        def post(url, headers=None, json=None, **kwargs):
            sent.append(__import__('copy').deepcopy(json))
            response = Mock(status_code=200)
            event = {'choices': [{'delta': {'content': 'siap\n'}}]}
            response.iter_lines.return_value = [('data: ' + __import__('json').dumps(event)).encode(), b'data: [DONE]']
            return response
        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(patch.object(sys, 'argv', ['amagi']))
            stack.enter_context(patch.object(app.os, 'getcwd', return_value=cwd))
            stack.enter_context(patch.object(app.os, 'chdir'))
            for name, value in (('load_config', {}), ('get_api_key', 'x')):
                stack.enter_context(patch.object(app, name, return_value=value))
            stack.enter_context(patch.object(app, 'ensure_daemon_running'))
            stack.enter_context(patch.object(app, 'read_memory', return_value=''))
            stack.enter_context(patch.object(app, 'check_remote_version', return_value=(False, app.VERSION)))
            editor = stack.enter_context(patch.object(app, 'TerminalInput'))
            stack.enter_context(patch.object(app.requests, 'post', side_effect=post))
            editor.return_value.read.side_effect = list(inputs) + [EOFError()]
            app.main()
        return styling.strip_ansi(out.getvalue()), sent

    def test_init_in_a_session_sends_the_project_prompt_to_the_model(self):
        out, sent = self.run_main(['/init'], self.repo)
        self.assertEqual(len(sent), 1)
        last = sent[0]['messages'][-1]['content']
        self.assertIn('Buat file LYRA.md', last)
        self.assertIn(self.repo, last)
        self.assertIn('write_file', json.dumps(sent[0]['messages'][0]['content']) )   # the tool is documented in the system prompt

    def test_a_loaded_file_reaches_the_request_and_is_announced(self):
        self.write(self.repo, 'Balas selalu dengan satu kalimat.')
        out, sent = self.run_main(['halo'], self.repo)
        self.assertIn('Instruksi project dimuat', out)
        self.assertIn('Balas selalu dengan satu kalimat.', sent[0]['messages'][0]['content'])

    def test_instruksi_and_status_in_a_session(self):
        self.write(self.repo, 'panduan')
        out, sent = self.run_main(['/instruksi', '/status'], self.repo)
        self.assertEqual(sent, [])                                    # neither reaches the model
        self.assertIn('Instruksi project yang dimuat', out)
        self.assertRegex(out, r'Instruksi\s+repo/LYRA\.md')

    def test_commands_are_listed_and_documented(self):
        names = [n for n, _ in styling.COMMANDS]
        self.assertIn('/init', names)
        self.assertIn('/instruksi', names)
        for name in ('/init', '/instruksi'):
            self.assertTrue(styling.COMMAND_DETAILS[name]['examples'])

    def test_print_mode_uses_the_same_instructions(self):
        self.write(self.repo, 'Jawab dalam bahasa formal.')
        captured = {}

        def fake(headers, data):
            captured.update(data)
            return 200, 'ok', ''
        with patch.object(app.os, 'getcwd', return_value=self.repo), patch.object(app, '_collect_stream', side_effect=fake), \
             patch.object(app, 'load_config', return_value={'api_key': 'k'}), patch.object(app, 'read_memory', return_value=''), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_print_mode('halo', stdin_text=''), 0)
        self.assertIn('Jawab dalam bahasa formal.', captured['messages'][0]['content'])


if __name__ == '__main__':
    unittest.main()
