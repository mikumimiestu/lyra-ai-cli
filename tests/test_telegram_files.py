"""Files over Telegram: documents and photos from the phone are saved and handed to Lyra; Lyra can send files back, always
after asking, and never secrets. Fake Telegram only."""
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import styling
import tools
from faketelegram import FakeTelegram
from test_telegram import BridgeCase


class FilesCase(BridgeCase):
    def setUp(self):
        super().setUp()
        self.inbox_dir = os.path.join(tempfile.mkdtemp(prefix='lyra-inbox-'), 'masuk')
        self.work = tempfile.mkdtemp(prefix='lyra-files-')
        for folder in (os.path.dirname(self.inbox_dir), self.work):
            self.addCleanup(__import__('shutil').rmtree, folder, True)
        patcher = patch.dict(os.environ, {'LYRA_INBOX_DIR': self.inbox_dir})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.pair()
        self.fake.wait_for(lambda: self.fake.sent(555))
        self.fake.calls.clear()

    def next_item(self, timeout=6):
        self.assertTrue(self.fake.wait_for(lambda: not self.live.inbox.empty(), timeout), self.fake.sent(555))
        return self.live.inbox.get_nowait()


class ReceivingTests(FilesCase):
    def test_a_document_is_saved_privately_and_offered_to_lyra_as_a_file_reference(self):
        self.fake.send_document('catatan rapat.txt', 'Keputusan: rilis hari Jumat.\n'.encode())
        item = self.next_item()
        self.assertIsInstance(item, app.RemoteText)
        self.assertTrue(item.startswith('File dari Telegram: catatan rapat.txt'))
        self.assertIn('Ringkas isi file ini.', item)
        saved = os.listdir(self.inbox_dir)
        self.assertEqual(len(saved), 1)
        path = os.path.join(self.inbox_dir, saved[0])
        self.assertEqual(Path(path).read_text(), 'Keputusan: rilis hari Jumat.\n')
        self.assertIn(f'@"{path}"', item)
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(os.stat(self.inbox_dir).st_mode), 0o700)
        attached = styling.prepare_user_message(str(item), self.work)         # the real loop turns the reference into content
        self.assertIn('Keputusan: rilis hari Jumat.', attached)

    def test_the_caption_becomes_the_instruction(self):
        self.fake.send_document('data.csv', b'a,b\n1,2\n', caption='hitung total kolom b')
        item = self.next_item()
        self.assertIn('hitung total kolom b', item)
        self.assertNotIn('Ringkas isi file ini.', item)

    def test_office_documents_and_pdfs_arrive_readable(self):
        fixtures = Path(__file__).resolve().parent / 'fixtures'
        self.fake.send_document('laporan.xlsx', (fixtures / 'contoh.xlsx').read_bytes())
        item = self.next_item()
        text = styling.prepare_user_message(str(item), self.work)
        self.assertIn('A2: Kopi', text)

    def test_a_photo_is_saved_and_only_used_when_there_is_a_caption(self):
        self.fake.send_photo(b'\xff\xd8\xff\xe0fakejpeg')
        self.assertTrue(self.fake.wait_for(lambda: any('Gambar tersimpan' in t for t in self.fake.sent(555))))
        self.assertTrue(self.live.inbox.empty())                              # no model call is spent on an image Lyra cannot see
        self.assertEqual(len(os.listdir(self.inbox_dir)), 1)
        self.fake.send_photo(b'\xff\xd8\xff\xe0fakejpeg2', caption='/hapus semuanya')
        item = self.next_item()
        self.assertTrue(item.startswith('Pesan: /hapus semuanya'))             # a caption can never act as a command
        self.assertIn('tidak bisa melihat isi gambar', item)

    def test_file_names_cannot_escape_the_inbox(self):
        for name in ('../../etc/passwd', '..\\..\\boot.ini', '/abs/path.txt', 'a\x00b.txt', '   ', '.hidden'):
            self.fake.send_document(name, b'x')
        self.assertTrue(self.fake.wait_for(lambda: len(os.listdir(self.inbox_dir)) >= 6 if os.path.isdir(self.inbox_dir) else False))
        for saved in os.listdir(self.inbox_dir):
            self.assertEqual(os.path.dirname(os.path.join(self.inbox_dir, saved)), self.inbox_dir)
            self.assertNotIn('..', saved)
        self.assertEqual(app.telegram_safe_name('../../x/y.txt'), 'y.txt')
        self.assertEqual(app.telegram_safe_name(''), 'file')
        self.assertEqual(len(app.telegram_safe_name('a' * 300)), 80)

    def test_oversized_files_are_refused_before_and_while_downloading(self):
        self.fake.send_document('besar.bin', b'x', declared_size=app.TELEGRAM_DOWNLOAD_LIMIT + 1)
        self.assertTrue(self.fake.wait_for(lambda: any('terlalu besar' in t for t in self.fake.sent(555))))
        self.assertEqual(self.fake.calls_to('getFile'), [])
        self.fake.calls.clear()
        with patch.object(app, 'TELEGRAM_DOWNLOAD_LIMIT', 1000):            # a sender that lies about the size is cut off
            self.fake.send_document('bohong.bin', b'y' * 5000, declared_size=10)
            self.assertTrue(self.fake.wait_for(lambda: any('Gagal menerima file' in t for t in self.fake.sent(555))))
        self.assertEqual([n for n in os.listdir(self.inbox_dir) if 'bohong' in n], [])

    def test_download_failures_are_reported_to_the_phone(self):
        self.fake.send_document('hilang.txt', b'x')
        self.fake.files.clear()                                              # Telegram "forgets" the file
        self.assertTrue(self.fake.wait_for(lambda: any('Gagal menerima file' in t for t in self.fake.sent(555))))
        self.assertTrue(self.live.inbox.empty())

    def test_only_the_owner_can_send_files_and_old_or_group_files_are_ignored(self):
        self.fake.send_document('asing.txt', b'x', chat=777)
        self.fake.send_document('lain.txt', b'x', sender=888)
        self.fake.send_document('lama.txt', b'x', age=3600)
        self.settle(0.8)
        self.assertEqual(self.fake.calls_to('getFile'), [])
        self.assertTrue(self.live.inbox.empty())
        self.assertFalse(os.path.isdir(self.inbox_dir) and os.listdir(self.inbox_dir))
        self.assertEqual(self.fake.sent(777), [])

    def test_a_pairing_only_terminal_says_to_start_the_gateway(self):
        self.bridge.pairing_only = True
        self.fake.send_document('x.txt', b'x')
        self.assertTrue(self.fake.wait_for(lambda: any('amagi gateway' in t for t in self.fake.sent(555))))
        self.assertEqual(self.fake.calls_to('getFile'), [])

    def test_a_busy_lyra_queues_the_file(self):
        self.live.busy = True
        self.fake.send_document('antre.txt', b'x')
        self.assertTrue(self.fake.wait_for(lambda: any('antrean' in t for t in self.fake.sent(555))))
        self.assertEqual(len(self.inbox()), 1)

    def test_the_inbox_keeps_only_the_newest_files(self):
        os.makedirs(self.inbox_dir)
        for number in range(8):
            path = os.path.join(self.inbox_dir, f'f{number}.txt')
            Path(path).write_text('x')
            os.utime(path, (1000 + number, 1000 + number))
        app.prune_inbox(self.inbox_dir, keep=3)
        self.assertEqual(sorted(os.listdir(self.inbox_dir)), ['f5.txt', 'f6.txt', 'f7.txt'])

    def test_download_errors_never_contain_the_token(self):
        with patch.dict(os.environ, {'LYRA_TELEGRAM_API': 'http://127.0.0.1:9'}):
            with self.assertRaises(app.TelegramError) as caught:
                self.bridge._download('documents/x.txt', 'x.txt')
        self.assertNotIn(app.TelegramBridge, [type(caught.exception)])
        self.assertNotIn(self.config['telegram_token'], str(caught.exception))

    def test_unreadable_files_are_explained_on_the_phone_by_the_session_loop(self):
        source = Path(app.__file__).read_text(encoding='utf-8')
        self.assertIn('telegram["bridge"].send(f"⚠️ {error}")', source)


class SendingTests(FilesCase):
    def make(self, name, content=b'isi laporan', folder=None):
        folder = folder or self.work
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        Path(path).write_bytes(content)
        return path

    def send(self, path, caption=None, approve=True):
        with patch.object(app, '_confirm_permission', return_value=approve) as confirm:
            return app.send_file_to_telegram(self.bridge, path, caption), confirm

    def test_a_document_is_uploaded_to_the_paired_chat_after_approval(self):
        path = self.make('laporan.docx', b'PK-isi')
        result, confirm = self.send(path, caption='Laporan mingguan')
        self.assertTrue(result.startswith('✅ Terkirim ke Telegram: laporan.docx'), result)
        upload = self.fake.uploads[0]
        self.assertEqual((upload['method'], upload['field'], upload['filename'], upload['content']),
                         ('sendDocument', 'document', 'laporan.docx', b'PK-isi'))
        self.assertEqual(upload['fields'], {'chat_id': '555', 'caption': 'Laporan mingguan'})
        details = confirm.call_args[0][1]
        self.assertEqual(confirm.call_args[1]['kind'], 'send')
        self.assertEqual(details['Path'], path)
        self.assertIn('server Telegram', details['Peringatan'])

    def test_images_go_as_photos_and_captions_are_cut(self):
        result, _ = self.send(self.make('grafik.png', b'\x89PNG'), caption='x' * 3000)
        self.assertIn('✅', result)
        upload = self.fake.uploads[-1]
        self.assertEqual((upload['method'], upload['field']), ('sendPhoto', 'photo'))
        self.assertEqual(len(upload['fields']['caption']), 1000)
        with patch.object(app, 'TELEGRAM_PHOTO_LIMIT', 3):                      # too big for a photo: sent as a document instead
            self.send(self.make('besar.png', b'\x89PNG-lebih-besar'))
        self.assertEqual(self.fake.uploads[-1]['method'], 'sendDocument')

    def test_declining_uploads_nothing(self):
        result, _ = self.send(self.make('rahasia-kantor.txt'), approve=False)
        self.assertIn('dibatalkan', result)
        self.assertEqual(self.fake.uploads, [])

    def test_secrets_and_lyras_own_files_are_never_sent_even_if_approved(self):
        blocked = [
            self.make('id_rsa', folder=os.path.join(self.work, '.ssh')), self.make('credentials', folder=os.path.join(self.work, '.aws')),
            self.make('.env'), self.make('.env.production'), self.make('kunci.pem'), self.make('wallet.kdbx'),
            self.make('.amagi_cli_config.json'), self.make('.amagi_memory.md'), self.make('x.json', folder=os.path.join(self.work, '.amagi_sessions')),
            self.make('app.py', folder=os.path.join(self.work, '.amagi-cli')), self.make('config', folder=os.path.join(self.work, '.kube')),
        ]
        for path in blocked:
            result, confirm = self.send(path)
            self.assertIn('tidak boleh dikirim', result, path)
            confirm.assert_not_called()                                           # refused before even asking
        self.assertEqual(self.fake.uploads, [])
        self.assertFalse(app.is_sensitive_path(self.make('laporan.docx')))
        self.assertFalse(app.is_sensitive_path(os.path.join(self.inbox_dir, 'file-dari-hp.txt')))     # what the phone sent may go back
        self.assertTrue(app.is_sensitive_path(self.make('nested.txt', folder=os.path.join(self.work, 'a', '.ssh', 'b'))))

    def test_symlinks_cannot_smuggle_a_secret_out(self):
        if os.name != 'posix':
            self.skipTest('symlinks')
        secret = self.make('.env', b'TOKEN=rahasia')
        link = os.path.join(self.work, 'catatan-biasa.txt')
        os.symlink(secret, link)
        result, confirm = self.send(link)
        self.assertIn('tidak boleh dikirim', result)
        self.assertEqual(self.fake.uploads, [])

    def test_bad_inputs(self):
        self.assertIn('tidak ditemukan', self.send(os.path.join(self.work, 'tidak-ada.txt'))[0])
        self.assertIn("isi 'filepath'", self.send('')[0])
        self.assertIn('kosong', self.send(self.make('kosong.txt', b''))[0])
        with patch.object(app, 'TELEGRAM_UPLOAD_LIMIT', 5):
            self.assertIn('terlalu besar', self.send(self.make('enam-byte.txt', b'123456'))[0])
        folder = os.path.join(self.work, 'sebuah-folder')
        os.makedirs(folder)
        self.assertIn('tidak ditemukan', self.send(folder)[0])

    def test_telegram_errors_and_an_inactive_bridge_are_reported_plainly(self):
        self.fake.send_fails = True
        result, _ = self.send(self.make('a.txt'))
        self.assertIn('gagal mengirim ke Telegram', result)
        self.assertNotIn(self.config['telegram_token'], result)
        self.assertIn('belum aktif', app.send_file_to_telegram(None, 'a.txt'))
        self.bridge.pairing_only = True
        self.assertIn('belum aktif', app.send_file_to_telegram(self.bridge, 'a.txt'))
        self.bridge.pairing_only = False
        self.bridge.stop()
        self.assertIn('belum aktif', app.send_file_to_telegram(self.bridge, 'a.txt'))

    def test_on_a_remote_turn_the_phone_gets_the_buttons_and_the_file_waits(self):
        path = self.make('hasil.xlsx', b'PK-data')
        self.bridge.begin_turn()
        self.addCleanup(self.bridge.end_turn)
        outcome = []
        thread = threading.Thread(target=lambda: outcome.append(app.send_file_to_telegram(self.bridge, path, 'Hasil')))
        thread.start()
        self.assertTrue(self.fake.wait_for(lambda: self.fake.keyboards(), 8))
        question = [t for t in self.fake.sent(555) if 'Izin diperlukan' in t][0]
        self.assertIn('Kirim File', question)
        self.assertIn('hasil.xlsx', question)
        self.assertEqual(self.fake.uploads, [])                                  # nothing leaves before the tap
        self.fake.press(self.fake.keyboards()[0][0]['callback_data'])
        thread.join(8)
        self.assertTrue(outcome[0].startswith('✅'))
        self.assertEqual(self.fake.uploads[0]['filename'], 'hasil.xlsx')

    def test_the_session_loop_and_prompt_know_send_file(self):
        source = Path(app.__file__).read_text(encoding='utf-8')
        self.assertIn('func_name == "send_file"', source)
        with patch.object(app, 'read_memory', return_value=''):
            prompt = app.get_current_system_prompt()
        for needle in ('send_file', 'SELALU minta izin', '~/.amagi_inbox'):
            self.assertIn(needle, prompt)
        self.assertEqual(styling.tool_call_parts('send_file', {'filepath': 'a.docx'}), ('Kirim ke Telegram', 'a.docx'))


if __name__ == '__main__':
    unittest.main()
