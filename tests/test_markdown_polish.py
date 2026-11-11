import os
import re
import sys
import tempfile
import unittest

os.environ.setdefault('LYRA_SESSIONS_DIR', tempfile.mkdtemp(prefix='lyra-test-sessions-'))

import styling


def stream(text, width=70, step=1, wrap=True):
    chunks = []
    renderer = styling.StreamRenderer(chunks.append, wrap=wrap, width=lambda: width)
    for i in range(0, len(text), step):
        renderer.feed(text[i:i + step])
    renderer.finish()
    return ''.join(chunks)


def plain(text, **kwargs):
    return styling.strip_ansi(stream(text, **kwargs))


def block(line):
    formatted, _ = styling.format_markdown_line(line, {'in_code': False, 'lang': ''})
    return styling.strip_ansi(formatted).strip()


class LinkTests(unittest.TestCase):
    def test_link_shows_the_text_then_the_url(self):
        self.assertEqual(plain('Lihat [dokumentasi](https://docs.example.com/a_b_c) sekarang.\n').strip(),
                         '● Lihat dokumentasi (https://docs.example.com/a_b_c) sekarang.')

    def test_urls_are_never_mangled_by_emphasis_rules(self):
        out = plain('[x](https://e.com/a_b_c/*d*/~~e~~)\n')
        self.assertIn('(https://e.com/a_b_c/*d*/~~e~~)', out)

    def test_a_url_used_as_its_own_text_is_not_repeated(self):
        self.assertEqual(plain('[https://x.io](https://x.io)\n').strip(), '● https://x.io')

    def test_images_show_their_alt_text(self):
        self.assertIn('[gambar: logo] (https://x.io/l.png)', plain('![logo](https://x.io/l.png)\n'))
        self.assertIn('[gambar] (https://x.io/l.png)', plain('![](https://x.io/l.png)\n'))

    def test_titles_and_angle_brackets_are_ignored(self):
        self.assertIn('(https://a.b)', plain('[t](https://a.b "judul")\n'))
        self.assertIn('(https://a.b/c)', plain('[t](<https://a.b/c>)\n'))

    def test_brackets_that_are_not_links_stay_as_typed(self):
        for text in ('[bukan link] saja', 'array[0] dan [1]', 'akhir [belum selesai', 'kurung [juga](bukan.', 'seru ! dan ~ tunggal', 'a [b] (c)'):
            out = plain(text + '\n').strip()
            self.assertEqual(out, '● ' + text, text)

    def test_links_inside_code_spans_are_left_alone(self):
        self.assertIn('[a](http://b)', plain('`[a](http://b)`\n').replace('  ', ' '))

    def test_links_survive_wrapping_and_any_chunking(self):
        text = 'Baca [panduan lengkap instalasi](https://example.com/panduan/instalasi/lengkap) di sini ya.\n'
        whole = stream(text, width=36, step=len(text))
        for step in (1, 2, 5, 11):
            self.assertEqual(stream(text, width=36, step=step), whole, step)
        lines = styling.strip_ansi(whole).splitlines()
        self.assertTrue(all(styling.str_width(l) <= 35 for l in lines), lines)
        self.assertIn('https://example.com/panduan/instalasi/lengkap', ''.join(l.strip() for l in lines))

    def test_link_text_is_underlined_when_colour_is_on(self):
        if styling.USE_COLOR:
            self.assertIn(styling.UNDERLINE, stream('[a](http://b)\n'))

    def test_block_formatter_and_table_cells_render_links_too(self):
        self.assertEqual(block('Lihat [dokumentasi](https://docs.example.com/a_b_c) ya'), 'Lihat dokumentasi (https://docs.example.com/a_b_c) ya')
        table = '\n'.join(styling.strip_ansi(l) for l in styling.render_markdown_table(['| Nama | Tautan |', '|---|---|', '| a | [web](https://x.io/a_b) |']))
        self.assertIn('web (https://x.io/a_b)', table)


class StrikeAndTaskTests(unittest.TestCase):
    def test_strikethrough_is_styled_and_markers_disappear(self):
        out = stream('Teks ~~salah~~ benar\n')
        self.assertNotIn('~~', styling.strip_ansi(out))
        self.assertEqual(plain('Teks ~~salah~~ benar\n').strip(), '● Teks salah benar')
        if styling.USE_COLOR:
            self.assertIn(styling.STRIKE, out)
        self.assertNotIn('~~', block('x ~~y~~ z'))

    def test_single_tildes_and_bangs_are_literal(self):
        self.assertEqual(plain('harga 5~7 hari, wow! seru\n').strip(), '● harga 5~7 hari, wow! seru')

    def test_task_items_become_checkboxes_without_a_bullet(self):
        out = plain('- [ ] belum\n- [x] selesai\n- [X] juga selesai\n1. [ ] bernomor\n')
        lines = [l.strip() for l in out.splitlines()]
        self.assertIn('☐ belum', out)
        self.assertIn('☒ selesai', out)
        self.assertNotIn('• ☐', out)
        self.assertNotIn('[ ]', out)
        self.assertEqual(block('- [ ] tugas'), '☐ tugas')
        self.assertEqual(block('- [x] tugas'), '☒ tugas')

    def test_look_alikes_stay_ordinary_list_items(self):
        out = plain('- [catatan] penting\n- x adalah huruf\n- [x]tanpa spasi\n')
        self.assertIn('• [catatan] penting', out)
        self.assertIn('• x adalah huruf', out)
        self.assertNotIn('☒', out)

    def test_task_text_wraps_under_the_text_not_the_box(self):
        out = plain('- [ ] ' + 'kata ' * 30 + '\n', width=40).splitlines()
        self.assertTrue(out[0].lstrip().startswith('☐') or out[0].lstrip('● ').startswith('☐'))
        self.assertTrue(all(l.startswith('    ') for l in out[1:]), out)

    def test_ascii_terminals_get_text_boxes(self):
        from unittest.mock import patch
        with patch.object(styling, 'unicode_terminal', return_value=False):
            out = plain('- [ ] a\n- [x] b\n')
        self.assertIn('[ ] a', out)
        self.assertIn('[x] b', out)

    def test_chunking_never_changes_the_output(self):
        text = 'Teks ~~a~~ [l](http://u) ![i](http://v)\n- [ ] t\n- [x] u\n> > dalam\n1. n\n'
        whole = stream(text, width=50, step=len(text))
        for step in (1, 2, 3, 7, 13):
            self.assertEqual(stream(text, width=50, step=step), whole, step)


class QuoteTests(unittest.TestCase):
    def test_nested_quotes_show_one_bar_per_level(self):
        out = plain('> satu\n> > dua\n> > > tiga\n')
        self.assertIn('▎ satu', out)
        self.assertIn('▎ ▎ dua', out)
        self.assertIn('▎ ▎ ▎ tiga', out)
        self.assertNotIn('>', out)
        self.assertEqual(block('> > dalam'), '▎ ▎ dalam')

    def test_quote_wrap_indent_covers_every_bar(self):
        lines = plain('> > ' + 'kata ' * 20 + '\n', width=30).splitlines()
        self.assertTrue(all(l.startswith('    ') for l in lines[1:]), lines)

    def test_comparison_operators_are_not_quotes(self):
        self.assertEqual(plain('->panah dan a > b\n').strip(), '● ->panah dan a > b')


class NumberedListTests(unittest.TestCase):
    def test_nested_numbered_items_indent_further(self):
        lines = plain('1. satu\n   1. dalam\n      1. lebih dalam\n2. dua\n').splitlines()
        indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
        self.assertEqual(indents[1:], [4, 8, 2])
        self.assertIn('1. lebih dalam', lines[2])
        self.assertEqual(' '.join(plain('        - sangat dalam\n').split()), '● • sangat dalam')   # a deep bullet is still a bullet


if __name__ == '__main__':
    unittest.main()
