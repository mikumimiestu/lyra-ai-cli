"""Reading .docx/.xlsx/.pptx/.pdf as text, refusing to corrupt them, and syntax checks after edits."""
import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import styling
import tools

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def make_zip(path, files):
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


class ReaderTests(unittest.TestCase):
    def text(self, name):
        return styling.extract_document_text(str(FIXTURES / name))

    def test_word_headings_lists_tables_and_header_footer(self):
        text, summary = self.text('contoh.docx')
        self.assertIn('Dokumen Word', summary)
        self.assertIn('# BAB I Pendahuluan', text)
        self.assertIn('## 1.1 Rumusan Masalah', text)
        self.assertIn('- Poin pertama', text)
        self.assertIn('Teks tebal dan biasa.', text)
        self.assertIn('| Nama | Umur | Kota |', text)
        self.assertIn('| Budi | 21 | Bandung |', text)
        self.assertLess(text.index('Header: Header Dokumen'), text.index('Footer: Halaman footer'))

    def test_excel_cells_have_addresses_formulas_and_booleans(self):
        text, summary = self.text('contoh.xlsx')
        self.assertIn('2 sheet', summary)
        self.assertIn('## Sheet: Penjualan (A1:D6)', text)
        self.assertIn('A2: Kopi | B2: 3 | C2: 15000 | D2: =B2*C2', text)
        self.assertIn('D6: =SUM(D2:D4)', text)
        self.assertIn('B1: TRUE', text)

    def test_powerpoint_slides_titles_bullets_and_notes(self):
        text, summary = self.text('contoh.pptx')
        self.assertIn('2 slide', summary)
        self.assertIn('## Slide 1: Judul Presentasi', text)
        self.assertIn('Subjudul di sini', text)
        self.assertIn('## Slide 2: Agenda', text)
        self.assertIn('Pembahasan', text)
        self.assertIn('Catatan: Catatan pembicara penting', text)

    @unittest.skipUnless(importlib.util.find_spec('pypdf') or shutil.which('pdftotext'), 'no PDF reader available')
    def test_pdf_pages(self):
        text, summary = self.text('contoh.pdf')
        self.assertIn('2 halaman', summary)
        self.assertIn('## Halaman 1', text)
        self.assertIn('Halo dari PDF', text)
        self.assertIn('Halaman dua', text)

    def test_pdf_without_any_reader_explains_what_to_install(self):
        with patch('importlib.util.find_spec', return_value=None), patch.object(shutil, 'which', return_value=None):
            with self.assertRaises(styling.DocumentError) as caught:
                styling.extract_document_text(str(FIXTURES / 'contoh.pdf'))
        self.assertIn('pypdf', str(caught.exception))

    def test_long_documents_are_truncated_with_a_notice(self):
        text, _ = styling.extract_document_text(str(FIXTURES / 'contoh.docx'), limit=40)
        self.assertIn('dipotong', text)

    def test_corrupt_and_wrong_files_give_clear_errors(self):
        folder = tempfile.mkdtemp(prefix='lyra-docs-')
        self.addCleanup(shutil.rmtree, folder, True)
        bad = Path(folder, 'rusak.docx')
        bad.write_bytes(b'bukan zip sama sekali')
        with self.assertRaises(styling.DocumentError) as caught:
            styling.extract_document_text(str(bad))
        self.assertIn('rusak', str(caught.exception))
        empty = make_zip(Path(folder, 'kosong.docx'), {'readme.txt': 'x'})
        with self.assertRaises(styling.DocumentError) as caught:
            styling.extract_document_text(str(empty))
        self.assertIn('bukan dokumen Word', str(caught.exception))
        for legacy, hint in (('lama.doc', '.docx'), ('lama.xls', '.xlsx'), ('lama.ppt', '.pptx')):
            with self.assertRaises(styling.DocumentError) as caught:
                styling.extract_document_text(str(Path(folder, legacy)))
            self.assertIn(hint, str(caught.exception))

    def test_entity_tricks_and_oversized_files_are_refused(self):
        folder = tempfile.mkdtemp(prefix='lyra-docs-')
        self.addCleanup(shutil.rmtree, folder, True)
        evil = make_zip(Path(folder, 'evil.docx'), {'word/document.xml':
            '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'})
        with self.assertRaises(styling.DocumentError) as caught:
            styling.extract_document_text(str(evil))
        self.assertIn('tidak aman', str(caught.exception))
        with patch.object(styling, 'DOCUMENT_MAX_BYTES', 10):
            with self.assertRaises(styling.DocumentError) as caught:
                styling.extract_document_text(str(FIXTURES / 'contoh.docx'))
        self.assertIn('terlalu besar', str(caught.exception))

    def test_large_excel_sheets_are_cut_per_row_and_column(self):
        folder = tempfile.mkdtemp(prefix='lyra-docs-')
        self.addCleanup(shutil.rmtree, folder, True)
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        rows = ''.join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>baris {i}</t></is></c></row>' for i in range(1, 401))
        path = make_zip(Path(folder, 'besar.xlsx'), {
            'xl/workbook.xml': f'<workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>',
            'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="x/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            'xl/worksheets/sheet1.xml': f'<worksheet {ns}><sheetData>{rows}</sheetData></worksheet>'})
        text, _ = styling.extract_document_text(str(path))
        self.assertIn('A300: baris 300', text)
        self.assertNotIn('A301', text)
        self.assertIn('… +100 baris lagi', text)


class ToolIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-docs-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_read_file_returns_document_text_with_a_header(self):
        result = tools.read_file(str(FIXTURES / 'contoh.xlsx'))
        self.assertTrue(result.startswith('[Excel:'))
        self.assertIn('A2: Kopi', result)
        self.assertIn('edit_document', result)

    def test_read_file_no_longer_dumps_binary_garbage(self):
        Path(self.path('a.bin')).write_bytes(b'\x00\x01\x02binary\x00')
        result = tools.read_file(self.path('a.bin'))
        self.assertTrue(result.startswith('Error:'))
        self.assertIn('biner', result)
        Path(self.path('t.txt')).write_text('halo\n', encoding='utf-8')
        self.assertEqual(tools.read_file(self.path('t.txt')), 'halo\n')

    def test_read_file_reports_unreadable_documents_instead_of_crashing(self):
        Path(self.path('x.docx')).write_bytes(b'bukan zip')
        self.assertIn('Error membaca dokumen', tools.read_file(self.path('x.docx')))

    def test_writing_text_over_a_document_is_refused_and_file_untouched(self):
        shutil.copy(FIXTURES / 'contoh.docx', self.path('laporan.docx'))
        before = Path(self.path('laporan.docx')).read_bytes()
        for result in (tools.write_file(self.path('laporan.docx'), 'teks biasa'),
                       tools.edit_file(self.path('laporan.docx'), 'Pendahuluan', 'Penutup')):
            self.assertTrue(result.startswith('Error:'), result)
            self.assertIn('dokumen', result)
        self.assertEqual(Path(self.path('laporan.docx')).read_bytes(), before)
        self.assertTrue(tools.write_file(self.path('catatan.md'), '# ok\n').startswith('✅'))

    def test_at_reference_attaches_document_text(self):
        shutil.copy(FIXTURES / 'contoh.pptx', self.path('slide.pptx'))
        message = styling.prepare_user_message('ringkas @slide.pptx', self.dir)
        self.assertIn('[Referensi dokumen: slide.pptx', message)
        self.assertIn('Agenda', message)
        Path(self.path('lama.doc')).write_bytes(b'x')
        with self.assertRaises(ValueError) as caught:
            styling.prepare_user_message('baca @lama.doc', self.dir)
        self.assertIn('.docx', str(caught.exception))

    def test_system_prompt_describes_documents_and_syntax_checks(self):
        import app
        with patch.object(app, 'read_memory', return_value='(memori uji)'):
            prompt = app.get_current_system_prompt()
        self.assertIn('.docx', prompt)
        self.assertIn('HANYA dengan `edit_document`', prompt)
        self.assertIn('PDF dan format lama', prompt)
        self.assertIn('pemeriksaan sintaks', prompt)


class SyntaxCheckTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-syntax-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))

    def check(self, name, text):
        path = os.path.join(self.dir, name)
        Path(path).write_text(text, encoding='utf-8')
        return tools.check_syntax(path)

    def test_python(self):
        self.assertEqual(self.check('a.py', 'x = 1\n'), ('python', None))
        language, problem = self.check('b.py', 'x = (1,\n')
        self.assertEqual(language, 'python')
        self.assertIn('baris 1', problem)

    def test_json_xml_css(self):
        self.assertEqual(self.check('a.json', '{"a": 1}'), ('JSON', None))
        self.assertIsNotNone(self.check('b.json', '{"a": 1,}')[1])
        self.assertIsNotNone(self.check('a.xml', '<a><b></a>')[1])
        self.assertIsNone(self.check('a.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>')[1])
        self.assertIsNone(self.check('a.css', '/* { */ a { content: "}"; }')[1])
        self.assertIn('tidak seimbang', self.check('b.css', 'a { color: red;')[1])

    def test_html_finds_real_problems_but_accepts_normal_markup(self):
        ok = '<!doctype html><html><head><title>x</title></head><body><ul><li>a<li>b</ul><img src=a><br><p>x</body></html>'
        self.assertEqual(self.check('ok.html', ok), ('HTML', None))
        self.assertIn('belum ditutup', self.check('b.html', '<div><section><p>hi</div>')[1])
        self.assertIn('tanpa pembuka', self.check('c.html', '<div></span></div>')[1])
        self.assertIsNone(self.check('d.html', '<script>if (a < b && c > d) { x = "</"; }</script>')[1])

    def test_unknown_types_are_not_checked(self):
        self.assertEqual(self.check('a.txt', 'x'), (None, None))
        self.assertEqual(self.check('a.md', '# x'), (None, None))

    def test_php_node_and_shell_use_the_real_tools_when_present(self):
        if shutil.which('php'):
            self.assertIsNone(self.check('ok.php', '<?php echo "hi";\n')[1])
            self.assertIn('Parse error', self.check('bad.php', '<?php\n$x = ;\n')[1])
        if shutil.which('node'):
            self.assertIsNone(self.check('ok.js', 'const a = 1;\n')[1])
            self.assertIsNotNone(self.check('bad.js', 'const = ;\n')[1])
        if shutil.which('bash'):
            self.assertIsNone(self.check('ok.sh', 'echo hi\n')[1])
            self.assertIsNotNone(self.check('bad.sh', 'if true; then echo hi\n')[1])

    def test_missing_tool_means_no_check_not_an_error(self):
        with patch.object(shutil, 'which', return_value=None):
            self.assertEqual(self.check('x.php', '<?php $x = ;'), ('PHP', None))

    def test_php_startup_warnings_do_not_hide_the_real_error(self):
        fake = type('Done', (), {'returncode': 255, 'stdout': 'PHP Parse error:  syntax error, unexpected end of file in X on line 2\n',
                                 'stderr': "PHP Warning:  PHP Startup: Unable to load dynamic library 'gd'\n"})()
        with patch.object(shutil, 'which', return_value='/usr/bin/php'), patch.object(tools.subprocess, 'run', return_value=fake):
            message = tools._check_with_tool(['php', '-l'], '/tmp/x.php', pick=r'(?:Parse|Fatal) error')
        self.assertIn('Parse error', message)
        self.assertNotIn('Startup', message)

    def test_write_and_edit_report_the_result_to_the_model(self):
        path = os.path.join(self.dir, 'm.py')
        self.assertIn('✔ Sintaks python valid', tools.write_file(path, 'x = 1\n'))
        broken = tools.edit_file(path, 'x = 1', 'x = (1,')
        self.assertTrue(broken.startswith('✅'))
        self.assertIn('⚠ Pemeriksaan sintaks python GAGAL', broken)
        self.assertIn('edit_file', broken)
        fixed = tools.edit_file(path, 'x = (1,', 'x = 2')
        self.assertIn('✔ Sintaks python valid', fixed)
        self.assertEqual(tools.write_file(os.path.join(self.dir, 'n.md'), '# x\n'), "✅ Berhasil menulis ke '" + os.path.join(self.dir, 'n.md') + "'.")

    def test_a_crashing_checker_never_breaks_the_edit(self):
        with patch.dict(tools.SYNTAX_CHECKS, {'.py': ('python', lambda path, text: 1 / 0)}):
            self.assertTrue(tools.write_file(os.path.join(self.dir, 'z.py'), 'x = 1\n').startswith('✅'))


if __name__ == '__main__':
    unittest.main()
