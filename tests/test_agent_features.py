import contextlib
import io
import os
import threading
import time
import unittest
from unittest.mock import patch

import app
import styling
import tools
from spinner import EscapeWatcher


class StreamRendererTests(unittest.TestCase):
    def render(self, text, step=1):
        writes = []
        renderer = styling.StreamRenderer(writes.append)
        for i in range(0, len(text), step):
            renderer.feed(text[i:i + step])
        renderer.finish()
        return writes, styling.strip_ansi(''.join(writes))

    def test_paragraph_text_is_written_token_by_token(self):
        writes = []
        renderer = styling.StreamRenderer(writes.append)
        renderer.feed('Halo')
        self.assertIn('Halo', styling.strip_ansi(''.join(writes)))
        renderer.feed(' dunia')
        self.assertIn('Halo dunia', styling.strip_ansi(''.join(writes)))
        self.assertFalse(''.join(writes).endswith('\n'))

    def test_output_does_not_depend_on_chunk_size(self):
        text = ('Halo **tebal** dan `kode` serta *miring*.\n- item satu\n1. item dua\n# Judul\n'
                '```py\nprint(1)\n```\n| a | b |\n|---|---|\n| 1 | 2 |\nAkhir')
        _, whole = self.render(text, step=len(text))
        for step in (1, 2, 3, 7):
            self.assertEqual(self.render(text, step)[1], whole, step)
        self.assertTrue(whole.startswith('● Halo tebal dan  kode  serta miring.'))
        self.assertIn('• item satu', whole)
        self.assertIn('print(1)', whole)
        self.assertIn('┌───┬───┐', whole)
        self.assertTrue(whole.rstrip().endswith('Akhir'))

    def test_styles_are_closed_at_end_of_line(self):
        writes, _ = self.render('a **b\nc\n')
        text = ''.join(writes)
        self.assertLess(text.index('\n'), len(text))
        self.assertTrue(text.split('\n')[0].endswith(styling.RESET))

    def test_literal_asterisk_and_underscores_are_kept(self):
        _, plain = self.render('2 * 3 dan snake_case_name\n')
        self.assertIn('2 * 3 dan snake_case_name', plain)

    def test_blank_lines_before_answer_are_dropped(self):
        _, plain = self.render('\n\n  \nHalo\n')
        self.assertTrue(plain.startswith('● Halo'))

    def test_code_block_blank_lines_are_kept(self):
        _, plain = self.render('```\na\n\nb\n```\n')
        self.assertEqual(plain.count('│'), 3)


class EscapeWatcherTests(unittest.TestCase):
    def watch(self, payload):
        read, write = os.pipe()
        hits = []
        try:
            with EscapeWatcher(on_escape=lambda: hits.append(1), fd=read, force=True):
                os.write(write, payload)
                time.sleep(0.4)
        finally:
            os.close(read)
            os.close(write)
        return hits

    @unittest.skipIf(os.name == 'nt', 'POSIX file descriptors only')
    def test_lone_escape_fires_once(self):
        self.assertEqual(self.watch(b'\x1b'), [1])

    @unittest.skipIf(os.name == 'nt', 'POSIX file descriptors only')
    def test_arrow_keys_and_text_do_not_fire(self):
        self.assertEqual(self.watch(b'\x1b[A'), [])
        self.assertEqual(self.watch(b'abc'), [])

    def test_disabled_without_a_terminal(self):
        with patch.object(EscapeWatcher, '_enabled', return_value=False):
            watcher = EscapeWatcher()
            with watcher:
                self.assertIsNone(watcher._thread)

    def test_stream_interrupt_returns_to_caller_and_stops_spinner(self):
        from unittest.mock import Mock
        progress = Mock()
        with contextlib.redirect_stdout(io.StringIO()), patch.object(app.requests, 'post', side_effect=KeyboardInterrupt()), \
             patch.object(app, 'Spinner', return_value=progress), self.assertRaises(KeyboardInterrupt):
            app.stream_ai_response({}, {})
        progress.stop.assert_called()


class TodoTests(unittest.TestCase):
    def test_update_validates_and_summarises(self):
        todos = tools.TodoList()
        result = todos.update([{'content': 'Baca kode', 'status': 'completed'},
                               {'content': 'Ubah UI', 'status': 'in_progress'}, 'Tes'])
        self.assertIn('1/3 selesai', result)
        self.assertIn('Ubah UI', result)
        self.assertEqual([item['status'] for item in todos.items], ['completed', 'in_progress', 'pending'])

    def test_invalid_input_is_rejected_without_changing_state(self):
        todos = tools.TodoList()
        todos.update(['a'])
        for bad in (None, [], [{'content': ''}], [{'content': 'x', 'status': 'selesai'}], [1], ['x'] * 21):
            self.assertTrue(todos.update(bad).startswith('Error'), bad)
        self.assertEqual(len(todos.items), 1)

    def test_checklist_rendering_and_activity(self):
        items = styling.normalize_todos([{'content': 'A', 'status': 'completed'},
                                         {'content': 'B', 'status': 'in_progress'}, {'content': 'C'}])
        lines = [styling.strip_ansi(line) for line in styling.render_todo_lines(items)]
        self.assertEqual(len(lines), 3)
        self.assertIn('B', lines[1])
        output = io.StringIO()
        log = styling.ActivityLog()
        args = {'todos': [{'content': 'A'}, {'content': 'B', 'status': 'in_progress'}]}
        with contextlib.redirect_stdout(output):
            log.start('update_todos', args)
            log.finish('update_todos', args, 'Daftar tugas diperbarui: 0/2 selesai.')
        plain = styling.strip_ansi(output.getvalue())
        self.assertIn('● Daftar tugas', plain)
        self.assertIn('Daftar tugas diperbarui', plain)

    def test_main_dispatches_todos_and_todos_command(self):
        import json
        from unittest.mock import Mock
        call = '<tool_call>' + json.dumps({'name': 'update_todos', 'arguments': {'todos': [{'content': 'Satu', 'status': 'in_progress'}]}}) + '</tool_call>'
        def reply(text):
            response = Mock(status_code=200)
            response.iter_lines.return_value = [('data: ' + json.dumps({'choices': [{'delta': {'content': text}}]})).encode(), b'data: [DONE]']
            return response
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(app, 'load_config', return_value={}), \
             patch.object(app, 'get_api_key', return_value='test-only'), patch.object(app, 'ensure_daemon_running'), \
             patch.object(app, 'get_current_system_prompt', return_value='x'), \
             patch.object(app, 'check_remote_version', return_value=(False, app.VERSION)), \
             patch.object(app, 'TerminalInput') as editor, patch.object(app.requests, 'post', side_effect=[reply(call), reply('Selesai.')]):
            editor.return_value.read.side_effect = ['kerjakan', '/todos', EOFError()]
            app.main()
        plain = styling.strip_ansi(output.getvalue())
        self.assertIn('Daftar tugas diperbarui: 0/1 selesai', plain)
        self.assertIn('Satu', plain.split('Daftar tugas diperbarui')[-1])
        self.assertIn('Selesai.', plain)


class StatusAndContextTests(unittest.TestCase):
    def test_context_estimate_and_override(self):
        messages = [{'role': 'user', 'content': 'x' * 4000}]
        self.assertEqual(app.estimate_context_tokens(messages), 1000)
        with patch.dict(os.environ, {'LYRA_CONTEXT_TOKENS': '10000'}):
            self.assertEqual(app.context_percent(messages), 10)
        with patch.dict(os.environ, {'LYRA_CONTEXT_TOKENS': 'abc'}):
            self.assertEqual(app.context_limit(), app.DEFAULT_CONTEXT_TOKENS)

    def test_footer_shows_context_only_when_known(self):
        self.assertIn('ctx ~12%', styling.toolbar_text('Lyra Orpheus 6', 'medium', '/work', context_pct=12))
        self.assertNotIn('ctx', styling.toolbar_text('Lyra Orpheus 6', 'medium', '/work'))

    def test_status_card_never_prints_the_key(self):
        output = io.StringIO()
        config = {'api_key': 'sk-secret-123', 'reasoning_effort': 'medium'}
        with contextlib.redirect_stdout(output), patch.dict(os.environ, {'ASTBYTE_API_KEY': ''}), \
             patch.object(app, 'is_daemon_running', return_value=False), \
             patch.object(app, 'read_memory', return_value='abc'):
            app.handle_status_command(config, 2, '/work', [{'role': 'system', 'content': 'x'}], tools.TodoList())
        plain = styling.strip_ansi(output.getvalue())
        self.assertNotIn('sk-secret-123', plain)
        for expected in ('Lyra Orpheus 6', 'tersimpan di config', 'authx.astbyte.com', 'daemon mati', 'v' + app.VERSION):
            self.assertIn(expected, plain)

    def test_new_commands_are_listed(self):
        names = [name for name, _ in styling.COMMANDS]
        self.assertIn('/status', names)
        self.assertIn('/todos', names)


class ModelListTests(unittest.TestCase):
    def test_current_models_and_default(self):
        self.assertEqual([(m['name'], m['id']) for m in app.MODELS], [
            ('Lyra Luma 6.1', 'lyra-luma-6-1'), ('Lyra Luma 4 mini', 'lyra-luma-4-mini'),
            ('Lyra Orpheus 6', 'lyra-orpheus-6'), ('Lyra Eurydice 6', 'lyra-eurydice-6'),
            ('Lyra Luma Flash', 'lyra-luma-flash')])
        self.assertEqual(app.MODELS[app.DEFAULT_MODEL_INDEX]['id'], 'lyra-orpheus-6')
        self.assertEqual([m['supports_reasoning'] for m in app.MODELS], [True, False, True, True, False])

    def test_legacy_ids_are_redirected(self):
        for old, new in [('lyra-luma-5.5', 'lyra-luma-6-1'), ('mimo-v2.5', 'lyra-luma-6-1'),
                         ('lyra-luma-6.1', 'lyra-luma-6-1'), ('lyra-luma-flash', 'lyra-luma-flash'),
                         ('lyra-nebula-4', 'lyra-luma-4-mini'), ('lyra-orpheus-6', 'lyra-orpheus-6')]:
            self.assertEqual(app.canonical_model_id(old), new)
        self.assertEqual(app.canonical_model_id('model-baru'), 'model-baru')

    def test_saved_config_with_old_id_is_migrated_not_crashing(self):
        config = {'model': 'lyra-nebula-4', 'model_index': 2, 'reasoning_effort': 'low'}
        self.assertTrue(app.migrate_model_config(config))
        self.assertEqual(config['model'], 'lyra-luma-4-mini')
        self.assertEqual(config['model_index'], 1)
        config = {'model_id': 'mimo-v2.5'}
        self.assertTrue(app.migrate_model_config(config))
        self.assertEqual((config['model_id'], config['model_index']), ('lyra-luma-6-1', 0))
        self.assertFalse(app.migrate_model_config({'model_index': 2}))

    def test_request_never_carries_an_old_id(self):
        import json
        from unittest.mock import Mock
        sent = []
        def post(url, headers=None, json=None, **kwargs):
            sent.append(json['model'])
            response = Mock(status_code=200)
            response.iter_lines.return_value = [b'data: {"choices":[{"delta":{"content":"ok\\n"}}]}', b'data: [DONE]']
            return response
        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(app, 'load_config', return_value={'model': 'lyra-nebula-4'}), patch.object(app, 'save_config'), \
             patch.object(app, 'get_api_key', return_value='test-only'), patch.object(app, 'ensure_daemon_running'), \
             patch.object(app, 'get_current_system_prompt', return_value='x'), \
             patch.object(app, 'check_remote_version', return_value=(False, app.VERSION)), \
             patch.object(app, 'TerminalInput') as editor, patch.object(app.requests, 'post', side_effect=post):
            editor.return_value.read.side_effect = ['halo', EOFError()]
            app.main()
        self.assertEqual(sent, ['lyra-luma-4-mini'])


if __name__ == '__main__':
    unittest.main()
