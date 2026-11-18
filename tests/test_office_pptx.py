"""PowerPoint editing, {{placeholder}} templates for Word/Excel/PowerPoint, and filling many documents from rows of data."""
import base64
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
HAVE = all(importlib.util.find_spec(name) is not None for name in ('pptx', 'docx', 'openpyxl'))
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAHnOcQAAAAABJRU5ErkJggg==')


@unittest.skipUnless(HAVE, 'python-pptx, python-docx and openpyxl are required')
class OfficeCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='lyra-pptx-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.output = io.StringIO()
        stack.enter_context(contextlib.redirect_stdout(self.output))
        stack.enter_context(patch.dict(os.environ, {'LYRA_BACKUP_DIR': os.path.join(self.dir, 'backups')}))
        self.confirm = stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))
        tools.UNDO.clear()
        self.addCleanup(tools.UNDO.clear)

    def path(self, name):
        return os.path.join(self.dir, name)

    def copy(self, name):
        shutil.copy(FIXTURES / name, self.path(name))
        return self.path(name)

    def text(self, path):
        return styling.extract_document_text(path)[0]

    def slides(self, path):
        from pptx import Presentation
        return list(Presentation(path).slides)

    def listing(self):
        return sorted(name for name in os.listdir(self.dir) if name != 'backups')


class PowerPointEditTests(OfficeCase):
    def edit(self, operations, **kw):
        path = self.copy('contoh.pptx') if not os.path.exists(self.path('contoh.pptx')) else self.path('contoh.pptx')
        return path, tools.edit_document(path, operations, **kw)

    def test_replace_text_in_slides_and_notes_or_one_slide(self):
        path, result = self.edit([{'op': 'replace_text', 'find': 'Pembukaan', 'replace': 'Sambutan'},
                                  {'op': 'replace_text', 'find': 'pembicara penting', 'replace': 'pembicara utama'}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('Sambutan', text)
        self.assertIn('Catatan pembicara utama', text)
        scoped = tools.edit_document(path, [{'op': 'replace_text', 'slide': 1, 'find': 'Agenda', 'replace': 'X'}])
        self.assertIn('tidak ditemukan', scoped)

    def test_set_text_by_title_body_and_match(self):
        path, result = self.edit([{'op': 'set_text', 'slide': 1, 'shape': 'title', 'text': 'Judul Baru'},
                                  {'op': 'set_text', 'slide': 2, 'shape': 'body', 'text': 'Satu\nDua\nTiga'},
                                  {'op': 'set_text', 'slide': 1, 'match': 'Subjudul', 'text': 'Subjudul Baru'}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('## Slide 1: Judul Baru', text)
        self.assertIn('Subjudul Baru', text)
        for word in ('Satu', 'Dua', 'Tiga'):
            self.assertIn(word, text)
        self.assertNotIn('Pembahasan', text)
        bad = tools.edit_document(path, [{'op': 'set_text', 'slide': 2, 'match': 'tidak ada', 'text': 'x'}])
        self.assertIn('tidak ada teks yang memuat', bad)
        self.assertIn('slide 9 tidak ada', tools.edit_document(path, [{'op': 'set_text', 'slide': 9, 'shape': 'title', 'text': 'x'}]))

    def test_add_slide_with_layout_levels_notes_and_position(self):
        path, result = self.edit([{'op': 'add_slide', 'layout': 'title_content', 'title': 'Hasil',
                                   'body': ['Poin A', {'text': 'Rincian A1', 'level': 1}, 'Poin B'],
                                   'notes': 'Bicara pelan', 'position': 2}])
        self.assertTrue(result.startswith('✅'), result)
        slides = self.slides(path)
        self.assertEqual(len(slides), 3)
        self.assertEqual(slides[1].shapes.title.text_frame.text, 'Hasil')
        body = [s for s in slides[1].placeholders if s.placeholder_format.idx == 1][0].text_frame
        self.assertEqual([p.level for p in body.paragraphs], [0, 1, 0])
        self.assertEqual(slides[1].notes_slide.notes_text_frame.text, 'Bicara pelan')
        self.assertIn('## Slide 3: Agenda', self.text(path))

    def test_unknown_layout_lists_the_choices(self):
        path = self.copy('contoh.pptx')
        result = tools.edit_document(path, [{'op': 'add_slide', 'layout': 'tidak-ada', 'title': 'x'}])
        self.assertIn('Layout:', result)
        self.assertIn('Title Slide', result)
        self.assertIn('Tidak ada yang diubah', result)

    def test_delete_move_and_notes(self):
        path, result = self.edit([{'op': 'add_slide', 'layout': 'title_content', 'title': 'Tiga', 'body': 'x'},
                                  {'op': 'move_slide', 'slide': 3, 'to': 1},
                                  {'op': 'set_notes', 'slide': 2, 'text': 'Catatan baru'},
                                  {'op': 'delete_slide', 'slide': 2}])
        self.assertTrue(result.startswith('✅'), result)
        slides = self.slides(path)
        self.assertEqual([s.shapes.title.text_frame.text for s in slides], ['Tiga', 'Agenda'])
        with zipfile.ZipFile(path) as archive:        # the deleted slide's part must not linger in the file
            self.assertEqual(len([n for n in archive.namelist() if n.startswith('ppt/slides/slide')]), 2)
        self.assertIn('Slide 1: Tiga', self.text(path))

    def test_duplicate_slide_copies_text_and_notes(self):
        path, result = self.edit([{'op': 'duplicate_slide', 'slide': 2}])
        self.assertTrue(result.startswith('✅'), result)
        slides = self.slides(path)
        self.assertEqual(len(slides), 3)
        self.assertEqual(slides[2].shapes.title.text_frame.text, 'Agenda')
        self.assertEqual(slides[2].notes_slide.notes_text_frame.text, 'Catatan pembicara penting')

    def test_duplicate_is_refused_for_slides_with_pictures(self):
        from pptx import Presentation
        picture = self.path('pixel.png')
        Path(picture).write_bytes(PNG)
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.shapes.add_picture(picture, 0, 0)
        path = self.path('gambar.pptx')
        deck.save(path)
        before = Path(path).read_bytes()
        result = tools.edit_document(path, [{'op': 'duplicate_slide', 'slide': 1}])
        self.assertIn('gambar', result)
        self.assertEqual(Path(path).read_bytes(), before)

    def test_pictures_survive_other_edits(self):
        from pptx import Presentation
        picture = self.path('pixel.png')
        Path(picture).write_bytes(PNG)
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = 'Dengan gambar'
        slide.shapes.add_picture(picture, 0, 0)
        path = self.path('gambar.pptx')
        deck.save(path)
        result = tools.edit_document(path, [{'op': 'replace_text', 'find': 'Dengan gambar', 'replace': 'Tetap ada gambar'}])
        self.assertTrue(result.startswith('✅'), result)
        with zipfile.ZipFile(path) as archive:
            self.assertTrue(any(n.startswith('ppt/media/') for n in archive.namelist()))

    def test_table_cells(self):
        from pptx import Presentation
        from pptx.util import Inches
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = 'Tabel'
        table = slide.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
        table.cell(0, 0).text, table.cell(0, 1).text, table.cell(1, 0).text, table.cell(1, 1).text = 'A', 'B', 'C', 'D'
        path = self.path('tabel.pptx')
        deck.save(path)
        result = tools.edit_document(path, [{'op': 'set_cell', 'slide': 1, 'table': 1, 'row': 2, 'col': 2, 'text': 'Z'}])
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn('| C | Z |', self.text(path))
        self.assertIn('di luar tabel', tools.edit_document(path, [{'op': 'set_cell', 'slide': 1, 'row': 5, 'col': 1, 'text': 'x'}]))
        self.assertIn('0 tabel', tools.edit_document(self.copy('contoh.pptx'), [{'op': 'set_cell', 'slide': 1, 'row': 1, 'col': 1, 'text': 'x'}]))

    def test_unknown_operation_and_decline_change_nothing(self):
        path = self.copy('contoh.pptx')
        before = Path(path).read_bytes()
        self.assertIn('tidak dikenal untuk PowerPoint', tools.edit_document(path, [{'op': 'animasi'}]))
        self.confirm.return_value = False
        self.assertIn('dibatalkan', tools.edit_document(path, [{'op': 'replace_text', 'find': 'Agenda', 'replace': 'X'}]))
        self.assertEqual(Path(path).read_bytes(), before)
        self.assertEqual(self.listing(), ['contoh.pptx'])

    def test_backup_and_undo_for_a_deck(self):
        path = self.copy('contoh.pptx')
        original = Path(path).read_bytes()
        self.assertIn('Cadangan:', tools.edit_document(path, [{'op': 'replace_text', 'find': 'Agenda', 'replace': 'Rencana'}]))
        self.assertIn('Rencana', self.text(path))
        self.assertTrue(tools.undo_last().startswith('✅'))
        self.assertEqual(Path(path).read_bytes(), original)

    def test_create_a_presentation(self):
        path = self.path('baru.pptx')
        result = tools.create_document(path, slides=[
            {'layout': 'title', 'title': 'Judul Besar', 'body': 'Subjudul'},
            {'title': 'Agenda', 'body': ['Satu', 'Dua'], 'notes': 'Catatan'},
            {'layout': 'section', 'title': 'Bagian 2'}])
        self.assertTrue(result.startswith('✅'), result)
        slides = self.slides(path)
        self.assertEqual(len(slides), 3)
        from pptx import Presentation
        self.assertGreater(Presentation(path).slide_width, Presentation(path).slide_height * 1.7)       # 16:9
        text = self.text(path)
        self.assertIn('## Slide 1: Judul Besar', text)
        self.assertIn('Catatan: Catatan', text)
        self.assertIn('sudah ada', tools.create_document(path, slides=[{'title': 'x'}]))
        self.assertIn("'slides'", tools.create_document(self.path('kosong.pptx')))
        self.assertIn('Layout:', tools.create_document(self.path('x.pptx'), slides=[{'layout': 'nope', 'title': 'x'}]))
        self.assertEqual(self.listing(), ['baru.pptx'])


class TemplateTests(OfficeCase):
    def word_template(self):
        from docx import Document
        path = self.path('surat.docx')
        document = Document()
        document.add_paragraph('Kepada {{nama}}, kelas {{kelas}}.')
        split = document.add_paragraph()
        split.add_run('Tanggal: {{tan')
        split.add_run('ggal}}').bold = True
        document.add_table(rows=1, cols=2).cell(0, 0).text = '{{nama}}'
        document.sections[0].header.paragraphs[0].text = 'Surat untuk {{ nama }}'
        document.save(path)
        return path

    def test_fill_word_including_split_runs_tables_and_headers(self):
        path = self.word_template()
        result = tools.edit_document(path, [{'op': 'fill_template', 'values': {'nama': 'Budi', 'kelas': 'A', 'tanggal': '1 Januari'}}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(path)
        self.assertIn('Kepada Budi, kelas A.', text)
        self.assertIn('Tanggal: 1 Januari', text)
        self.assertIn('| Budi |', text)
        self.assertIn('Header: Surat untuk Budi', text)
        self.assertNotIn('{{', text)

    def test_unused_keys_and_leftover_placeholders_are_reported(self):
        path = self.word_template()
        result = tools.edit_document(path, [{'op': 'fill_template', 'values': {'nama': 'Budi', 'nilai': '90'}}])
        self.assertTrue(result.startswith('✅'), result)
        self.assertIn('kunci tidak ditemukan di template: nilai', result)
        self.assertIn('{{kelas}}', result)

    def test_no_matching_key_is_an_error(self):
        path = self.word_template()
        before = Path(path).read_bytes()
        result = tools.edit_document(path, [{'op': 'fill_template', 'values': {'x': '1'}}])
        self.assertIn('tidak ada placeholder', result)
        self.assertEqual(Path(path).read_bytes(), before)
        self.assertIn("butuh 'values'", tools.edit_document(path, [{'op': 'fill_template'}]))

    def test_fill_powerpoint_and_excel(self):
        from pptx import Presentation
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[0])
        slide.shapes.title.text = 'Halo {{nama}}'
        slide.placeholders[1].text = 'Acara {{acara}}'
        slide.notes_slide.notes_text_frame.text = 'Sapa {{nama}}'
        deck_path = self.path('sambutan.pptx')
        deck.save(deck_path)
        result = tools.edit_document(deck_path, [{'op': 'fill_template', 'values': {'nama': 'Sari', 'acara': 'Rapat'}}])
        self.assertTrue(result.startswith('✅'), result)
        text = self.text(deck_path)
        self.assertIn('Halo Sari', text)
        self.assertIn('Acara Rapat', text)
        self.assertIn('Sapa Sari', text)

        import openpyxl
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet['A1'], sheet['A2'], sheet['B2'] = 'Untuk {{nama}}', '{{jumlah}}', '{{kode}}'
        xlsx_path = self.path('tagihan.xlsx')
        workbook.save(xlsx_path)
        result = tools.edit_document(xlsx_path, [{'op': 'fill_template', 'values': {'nama': 'Budi', 'jumlah': 15000, 'kode': '0812'}}])
        self.assertTrue(result.startswith('✅'), result)
        filled = openpyxl.load_workbook(xlsx_path).active
        self.assertEqual(filled['A1'].value, 'Untuk Budi')
        self.assertEqual(filled['A2'].value, 15000)             # a whole-cell placeholder becomes a real number
        self.assertEqual(filled['B2'].value, '0812')            # but IDs with a leading zero stay text

    def test_merge_many_documents_from_rows(self):
        template = self.word_template()
        rows = [{'nama': 'Budi', 'kelas': 'A', 'tanggal': '1 Jan'}, {'nama': 'Sari / Putri', 'kelas': 'B', 'tanggal': '2 Jan'}]
        result = tools.fill_template(template, rows, 'surat-{nama}.docx')
        self.assertTrue(result.startswith('✅ 2 dokumen'), result)
        self.assertEqual(self.listing(), ['surat-Budi.docx', 'surat-Sari _ Putri.docx', 'surat.docx'])      # unsafe characters are replaced
        self.assertIn('Kepada Budi', self.text(self.path('surat-Budi.docx')))
        self.assertIn('Kepada Sari / Putri', self.text(self.path('surat-Sari _ Putri.docx')))
        self.assertIn('{{nama}}', self.text(template))          # the template itself is never touched
        self.assertEqual(len(tools.UNDO.items), 2)
        self.assertTrue(tools.undo_last().startswith('✅'))

    def test_merge_default_names_and_other_formats(self):
        from pptx import Presentation
        deck = Presentation()
        deck.slides.add_slide(deck.slide_layouts[5]).shapes.title.text = 'Untuk {{nama}}'
        template = self.path('kartu.pptx')
        deck.save(template)
        result = tools.fill_template(template, [{'nama': 'A'}, {'nama': 'B'}])
        self.assertTrue(result.startswith('✅ 2 dokumen'), result)
        self.assertIn('Untuk B', self.text(self.path('kartu-2.pptx')))

    def test_merge_refuses_unsafe_or_conflicting_requests_and_creates_nothing(self):
        template = self.word_template()
        Path(self.path('surat-Budi.docx')).write_bytes(b'ada')
        listing_before = self.listing()
        for call, fragment in (
                (lambda: tools.fill_template(template, [{'nama': 'Budi'}], 'surat-{nama}.docx'), 'sudah ada'),
                (lambda: tools.fill_template(template, [{'nama': 'A'}, {'nama': 'A'}], 'x-{nama}.docx'), 'kembar'),
                (lambda: tools.fill_template(template, [{'nama': 'A'}], '../keluar.docx'), 'relatif'),
                (lambda: tools.fill_template(template, [{'nama': 'A'}], '/tmp/abs.docx'), 'relatif'),
                (lambda: tools.fill_template(template, [{'nama': 'A'}], 'x.xlsx'), 'berekstensi'),
                (lambda: tools.fill_template(template, [{'nama': str(i)} for i in range(51)]), 'maksimal 50'),
                (lambda: tools.fill_template(template, []), "'rows'"),
                (lambda: tools.fill_template(template, ['bukan objek']), "'rows'"),
                (lambda: tools.fill_template(self.path('tidak-ada.docx'), [{'a': 1}]), 'tidak ditemukan'),
                (lambda: tools.fill_template(self.path('a.txt'), [{'a': 1}]), 'harus berupa'),
                (lambda: tools.fill_template(template, [{'x': 'tidak cocok'}]), 'tidak ada placeholder')):
            result = call()
            self.assertTrue(result.startswith('Error'), (fragment, result))
            self.assertIn(fragment, result)
        self.assertEqual(self.listing(), listing_before)

    def test_declining_the_merge_leaves_no_files_or_temp_files(self):
        template = self.word_template()
        self.confirm.return_value = False
        result = tools.fill_template(template, [{'nama': 'A', 'kelas': 'x', 'tanggal': 'y'}])
        self.assertIn('dibatalkan', result)
        self.assertEqual(self.listing(), ['surat.docx'])

    def test_a_bad_row_stops_everything(self):
        template = self.word_template()
        result = tools.fill_template(template, [{'nama': 'A', 'kelas': 'x', 'tanggal': 'y'}, {'zzz': '1'}])
        self.assertIn('baris 2', result)
        self.assertIn('Tidak ada yang dibuat', result)
        self.assertEqual(self.listing(), ['surat.docx'])

    def test_prompt_and_dispatch_know_the_batch_tool(self):
        import app
        self.assertIn('func_name == "fill_template"', Path(app.__file__).read_text(encoding='utf-8'))
        self.assertEqual(styling.tool_call_parts('fill_template', {'template': 'a.docx'}), ('Isi template', 'a.docx'))


if __name__ == '__main__':
    unittest.main()
