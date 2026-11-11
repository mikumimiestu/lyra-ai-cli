import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

import styling

LONG = ("Cache terbesar yang relatif aman dibersihkan adalah **Google, Codex, pip, TypeScript, dan node-gyp**—totalnya "
        "sekitar **1,4 GB**. Cache ini akan dibuat ulang otomatis saat aplikasinya digunakan lagi.\n"
        "- Total cache: 1,6 GB dan ini adalah butir daftar yang cukup panjang supaya terbungkus dengan benar\n"
        "1. Butir bernomor yang juga panjang dan harus dibungkus tanpa memotong kata di tengahnya\n"
        "> Kutipan panjang yang juga harus dibungkus rapi tanpa memotong kata di tengah-tengahnya ya\n")


def render(text, width=60, step=1, wrap=True):
    chunks = []
    renderer = styling.StreamRenderer(chunks.append, wrap=wrap, width=lambda: width)
    for i in range(0, len(text), step):
        renderer.feed(text[i:i + step])
    renderer.finish()
    return ''.join(chunks)


def words(text):
    return re.sub(r'[●•▎]|\d\.', ' ', styling.strip_ansi(text)).split()


class WrapTests(unittest.TestCase):
    def test_no_line_is_wider_than_the_terminal_and_no_word_is_cut(self):
        for width in (30, 45, 60, 100):
            plain = styling.strip_ansi(render(LONG, width))
            self.assertTrue(all(styling.str_width(line) <= width - 1 for line in plain.splitlines()), width)
            original = [w for w in re.sub(r'[*]', '', LONG).replace('- ', '').replace('> ', '').split() if w not in ('1.',)]
            self.assertEqual([w for w in words(plain) if w], [w for w in original if w], width)

    def test_continuation_lines_keep_the_text_indent(self):
        lines = styling.strip_ansi(render(LONG, 50)).splitlines()
        self.assertTrue(lines[0].startswith('● Cache terbesar'))
        paragraph = lines[1:lines.index(next(l for l in lines if '•' in l))]
        self.assertTrue(paragraph and all(l.startswith('  ') and not l.startswith('   ') for l in paragraph), paragraph)
        bullet = next(i for i, l in enumerate(lines) if '•' in l)
        self.assertTrue(lines[bullet + 1].startswith('    ') and not lines[bullet + 1].startswith('     '))
        quote = next(i for i, l in enumerate(lines) if '▎' in l)
        self.assertTrue(lines[quote + 1].startswith('    '))

    def test_output_does_not_depend_on_chunk_size(self):
        whole = render(LONG, 40, step=len(LONG))
        for step in (1, 2, 3, 7, 13):
            self.assertEqual(render(LONG, 40, step=step), whole, step)

    def test_no_trailing_spaces_before_a_wrap_and_none_at_the_start_of_a_line(self):
        for line in styling.strip_ansi(render('kata ' * 60 + '\n', 30)).splitlines():
            self.assertEqual(line, line.rstrip())
            self.assertFalse(line[2:3] == ' ')

    def test_bold_and_code_styles_survive_a_wrap(self):
        out = render('x ' * 10 + '**tebal yang sangat panjang sekali supaya terbungkus** selesai\n', 30)
        lines = out.split('\n')
        wrapped = next(l for l in lines if 'terbungkus' in l and styling.strip_ansi(l).strip().startswith(('yang', 'sangat', 'sekali', 'supaya')))
        if styling.USE_COLOR:
            self.assertIn(styling.BOLD, wrapped)            # the continuation line re-applies bold itself
        self.assertTrue(lines[-2].endswith(styling.RESET) or not styling.USE_COLOR)

    def test_a_word_longer_than_the_line_is_broken_instead_of_overflowing(self):
        plain = styling.strip_ansi(render('a ' + 'x' * 100 + ' b\n', 30))
        self.assertTrue(all(styling.str_width(l) <= 29 for l in plain.splitlines()))
        self.assertEqual(plain.replace('\n', '').replace(' ', '').count('x'), 100)

    def test_wide_characters_count_two_columns(self):
        plain = styling.strip_ansi(render('日本語の文章 ' * 12 + '\n', 30))
        self.assertTrue(all(styling.str_width(l) <= 29 for l in plain.splitlines()), plain)

    def test_resizing_mid_answer_applies_to_the_next_words(self):
        size = [60]
        chunks = []
        renderer = styling.StreamRenderer(chunks.append, wrap=True, width=lambda: size[0])
        renderer.feed('kata ' * 8)
        size[0] = 24
        renderer.feed('kata ' * 12 + '\n')
        renderer.finish()
        self.assertTrue(all(styling.str_width(l) <= 23 for l in styling.strip_ansi(''.join(chunks)).splitlines()[1:]))

    def test_wrapping_is_off_by_default_and_for_pipes(self):
        plain = styling.strip_ansi(render('kata ' * 40 + '\n', 30, wrap=False))
        self.assertEqual(len(plain.splitlines()), 1)

    def test_block_elements_are_not_reflowed(self):
        out = styling.strip_ansi(render('```python\n' + 'x = ' + '1' * 80 + '\n```\n# Judul\n', 30))
        self.assertIn('x = ' + '1' * 80, out)

    def test_interrupt_shows_the_word_in_progress(self):
        chunks = []
        renderer = styling.StreamRenderer(chunks.append, wrap=True, width=lambda: 60)
        renderer.feed('halo dunia yang terpotong di teng')
        renderer.abort()
        self.assertIn('terpotong di teng', styling.strip_ansi(''.join(chunks)))


class CompactDialogTests(unittest.TestCase):
    def dialog(self, title, details, width=100):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(styling, 'get_terminal_width', return_value=width):
            styling.render_permission_box(title, details)
        return styling.strip_ansi(out.getvalue())

    def test_command_is_complete_beside_a_bar_with_one_info_line(self):
        command = "du -sh \"$HOME/Library/Caches\"; " + "find . -name '*.log'; " * 8 + "df -h /"
        page = self.dialog('Konfirmasi Eksekusi Perintah', {'Perintah': command, 'Direktori': '/Users/x/proj', 'Timeout': '120 detik'}, width=60)
        self.assertNotIn('╭', page)
        self.assertNotIn('Timeout', page)
        self.assertIn('Eksekusi Perintah', page)
        self.assertIn('batas 120 dtk', page)
        lines = [l for l in page.splitlines() if l.strip()]
        self.assertTrue(lines[0].lstrip().startswith('⚠'))
        body = [l for l in lines if '│' in l]
        self.assertEqual(re.sub(r'\s+', '', ''.join(l.split('│', 1)[1] for l in body)), re.sub(r'\s+', '', command))
        self.assertTrue(all(styling.str_width(l) <= 60 for l in lines))
        self.assertEqual(len(lines), len(body) + 2)                       # heading + info line only

    def test_file_operations_fit_on_two_lines(self):
        page = self.dialog('Konfirmasi Ubah File', {'Operasi': 'Mengubah File', 'Path': os.path.expanduser('~/proj/app.py'), 'Penggantian': '2'})
        lines = [l for l in page.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertIn('Mengubah File · ~/proj/app.py · 2 penggantian', lines[1])

    def test_warnings_stand_out_and_multi_line_commands_keep_their_lines(self):
        page = self.dialog('Konfirmasi Urungkan', {'Operasi': 'Mengembalikan versi sebelumnya', 'Path': '/x/a.txt', 'Peringatan': 'File diubah setelah perubahan Lyra'})
        self.assertIn('⚠ File diubah setelah perubahan Lyra', page)
        page = self.dialog('Konfirmasi Eksekusi Perintah', {'Perintah': 'cd app\necho satu\necho dua'})
        self.assertEqual(page.count('│'), 3)

    def test_other_detail_keys_are_still_shown(self):
        self.assertIn('aneh nilai', self.dialog('X', {'Aneh': 'nilai'}))
        page = self.dialog('Inisialisasi Project Baru', {'Tipe Project': 'react', 'Nama': 'demo', 'Target Path': '/x/demo'})
        self.assertIn('react · demo · /x/demo', page)


if __name__ == '__main__':
    unittest.main()


class HeadingTests(unittest.TestCase):
    def line(self, text):
        formatted, _ = styling.format_markdown_line(text, {'in_code': False, 'lang': ''})
        return styling.strip_ansi(formatted).strip()

    def test_all_six_heading_levels_lose_their_hashes(self):
        for level in range(1, 7):
            self.assertEqual(self.line('#' * level + ' Manfaat Teoretis'), 'Manfaat Teoretis', level)

    def test_closing_hashes_emphasis_and_extra_spaces_are_cleaned(self):
        self.assertEqual(self.line('## Judul ##'), 'Judul')
        self.assertEqual(self.line('#### **Manfaat** Praktis'), 'Manfaat Praktis')
        self.assertEqual(self.line('###   Banyak spasi   '), 'Banyak spasi')

    def test_things_that_are_not_headings_stay_as_typed(self):
        for text in ('#hashtag', '####### terlalu dalam', 'C# adalah bahasa', '#'):
            self.assertIn(text.split()[0], self.line(text), text)
        self.assertTrue(self.line('#hashtag').startswith('#hashtag'))
        self.assertTrue(self.line('####### terlalu dalam').startswith('#######'))

    def test_levels_look_different_and_code_comments_are_untouched(self):
        if styling.USE_COLOR:
            styles = {styling.format_markdown_line('#' * n + ' x', {'in_code': False, 'lang': ''})[0] for n in range(1, 6)}
            self.assertEqual(len(styles), 5)
        state = {'in_code': True, 'lang': 'python'}
        formatted, _ = styling.format_markdown_line('#### komentar di dalam blok kode', state)
        self.assertIn('#### komentar', styling.strip_ansi(formatted))

    def test_streamed_answers_render_deep_headings_in_any_chunking(self):
        text = 'Pembuka.\n#### Manfaat Teoretis\nMenambah referensi.\n##### Detail\nIsi.\n'
        whole = styling.strip_ansi(render(text, 80, step=len(text), wrap=False))
        self.assertNotIn('####', whole)
        self.assertNotIn('#####', whole)
        self.assertIn('Manfaat Teoretis', whole)
        for step in (1, 3, 5):
            self.assertEqual(styling.strip_ansi(render(text, 80, step=step, wrap=False)), whole, step)
        self.assertEqual(len([l for l in whole.splitlines() if 'Manfaat' in l]), 1)
