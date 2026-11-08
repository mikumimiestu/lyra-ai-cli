import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

import app
import memory
import styling
import tools


def convo(turns=4, tail='tugas terakhir'):
    """system + `turns` user/assistant pairs + the latest user request."""
    messages = [{'role': 'system', 'content': 'sistem'}]
    for i in range(turns):
        messages += [{'role': 'user', 'content': f'pertanyaan {i}'}, {'role': 'assistant', 'content': f'jawaban {i}'}]
    messages.append({'role': 'user', 'content': tail})
    return messages


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='lyra-sessions-')
        patcher = patch.dict(os.environ, {'LYRA_SESSIONS_DIR': self.folder})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(__import__('shutil').rmtree, self.folder, True)

    def test_round_trip_excludes_the_system_prompt(self):
        self.assertTrue(memory.save_session('abc', convo(1), '/work', started=100.0))
        data = memory.load_session('abc')
        self.assertEqual([m['role'] for m in data['messages']], ['user', 'assistant', 'user'])
        self.assertEqual((data['cwd'], data['started'], data['title']), ('/work', 100.0, 'pertanyaan 0'))

    @unittest.skipIf(os.name == 'nt', 'POSIX permissions')
    def test_files_are_private(self):
        memory.save_session('abc', convo(1), '/work')
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.folder, 'abc.json')).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.folder).st_mode), 0o700)

    def test_nothing_to_save_for_an_empty_conversation_and_history_can_be_disabled(self):
        self.assertFalse(memory.save_session('abc', [{'role': 'system', 'content': 'x'}], '/w'))
        with patch.dict(os.environ, {'LYRA_NO_HISTORY': '1'}):
            self.assertFalse(memory.history_enabled())
            self.assertFalse(memory.save_session('abc', convo(1), '/w'))
        self.assertEqual(os.listdir(self.folder), [])

    def test_list_is_newest_first_and_skips_damaged_files(self):
        for index, name in enumerate(['lama', 'tengah', 'baru']):
            memory.save_session(name, convo(1, tail=name), '/w')
            os.utime(os.path.join(self.folder, name + '.json'), (1000 + index, 1000 + index))
        open(os.path.join(self.folder, 'rusak.json'), 'w').write('{bukan json')
        open(os.path.join(self.folder, 'aneh.json'), 'w').write(json.dumps({'messages': [{'role': 'x', 'content': 1}]}))
        self.assertEqual([s['id'] for s in memory.list_sessions()], ['baru', 'tengah', 'lama'])
        self.assertIsNone(memory.load_session('rusak'))
        self.assertIsNone(memory.load_session('aneh'))
        self.assertIsNone(memory.load_session('tidak-ada'))

    def test_old_sessions_are_pruned(self):
        with patch.object(memory, 'MAX_SESSIONS', 3):
            for i in range(6):
                memory.save_session(f's{i}', convo(1), '/w')
                os.utime(os.path.join(self.folder, f's{i}.json'), (2000 + i, 2000 + i))
        self.assertEqual(sorted(s['id'] for s in memory.list_sessions()), ['s3', 's4', 's5'])

    def test_ids_cannot_escape_the_folder_and_oversized_sessions_are_skipped(self):
        memory.save_session('../../evil', convo(1), '/w')
        self.assertEqual(os.listdir(self.folder), ['evil.json'])
        with patch.object(memory, 'MAX_SESSION_BYTES', 50):
            self.assertFalse(memory.save_session('big', convo(3), '/w'))

    def test_title_ignores_tool_results_attachments_and_summaries(self):
        messages = [{'role': 'user', 'content': '[Ringkasan percakapan sebelumnya]\nx'},
                    {'role': 'user', 'content': '[Hasil Tool \'x\']\n..'},
                    {'role': 'user', 'content': 'jelaskan ini\n[Referensi file: a.py]\nrahasia\n[Akhir referensi file]'}]
        self.assertEqual(memory.session_title(messages), 'jelaskan ini')
        self.assertEqual(memory.session_title([]), '(tanpa judul)')

    def test_delete_all_and_relative_time(self):
        memory.save_session('a', convo(1), '/w')
        memory.save_session('b', convo(1), '/w')
        self.assertEqual(memory.delete_all_sessions(), 2)
        self.assertEqual(memory.list_sessions(), [])
        now = time.time()
        self.assertEqual(memory.relative_time(now), 'baru saja')
        self.assertEqual(memory.relative_time(now - 600), '10 menit lalu')
        self.assertEqual(memory.relative_time(now - 7200), '2 jam lalu')
        self.assertEqual(memory.relative_time(now - 100000), 'kemarin')
        self.assertEqual(memory.relative_time(now - 5 * 86400), '5 hari lalu')


class CompactTests(unittest.TestCase):
    def compact(self, messages, status=200, text='ringkasan padat', focus=''):
        sent = {}
        def fake(headers, data):
            sent.update(data)
            return status, text
        with patch.object(app, 'collect_completion', side_effect=fake):
            return app.compact_messages(messages, {}, 'lyra-orpheus-6', 'medium', focus), sent

    def test_summary_replaces_old_turns_and_keeps_the_latest_request(self):
        (new, error), sent = self.compact(convo(4))
        self.assertIsNone(error)
        self.assertEqual([m['role'] for m in new], ['system', 'user', 'assistant', 'user'])
        self.assertIn('ringkasan padat', new[1]['content'])
        self.assertEqual(new[-1]['content'], 'tugas terakhir')
        self.assertNotIn('pertanyaan 0', json.dumps(new))
        self.assertIn('pertanyaan 0', sent['messages'][1]['content'])      # the old turns went to the summariser
        self.assertNotIn('tugas terakhir', sent['messages'][1]['content'])

    def test_a_running_tool_cycle_stays_verbatim(self):
        messages = convo(3, tail='ubah file')
        messages += [{'role': 'assistant', 'content': '<tool_call>...</tool_call>'},
                     {'role': 'user', 'content': "[Hasil Tool 'read_file']\nisi"}]
        (new, error), _ = self.compact(messages)
        self.assertEqual([m['content'] for m in new[-3:]], ['ubah file', '<tool_call>...</tool_call>', "[Hasil Tool 'read_file']\nisi"])

    def test_short_conversations_and_failures_leave_messages_alone(self):
        (new, error), _ = self.compact(convo(1))
        self.assertIsNone(new)
        self.assertIn('pendek', error)
        for status, text in ((500, 'galat'), (200, '   ')):
            (new, error), _ = self.compact(convo(4), status=status, text=text)
            self.assertIsNone(new)
            self.assertTrue(error)

    def test_focus_and_long_tool_output_are_handled(self):
        messages = convo(3)
        messages[2]['content'] = "[Hasil Tool 'x']\n" + 'z' * 9000
        (new, _), sent = self.compact(messages, focus='fokus ke tes')
        self.assertIn('fokus ke tes', sent['messages'][1]['content'])
        self.assertLess(len(sent['messages'][1]['content']), 6000)
        self.assertIn('dipotong', sent['messages'][1]['content'])

    def test_collect_completion_returns_visible_text_only(self):
        lines = [('data: ' + json.dumps({'choices': [{'delta': {'content': c}}]})).encode()
                 for c in ('<think>rahasia</think>', 'Ringkasan ', 'selesai')] + [b'data: [DONE]']
        response = Mock(status_code=200)
        response.iter_lines.return_value = lines
        with patch.object(app.requests, 'post', return_value=response):
            self.assertEqual(app.collect_completion({}, {}), (200, 'Ringkasan selesai'))
        response.close.assert_called_once()
        with patch.object(app.requests, 'post', return_value=Mock(status_code=429, text='penuh')):
            self.assertEqual(app.collect_completion({}, {}), (429, 'penuh'))

    def test_command_reports_before_and_after_and_keeps_the_list_on_error(self):
        messages = convo(4)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(app, 'Spinner'), \
             patch.object(app, 'collect_completion', return_value=(200, 'ringkas')):
            new = app.handle_compact_command(messages, {}, 'lyra-orpheus-6', 'medium')
        self.assertLess(len(new), len(messages))
        self.assertIn('Percakapan diringkas', styling.strip_ansi(out.getvalue()))
        with contextlib.redirect_stdout(io.StringIO()), patch.object(app, 'Spinner'), \
             patch.object(app, 'collect_completion', return_value=(500, 'x')):
            self.assertIs(app.handle_compact_command(messages, {}, 'lyra-orpheus-6', 'medium'), messages)


class SessionFlowTests(unittest.TestCase):
    """Whole-program flows with the API mocked: saving, --continue, /resume, /compact, /undo."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='lyra-flow-')
        patcher = patch.dict(os.environ, {'LYRA_SESSIONS_DIR': self.folder})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(__import__('shutil').rmtree, self.folder, True)
        self.addCleanup(tools.APPROVAL.set, 'ask')
        self.addCleanup(tools.UNDO.clear)
        self.posts = []

    def run_main(self, inputs, argv=('amagi',), extra=()):
        def post(url, headers=None, json=None, **kwargs):
            self.posts.append(__import__('copy').deepcopy(json))     # the program keeps mutating its list
            response = Mock(status_code=200)
            event = {'choices': [{'delta': {'content': 'jawaban baru\n'}}]}
            response.iter_lines.return_value = [('data: ' + __import__('json').dumps(event)).encode(), b'data: [DONE]']
            return response
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(output))
            stack.enter_context(patch.object(sys, 'argv', list(argv)))
            for target, value in (('load_config', {}), ('get_api_key', 'x'), ('get_current_system_prompt', 'sistem')):
                stack.enter_context(patch.object(app, target, return_value=value))
            stack.enter_context(patch.object(app, 'ensure_daemon_running'))
            stack.enter_context(patch.object(app, 'check_remote_version', return_value=(False, app.VERSION)))
            editor = stack.enter_context(patch.object(app, 'TerminalInput'))
            stack.enter_context(patch.object(app.requests, 'post', side_effect=post))
            for patcher in extra:
                stack.enter_context(patcher)
            editor.return_value.read.side_effect = list(inputs) + [EOFError()]
            app.main()
        return styling.strip_ansi(output.getvalue())

    def test_each_finished_turn_is_saved(self):
        self.run_main(['halo dunia'])
        saved = memory.list_sessions()
        self.assertEqual(len(saved), 1)
        self.assertEqual((saved[0]['title'], saved[0]['count']), ('halo dunia', 2))

    def test_continue_flag_resumes_the_latest_session(self):
        self.run_main(['pertanyaan lama'])
        self.posts.clear()
        out = self.run_main(['lanjut'], argv=('amagi', '--continue'))
        self.assertIn('Melanjutkan', out)
        sent = [m['content'] for m in self.posts[-1]['messages']]
        self.assertIn('pertanyaan lama', sent)
        self.assertEqual(sent[-1], 'lanjut')
        self.assertEqual(len(memory.list_sessions()), 1)             # appended to the same session

    def test_resume_command_loads_the_picked_session(self):
        self.run_main(['topik pertama'])
        self.run_main(['topik kedua'])
        self.posts.clear()
        titles = []
        def pick(title, options, selected=0, subtitle=''):
            titles.extend(label for label, _ in options)
            return titles.index('topik pertama')
        out = self.run_main(['/resume', 'lanjut'], extra=[patch.object(app, 'pick_option', side_effect=pick)])
        self.assertEqual(sorted(titles), ['topik kedua', 'topik pertama'])
        self.assertIn('Dilanjutkan: topik pertama', out)
        sent = [m['content'] for m in self.posts[-1]['messages']]
        self.assertIn('topik pertama', sent)
        self.assertNotIn('topik kedua', sent)

    def test_resume_handles_nothing_saved_cancel_and_delete(self):
        self.assertIn('Belum ada percakapan tersimpan', self.run_main(['/resume']))
        self.run_main(['halo'])
        out = self.run_main(['/resume'], extra=[patch.object(app, 'pick_option', return_value=None)])
        self.assertIn('Dibatalkan', out)
        out = self.run_main(['/resume hapus'], extra=[patch('builtins.input', return_value='y')])
        self.assertIn('1 sesi dihapus', out)
        self.assertEqual(memory.list_sessions(), [])

    def test_clear_starts_a_new_saved_session(self):
        self.run_main(['pertama', '/clear', 'kedua'])
        self.assertEqual(sorted(s['title'] for s in memory.list_sessions()), ['kedua', 'pertama'])

    def test_compact_command_shrinks_what_the_next_request_carries(self):
        inputs = [f'pesan {i}' for i in range(4)] + ['/compact', 'lanjut']
        out = self.run_main(inputs, extra=[patch.object(app, 'collect_completion', return_value=(200, 'ringkasan sesi')),
                                           patch.object(app, 'Spinner')])
        self.assertIn('Percakapan diringkas', out)
        sent = [m['content'] for m in self.posts[-1]['messages']]
        self.assertTrue(any(c.startswith('[Ringkasan') and 'ringkasan sesi' in c for c in sent))
        self.assertNotIn('pesan 0', sent)
        self.assertEqual(sent[-1], 'lanjut')

    def test_undo_command_restores_a_file(self):
        target = os.path.join(self.folder, 'u.txt')
        with open(target, 'w') as handle:
            handle.write('asli')
        tools.APPROVAL.set('edits')
        with contextlib.redirect_stdout(io.StringIO()):
            tools.edit_file(target, 'asli', 'diubah')
        out = self.run_main(['/undo list', '/undo'])
        self.assertIn('u.txt', out)
        self.assertIn('Dikembalikan', out)
        with open(target) as handle:
            self.assertEqual(handle.read(), 'asli')

    def test_status_reports_undo_and_history(self):
        out = self.run_main(['/status'])
        self.assertIn('Urungkan', out)
        self.assertIn('Riwayat', out)
        self.assertIn('tersimpan di ~/.amagi_sessions', out)


if __name__ == '__main__':
    unittest.main()
