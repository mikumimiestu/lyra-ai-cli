"""edit_document / create_document for Word and Excel. Everything happens in temporary folders, and the backup folder
is redirected to a temporary one too, so nothing outside them is ever touched."""
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
HAVE_DOCX = importlib.util.find_spec('docx') is not None
HAVE_XLSX = importlib.util.find_spec('openpyxl') is not None


class OfficeBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-office-')
        self.backups = os.path.join(self.dir, 'backups')
        self.addCleanup(shutil.rmtree, self.dir, True)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.output = io.StringIO()
        stack.enter_context(contextlib.redirect_stdout(self.output))
        stack.enter_context(patch.dict(os.environ, {'LYRA_BACKUP_DIR': self.backups}))
        self.confirm = stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))
        tools.UNDO.clear()
        self.addCleanup(tools.UNDO.clear)

    def copy(self, name):
        shutil.copy(FIXTURES / name, os.path.join(self.dir, name))
        return os.path.join(self.dir, name)

    def listing(self):
        return sorted(name for name in os.listdir(self.dir) if name != 'backups')


@unittest.skipUnless(HAVE_DOCX, 'python-docx is not installed')
class WordEditTests(OfficeBase):
    def edit(self, operations, name='contoh.docx', **kw):
        path = self.copy(name) if not os.path.exists(os.path.join(self.dir, name)) else os.path.join(self.dir, name)
        return path, tools.edit_document(path, operations, **kw)

    def text(self, path):
        return styling.extract_document_text(path)[0]

    def test_replace_text_everywhere_and_report_the_count(self):
        path, result = self.edit([{'op': 'replace_text', 'find': 'Staff', 'replace': 'Anggota'}, ])
        self.assertTrue(result.startswith('Error'), result)            # 'Staff' is not in contoh.docx
        self.assertIn('tidak ditemukan', result)
        path, result = self.edit([{'op': 'replace_text', 'find': 'Budi', 'replace': 'Budiman'},
                                  {'op': 'replace_text', 'find': 'Header Dokumen', 'replace': 'Kop Surat'}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('Budiman', text)
        self.assertIn('Header: Kop Surat', text)

    def test_replace_across_runs_keeps_the_first_runs_formatting(self):
        from docx import Document
        path = os.path.join(self.dir, 'runs.docx')
        document = Document()
        paragraph = document.add_paragraph()
        paragraph.add_run('Halo ').bold = False
        bold = paragraph.add_run('Dunia')
        bold.bold = True
        paragraph.add_run(' semua')
        document.save(path)
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Halo Dunia', 'replace': 'Selamat Pagi'}])
        self.assertTrue(result.startswith('✅'), result)
        reopened = Document(path)
        runs = reopened.paragraphs[0].runs
        self.assertEqual(reopened.paragraphs[0].text, 'Selamat Pagi semua')
        self.assertFalse(runs[0].bold)               # the match started in the plain run, so its style wins
        self.assertEqual(runs[-1].text, ' semua')

    def test_replace_first_only_when_all_is_false(self):
        from docx import Document
        path = os.path.join(self.dir, 'dua.docx')
        document = Document()
        document.add_paragraph('kata kata kata')
        document.save(path)
        tools.edit_document(path, [{'op': 'replace_text', 'find': 'kata', 'replace': 'KATA', 'all': False}])
        self.assertEqual(Document(path).paragraphs[0].text, 'KATA kata kata')

    def test_insert_after_a_paragraph_and_at_the_end_of_a_section(self):
        path, result = self.edit([
            {'op': 'insert_paragraph', 'where': 'end_of_section', 'anchor': 'BAB I Pendahuluan',
             'text': ['Tujuan penelitian ada tiga.', 'Manfaat penelitian ada dua.']},
            {'op': 'insert_paragraph', 'where': 'after', 'anchor': 'Rumusan Masalah', 'text': 'Bagaimana topik terbentuk?',
             'style': 'List Bullet'}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertLess(text.index('Teks tebal dan biasa.'), text.index('Tujuan penelitian ada tiga.'))
        self.assertLess(text.index('Tujuan penelitian ada tiga.'), text.index('Manfaat penelitian ada dua.'))
        self.assertLess(text.index('## 1.1 Rumusan Masalah'), text.index('- Bagaimana topik terbentuk?'))

    def test_insert_start_end_and_before(self):
        path, result = self.edit([
            {'op': 'insert_paragraph', 'where': 'start', 'text': 'PALING AWAL'},
            {'op': 'insert_paragraph', 'where': 'end', 'text': 'PALING AKHIR', 'style': 'Heading 2'},
            {'op': 'insert_paragraph', 'where': 'before', 'anchor': 'Latar belakang', 'text': 'Sebelum latar'}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertTrue(text.startswith('PALING AWAL'))
        self.assertIn('## PALING AKHIR', text)
        self.assertLess(text.index('Sebelum latar'), text.index('Latar belakang'))

    def test_ambiguous_anchor_is_refused_with_choices_and_file_untouched(self):
        from docx import Document
        path = os.path.join(self.dir, 'amb.docx')
        document = Document()
        document.add_paragraph('Catatan penting A')
        document.add_paragraph('Catatan penting B')
        document.save(path)
        before = Path(path).read_bytes()
        result = tools.edit_document(path, [{'op': 'insert_paragraph', 'where': 'after', 'anchor': 'Catatan penting', 'text': 'x'}])
        self.assertIn('cocok dengan 2 paragraf', result)
        self.assertIn('occurrence', result)
        self.assertEqual(Path(path).read_bytes(), before)
        ok = tools.edit_document(path, [{'op': 'insert_paragraph', 'where': 'after', 'anchor': 'Catatan penting',
                                         'occurrence': 2, 'text': 'x'}])
        self.assertTrue(ok.startswith('✅'), ok)

    def test_delete_paragraph(self):
        path, result = self.edit([{'op': 'delete_paragraph', 'match': 'Latar belakang penelitian'}])
        self.assertTrue(result.startswith('✅'), result)
        self.assertNotIn('Latar belakang', self.text(path))

    def test_table_cell_row_and_new_table(self):
        path, result = self.edit([
            {'op': 'set_cell', 'table': 1, 'row': 2, 'col': 2, 'text': '23'},
            {'op': 'add_table_row', 'table': 1, 'values': ['Sari', '22', 'Jakarta']},
            {'op': 'add_table', 'where': 'end', 'rows': [['A', 'B'], ['1', '2']]}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('| Budi | 23 | Bandung |', text)
        self.assertIn('| Sari | 22 | Jakarta |', text)
        self.assertIn('| A | B |', text)
        bad = tools.edit_document(path, [{'op': 'set_cell', 'table': 1, 'row': 9, 'col': 1, 'text': 'x'}])
        self.assertIn('di luar tabel', bad)
        self.assertIn('tabel 5 tidak ada', tools.edit_document(path, [{'op': 'set_cell', 'table': 5, 'row': 1, 'col': 1, 'text': 'x'}]))

    def test_a_failing_operation_changes_nothing_and_leaves_no_temp_files(self):
        path = self.copy('contoh.docx')
        before = Path(path).read_bytes()
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'X'},
                                            {'op': 'nonsense'}])
        self.assertIn('operasi #2', result)
        self.assertIn('Tidak ada yang diubah', result)
        self.assertEqual(Path(path).read_bytes(), before)
        self.assertEqual(self.listing(), ['contoh.docx'])

    def test_declining_leaves_the_file_and_cleans_up(self):
        path = self.copy('contoh.docx')
        before = Path(path).read_bytes()
        self.confirm.return_value = False
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'X'}])
        self.assertIn('dibatalkan', result)
        self.assertEqual(Path(path).read_bytes(), before)
        self.assertEqual(self.listing(), ['contoh.docx'])
        self.assertFalse(os.path.exists(self.backups))

    def test_no_op_is_reported_without_asking(self):
        path = self.copy('contoh.docx')
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'Budi'}])
        self.assertIn('Tidak ada perubahan', result)
        self.confirm.assert_not_called()

    def test_backup_and_undo_restore_the_original_bytes(self):
        path = self.copy('contoh.docx')
        original = Path(path).read_bytes()
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'Budiman'}])
        self.assertIn('Cadangan:', result)
        backups = os.listdir(self.backups)
        self.assertEqual(len(backups), 1)
        self.assertEqual(Path(self.backups, backups[0]).read_bytes(), original)
        self.assertIn('Ubah dokumen', tools.describe_undo_stack()[0])
        self.assertTrue(tools.undo_last().startswith('✅'))
        self.assertEqual(Path(path).read_bytes(), original)

    def test_save_as_keeps_the_original_and_refuses_to_overwrite(self):
        path = self.copy('contoh.docx')
        original = Path(path).read_bytes()
        target = os.path.join(self.dir, 'salinan.docx')
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'Budiman'}], save_as=target)
        self.assertIn('Salinan baru', result)
        self.assertEqual(Path(path).read_bytes(), original)
        self.assertIn('Budiman', self.text(target))
        again = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'X'}], save_as=target)
        self.assertIn('sudah ada', again)
        self.assertIn('berekstensi .docx', tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'X'}],
                                                              save_as=os.path.join(self.dir, 'x.txt')))

    def test_bad_requests_get_clear_errors(self):
        path = self.copy('contoh.docx')
        self.assertIn('tidak ditemukan', tools.edit_document(os.path.join(self.dir, 'tidak-ada.docx'), [{'op': 'x'}]))
        self.assertIn('daftar operasi', tools.edit_document(path, 'ganti sesuatu'))
        self.assertIn('daftar operasi', tools.edit_document(path, []))
        self.assertIn('maksimal', tools.edit_document(path, [{'op': 'x'}] * 101))
        pdf = self.copy('contoh.pdf')
        self.assertIn('belum bisa diubah', tools.edit_document(pdf, [{'op': 'x'}]))
        plain = os.path.join(self.dir, 'a.txt')
        Path(plain).write_text('x')
        self.assertIn('edit_file', tools.edit_document(plain, [{'op': 'x'}]))
        broken = os.path.join(self.dir, 'rusak.docx')
        Path(broken).write_bytes(b'bukan zip')
        self.assertTrue(tools.edit_document(broken, [{'op': 'replace_text', 'find': 'a', 'replace': 'b'}]).startswith('Error'))

    def test_create_word_document(self):
        path = os.path.join(self.dir, 'baru.docx')
        result = tools.create_document(path, blocks=[
            {'type': 'title', 'text': 'Laporan'}, {'type': 'heading', 'text': 'Ringkasan', 'level': 1},
            {'type': 'paragraph', 'text': 'Isi laporan.'}, {'type': 'bullets', 'items': ['satu', 'dua']},
            {'type': 'numbered', 'items': ['pertama']}, {'type': 'table', 'rows': [['Nama', 'Nilai'], ['A', '1']]}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('# Laporan', text)
        self.assertIn('# Ringkasan', text)
        self.assertIn('- satu', text)
        self.assertIn('| A | 1 |', text)
        self.assertIn('Buat dokumen', tools.describe_undo_stack()[0])
        self.assertIn('sudah ada', tools.create_document(path, blocks=[{'type': 'paragraph', 'text': 'x'}]))
        self.assertTrue(tools.undo_last().startswith('✅'))
        self.assertFalse(os.path.exists(path))

    def test_create_rejects_bad_input_and_leaves_nothing_behind(self):
        path = os.path.join(self.dir, 'x.docx')
        self.assertIn("'blocks'", tools.create_document(path))
        self.assertIn('tidak dikenal', tools.create_document(path, blocks=[{'type': 'video'}]))
        self.assertIn('hanya membuat', tools.create_document(os.path.join(self.dir, 'x.txt'), blocks=[{'type': 'paragraph'}]))
        self.assertEqual(self.listing(), [])


@unittest.skipUnless(HAVE_XLSX, 'openpyxl is not installed')
class ExcelEditTests(OfficeBase):
    def edit(self, operations, **kw):
        path = os.path.join(self.dir, 'contoh.xlsx')
        if not os.path.exists(path):
            self.copy('contoh.xlsx')
        return path, tools.edit_document(path, operations, **kw)

    def text(self, path):
        return styling.extract_document_text(path)[0]

    def test_cells_ranges_rows_formulas_and_sheets(self):
        path, result = self.edit([
            {'op': 'set_cell', 'sheet': 'Penjualan', 'cell': 'B2', 'value': '4'},
            {'op': 'append_row', 'sheet': 'Penjualan', 'values': ['Roti', 6, 9000, '=B7*C7']},
            {'op': 'add_sheet', 'name': 'Ringkasan'},
            {'op': 'set_range', 'sheet': 'Ringkasan', 'start': 'A1', 'values': [['Total', '=SUM(Penjualan!D2:D7)'], ['Aktif', True]]}])
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn('dihitung ulang', result)
        text = self.text(path)
        self.assertIn('B2: 4', text)
        self.assertIn('A7: Roti | B7: 6 | C7: 9000 | D7: =B7*C7', text)
        self.assertIn('## Sheet: Ringkasan', text)
        self.assertIn('B1: =SUM(Penjualan!D2:D7)', text)
        self.assertIn('B2: TRUE', text)

    def test_numbers_sent_as_text_become_numbers_but_ids_stay_text(self):
        self.assertEqual(tools._excel_value('15000'), 15000)
        self.assertEqual(tools._excel_value('12.5'), 12.5)
        self.assertEqual(tools._excel_value('0812345'), '0812345')
        self.assertEqual(tools._excel_value('=SUM(A1:A2)'), '=SUM(A1:A2)')
        self.assertEqual(tools._excel_value('Kopi'), 'Kopi')
        self.assertIsNone(tools._excel_value(None))
        with self.assertRaises(tools.OperationError):
            tools._excel_value({'a': 1})

    def test_the_diff_does_not_show_every_formula_as_changed(self):
        path = self.copy('contoh.xlsx')
        self.output.truncate(0)
        self.output.seek(0)
        tools.edit_document(path, [{'op': 'set_cell', 'sheet': 'Penjualan', 'cell': 'A2', 'value': 'Kopi Hitam'}])
        shown = styling.strip_ansi(self.output.getvalue())
        self.assertIn('Kopi Hitam', shown)
        self.assertNotIn('D3', shown.replace('D3: =B3*C3', ''))        # untouched formula rows are not part of the diff

    def test_errors_are_specific_and_change_nothing(self):
        path = self.copy('contoh.xlsx')
        before = Path(path).read_bytes()
        for operation, fragment in (
                ({'op': 'set_cell', 'sheet': 'Hilang', 'cell': 'A1', 'value': 1}, 'Sheet yang ada'),
                ({'op': 'set_cell', 'cell': 'ZZZZ1', 'value': 1}, 'tidak valid'),
                ({'op': 'set_cell', 'cell': 'A1', 'value': {'x': 1}}, 'teks, angka'),
                ({'op': 'append_row', 'values': []}, "butuh 'values'"),
                ({'op': 'add_sheet', 'name': 'Penjualan'}, 'sudah ada'),
                ({'op': 'add_sheet', 'name': 'a/b'}, 'nama sheet'),
                ({'op': 'hapus_semua'}, 'tidak dikenal')):
            result = tools.edit_document(path, [operation])
            self.assertTrue(result.startswith('Error'), (operation, result))
            self.assertIn(fragment, result)
        self.assertEqual(Path(path).read_bytes(), before)
        self.assertEqual(self.listing(), ['contoh.xlsx'])

    def test_workbooks_with_charts_are_only_edited_as_a_copy(self):
        import openpyxl
        from openpyxl.chart import BarChart, Reference
        path = os.path.join(self.dir, 'grafik.xlsx')
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        for row in ([1, 2], [3, 4]):
            sheet.append(row)
        chart = BarChart()
        chart.add_data(Reference(sheet, min_col=1, min_row=1, max_row=2))
        sheet.add_chart(chart, 'D2')
        workbook.save(path)
        original = Path(path).read_bytes()
        refused = tools.edit_document(path, [{'op': 'set_cell', 'cell': 'A1', 'value': 9}])
        self.assertIn('HILANG', refused)
        self.assertIn('save_as', refused)
        self.assertEqual(Path(path).read_bytes(), original)
        copy = os.path.join(self.dir, 'grafik-salinan.xlsx')
        ok = tools.edit_document(path, [{'op': 'set_cell', 'cell': 'A1', 'value': 9}], save_as=copy)
        self.assertIn('Salinan baru', ok)
        self.assertEqual(Path(path).read_bytes(), original)

    def test_create_excel_with_bold_header_and_widths(self):
        import openpyxl
        path = os.path.join(self.dir, 'data.xlsx')
        result = tools.create_document(path, sheets=[
            {'name': 'Data', 'rows': [['Nama', 'Qty'], ['Kopi Susu Gula Aren', '3'], ['Teh', 5]]},
            {'name': 'Kosong', 'rows': []}])
        self.assertTrue(result.startswith('✅'), result)
        workbook = openpyxl.load_workbook(path)
        sheet = workbook['Data']
        self.assertTrue(sheet['A1'].font.bold)
        self.assertEqual(sheet['B2'].value, 3)
        self.assertGreater(sheet.column_dimensions['A'].width, 15)
        self.assertEqual(workbook.sheetnames, ['Data', 'Kosong'])
        self.assertIn('nama sheet', tools.create_document(os.path.join(self.dir, 'y.xlsx'), sheets=[{'name': 'a/b', 'rows': []}]))
        self.assertIn('duplikat', tools.create_document(os.path.join(self.dir, 'z.xlsx'),
                                                        sheets=[{'name': 'A', 'rows': []}, {'name': 'A', 'rows': []}]))


class PackageAndPlumbingTests(OfficeBase):
    def test_missing_library_asks_before_installing_and_respects_a_refusal(self):
        self.confirm.return_value = False
        path = self.copy('contoh.docx')
        with patch('importlib.util.find_spec', return_value=None):
            result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Budi', 'replace': 'X'}])
        self.assertIn('python-docx', result)
        self.assertIn('dibatalkan', result)
        details = self.confirm.call_args[0][1]
        self.assertIn('pip install python-docx', details['Perintah'])

    def test_missing_library_is_installed_after_consent(self):
        import importlib
        calls = []

        def fake_find_spec(name, *args):
            return None if not calls else object()
        with patch('importlib.util.find_spec', side_effect=fake_find_spec), \
             patch('config.install_packages', side_effect=lambda specs: (calls.append(specs) or (True, 'terpasang'))):
            self.assertIsNone(tools._need_package('docx', 'python-docx'))
        self.assertEqual(calls, [['python-docx']])

    def test_failed_install_is_reported_with_the_manual_command(self):
        with patch('importlib.util.find_spec', return_value=None), \
             patch('config.install_packages', return_value=(False, 'offline')):
            result = tools._need_package('openpyxl', 'openpyxl')
        self.assertIn('gagal memasang', result)
        self.assertIn('python -m pip install openpyxl', result)

    def test_backup_folder_keeps_only_the_newest_files(self):
        source = os.path.join(self.dir, 'a.docx')
        Path(source).write_bytes(b'x')
        with patch.object(tools, 'DOC_BACKUP_KEEP', 3), patch.object(tools.time, 'strftime', side_effect=[f'2026010{i}-000000-' for i in range(1, 7)]):
            for _ in range(6):
                self.assertTrue(tools._backup_file(source))
        self.assertEqual(len(os.listdir(self.backups)), 3)
        self.assertTrue(sorted(os.listdir(self.backups))[-1].startswith('20260106'))
        if os.name == 'posix':
            self.assertEqual(os.stat(self.backups).st_mode & 0o777, 0o700)

    def test_write_and_edit_file_point_to_the_document_tools(self):
        path = self.copy('contoh.docx')
        self.assertIn('edit_document', tools.write_file(path, 'x'))
        self.assertIn('edit_document', tools.edit_file(path, 'a', 'b'))
        pdf = self.copy('contoh.pdf')
        self.assertNotIn('edit_document', tools.write_file(pdf, 'x'))
        self.assertIn('edit_document', tools.write_file(self.copy('contoh.pptx'), 'x'))

    def test_prompt_and_activity_know_the_new_tools(self):
        import app
        with patch.object(app, 'read_memory', return_value='(memori uji)'):
            prompt = app.get_current_system_prompt()
        for name in ('edit_document', 'create_document', 'replace_text', 'end_of_section', 'save_as', 'fill_template',
                     'duplicate_slide', 'set_notes'):
            self.assertIn(name, prompt)
        self.assertEqual(styling.tool_call_parts('edit_document', {'filepath': 'a.docx'}), ('Ubah dokumen', 'a.docx'))
        self.assertEqual(styling.tool_call_parts('create_document', {'filepath': 'b.xlsx'}), ('Buat dokumen', 'b.xlsx'))
        self.assertEqual(styling.activity_group('edit_document', {}), 'Perubahan')

    def test_the_agent_loop_dispatches_both_tools(self):
        import app
        source = Path(app.__file__).read_text(encoding='utf-8')
        self.assertIn('func_name == "edit_document"', source)
        self.assertIn('func_name == "create_document"', source)


if __name__ == '__main__':
    unittest.main()
