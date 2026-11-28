"""Gambar lewat Lyra Image 5 Flash. Layanan dipalsukan: tidak ada permintaan jaringan dan tidak memakai jatah."""
import base64
import os
import tempfile
import unittest
from unittest.mock import patch

import app

PNG = b'\x89PNG\r\n\x1a\n' + b'x' * 2048


class Reply:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        if self.body is None:
            raise ValueError('bukan json')
        return self.body


class ImageCase(unittest.TestCase):
    quota = Reply(200, {'tier': 'pro', 'limit': 3, 'used': 1, 'remaining': 2})
    result = Reply(200, {'data': [{'b64_json': base64.b64encode(PNG).decode()}], 'usage': {'daily_remaining': 1}})

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='lyra-img-')
        self.addCleanup(__import__('shutil').rmtree, self.folder, True)
        self.posts, self.asked, self.allow = [], [], True

        def post(url, **kwargs):
            self.posts.append((url, kwargs))
            return self.result

        def confirm(title, details, kind='command'):
            self.asked.append((details, kind))
            return self.allow

        for patcher in (patch.object(app.requests, 'get', lambda url, **k: self.quota),
                        patch.object(app.requests, 'post', post),
                        patch.object(app, '_confirm_permission', confirm)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def make(self, **kwargs):
        kwargs.setdefault('prompt', 'logo kopi')
        return app.generate_image({'Authorization': 'Bearer t'}, cwd=self.folder, **kwargs)

    def test_saves_the_image_and_shows_quota_before_asking(self):
        result = self.make(filepath='assets/logo.png', aspect_ratio='16:9')
        target = os.path.join(self.folder, 'assets', 'logo.png')
        with open(target, 'rb') as handle:
            self.assertEqual(handle.read(), PNG)
        self.assertIn(target, result)
        self.assertIn('Sisa jatah hari ini: 1', result)
        details, kind = self.asked[0]
        self.assertEqual(kind, 'send')                                    # tidak pernah otomatis disetujui
        self.assertIn('sisa 2 dari 3', details['Biaya'])
        url, sent = self.posts[0]
        self.assertTrue(url.endswith('/v1/images/generations'))
        self.assertEqual(sent['json'], {'model': 'lyra-image-5-flash', 'prompt': 'logo kopi', 'aspect_ratio': '16:9'})

    def test_never_overwrites_and_follows_the_real_format(self):
        with open(os.path.join(self.folder, 'a.png'), 'w') as handle:
            handle.write('lama')
        self.assertIn('a-2.png', self.make(filepath='a.jpg'))             # data PNG: ekstensi mengikuti isi
        with open(os.path.join(self.folder, 'a.png')) as handle:
            self.assertEqual(handle.read(), 'lama')

    def test_declined_permission_sends_nothing(self):
        self.allow = False
        self.assertIn('dibatalkan', self.make())
        self.assertEqual(self.posts, [])

    def test_exhausted_or_missing_quota_does_not_even_ask(self):
        for info, expected in (({'tier': 'free', 'limit': 0, 'remaining': 0}, 'belum bisa'),
                               ({'tier': 'pro', 'limit': 3, 'remaining': 0}, 'habis')):
            self.quota = Reply(200, info)
            self.assertIn(expected, self.make())
        self.assertEqual((self.asked, self.posts), ([], []))

    def test_api_key_shows_the_price_and_old_server_still_works(self):
        self.quota = Reply(200, {'price_usd': 0.07})
        self.make()
        self.assertIn('$0.07', self.asked[-1][0]['Biaya'])
        self.quota = Reply(404, None)
        self.make()
        self.assertIn('tidak bisa dicek', self.asked[-1][0]['Biaya'])

    def test_server_error_and_non_image_answers_write_no_file(self):
        self.result = Reply(403, {'error': {'message': 'Paket FREE belum bisa'}})
        self.assertIn('Paket FREE belum bisa', self.make())
        self.result = Reply(200, {'data': [{'b64_json': base64.b64encode(b'<html>').decode()}]})
        self.assertIn('tidak mengembalikan gambar', self.make())
        self.assertEqual(os.listdir(self.folder), [])

    def test_bad_input(self):
        self.assertIn('kosong', self.make(prompt='  '))
        self.assertIn('aspect_ratio', self.make(aspect_ratio='4:3'))
        self.assertEqual(self.posts, [])

    def test_command_parsing(self):
        self.assertEqual(app.image_command('/gambar --rasio 16:9 banner promo'), ('banner promo', '16:9'))
        self.assertEqual(app.image_command('/gambar logo kopi'), ('logo kopi', '1:1'))
        self.assertEqual(app.image_command('/gambar'), ('', '1:1'))


if __name__ == '__main__':
    unittest.main()
