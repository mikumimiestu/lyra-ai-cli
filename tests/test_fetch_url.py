"""fetch_url: reading web pages safely. Content tests use a tiny local server (private addresses allowed only through the
test switch); the safety tests mock DNS and requests, so nothing here touches the real internet."""
import contextlib
import io
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import styling
import tools

PAGE = b"""<!doctype html><html><head><title>Dokumen  Uji</title><script>bocor()</script><style>.x{}</style></head>
<body><nav><a href="/menu">Menu</a></nav><header><h1>Judul Utama</h1></header>
<main><h2>Bagian Satu</h2><p>Paragraf <b>penting</b> dengan <a href="https://contoh.id/a">tautan</a> dan <a href="https://contoh.id/b">https://contoh.id/b</a>.</p>
<ul><li>satu</li><li>dua</li></ul><pre>def f():
    return 1</pre><table><tr><td>A</td><td>B</td></tr></table>
<p>""" + b"isi panjang " * 40 + b"""</p></main><footer>hak cipta</footer></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    hits = []

    def log_message(self, *args):
        pass

    def reply(self, status, body, kind='text/html; charset=utf-8', extra=None):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Handler.hits.append((self.path, self.headers.get('User-Agent')))
        path = self.path
        if path == '/page':
            self.reply(200, PAGE)
        elif path == '/json':
            self.reply(200, b'{"nama": "Lyra", "versi": 1}', 'application/json')
        elif path == '/text':
            self.reply(200, 'Halo dunia é\n'.encode('latin-1'), 'text/plain; charset=latin-1')
        elif path == '/redirect':
            self.reply(302, b'', extra={'Location': '/page'})
        elif path == '/loop':
            self.reply(302, b'', extra={'Location': '/loop'})
        elif path == '/missing':
            self.reply(404, b'nope')
        elif path == '/error':
            self.reply(500, b'boom')
        elif path == '/image':
            self.reply(200, b'\x89PNG\r\n', 'image/png')
        elif path == '/big':
            self.reply(200, b'x' * (3 * 1024 * 1024), 'text/plain')
        elif path == '/empty':
            self.reply(200, b'<html><body><script>a()</script></body></html>')
        elif path == '/nolocation':
            self.reply(302, b'')
        else:
            self.reply(404, b'')


class LocalWebCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):      # a client that stops reading early is normal here
                pass
        cls.server = Quiet(('127.0.0.1', 0), Handler)
        cls.server.daemon_threads = True
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': '1'}))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.confirm = stack.enter_context(patch.object(tools, '_confirm_permission', return_value=True))
        tools.FETCH_ALLOWED_HOSTS.clear()
        self.addCleanup(tools.FETCH_ALLOWED_HOSTS.clear)
        Handler.hits.clear()


class ReadingTests(LocalWebCase):
    def test_html_becomes_readable_text(self):
        result = tools.fetch_url(self.base + '/page')
        self.assertIn('Dokumen Uji', result.splitlines()[0])
        self.assertIn('tidak tepercaya', result)
        self.assertIn('## Bagian Satu', result)
        self.assertIn('Paragraf penting dengan tautan (https://contoh.id/a)', result)
        self.assertIn('https://contoh.id/b', result)
        self.assertNotIn('https://contoh.id/b (https://contoh.id/b)', result)                   # an address is not repeated
        self.assertIn('- satu\n- dua', result)
        self.assertIn('def f():\n    return 1', result)
        self.assertIn('| A | B', result)
        for noise in ('bocor()', 'hak cipta', 'Menu', '.x{}'):
            self.assertNotIn(noise, result)

    def test_json_and_plain_text_use_the_declared_charset(self):
        self.assertIn('"nama": "Lyra"', tools.fetch_url(self.base + '/json'))
        self.assertIn('Halo dunia é', tools.fetch_url(self.base + '/text'))

    def test_a_missing_scheme_means_https_and_the_user_agent_is_honest(self):
        tools.fetch_url(self.base + '/page')
        self.assertTrue(all('Lyra-CLI' in agent for _path, agent in Handler.hits))
        with patch('requests.get', side_effect=__import__('requests').ConnectionError('mati')) as get, \
             patch.object(tools, 'check_public_url', return_value=('contoh.id', None)):
            result = tools.fetch_url('contoh.id/halaman')
        self.assertTrue(get.call_args[0][0].startswith('https://contoh.id/halaman'))
        self.assertIn('gagal membuka', result)

    def test_long_pages_are_truncated_with_a_hint(self):
        result = tools.fetch_url(self.base + '/page', max_chars=600)
        self.assertIn('dipotong', result.splitlines()[0])
        self.assertLess(len(result), 1400)
        self.assertIn('dipotong', tools.fetch_url(self.base + '/big', max_chars=999999).splitlines()[0])        # capped at 40,000
        self.assertIn('2 MB pertama', tools.fetch_url(self.base + '/big').splitlines()[0])

    def test_status_codes_content_types_and_empty_pages(self):
        self.assertIn('HTTP 404', tools.fetch_url(self.base + '/missing'))
        self.assertIn('HTTP 500', tools.fetch_url(self.base + '/error'))
        self.assertIn("'image/png' tidak didukung", tools.fetch_url(self.base + '/image'))
        self.assertIn('tidak berisi teks', tools.fetch_url(self.base + '/empty'))
        self.assertIn('kosong', tools.fetch_url(self.base + '/nolocation'))

    def test_redirects_are_followed_and_loops_stop(self):
        result = tools.fetch_url(self.base + '/redirect')
        self.assertIn('/page', result.splitlines()[0])
        self.assertIn('Bagian Satu', result)
        self.assertIn('terlalu banyak pengalihan', tools.fetch_url(self.base + '/loop'))

    def test_bad_arguments(self):
        self.assertIn("isi 'url'", tools.fetch_url(''))
        self.assertIn("isi 'url'", tools.fetch_url(None))
        self.assertIn('Bagian Satu', tools.fetch_url(self.base + '/page', max_chars='abc'))      # junk limit falls back to the default

    def test_it_is_not_available_in_the_read_only_print_mode(self):
        import app
        self.assertNotIn('fetch_url', app.PRINT_MODE_TOOLS)


class PermissionTests(LocalWebCase):
    def test_the_first_visit_to_each_site_is_asked_about_once(self):
        tools.fetch_url(self.base + '/page')
        tools.fetch_url(self.base + '/json')
        self.assertEqual(self.confirm.call_count, 1)
        details = self.confirm.call_args[0][1]
        self.assertEqual(details['Situs'], '127.0.0.1')
        self.assertIn('/page', details['URL'])
        self.assertEqual(self.confirm.call_args[1]['kind'], 'web')

    def test_declining_stops_before_any_request(self):
        self.confirm.return_value = False
        result = tools.fetch_url(self.base + '/page')
        self.assertIn('dibatalkan', result)
        self.assertEqual(Handler.hits, [])
        self.assertNotIn('127.0.0.1', tools.FETCH_ALLOWED_HOSTS)

    def test_a_redirect_to_another_site_is_asked_about_again(self):
        sequence = []

        def check(url):
            host = 'a.test' if 'a.test' in url else 'b.test'
            return host, None
        responses = [self._response(302, headers={'Location': 'https://b.test/x'}), self._response(200, b'<p>ok</p>')]
        with patch.object(tools, 'check_public_url', side_effect=check), patch('requests.get', side_effect=responses):
            self.confirm.side_effect = lambda title, details, kind='command': sequence.append(details['Situs']) or True
            result = tools.fetch_url('https://a.test/start')
        self.assertEqual(sequence, ['a.test', 'b.test'])
        self.assertIn('ok', result)

    def test_approval_modes_never_skip_sending_and_only_all_skips_web(self):
        approval = tools.ApprovalMode()
        for mode in ('ask', 'edits', 'all'):
            approval.set(mode)
            self.assertFalse(approval.allows('send', {}), mode)
        approval.set('edits')
        self.assertFalse(approval.allows('web', {}))
        approval.set('all')
        self.assertTrue(approval.allows('web', {}))

    @staticmethod
    def _response(status, body=b'', headers=None, kind='text/html'):
        class Response:
            def __init__(self):
                self.status_code = status
                self.headers = dict({'Content-Type': kind}, **(headers or {}))
                self.encoding = 'utf-8'

            def iter_content(self, size):
                yield body

            def close(self):
                pass
        return Response()


class SafetyTests(unittest.TestCase):
    """Without the test switch, nothing private or odd may be opened. DNS is mocked, so no real lookups happen."""

    def resolve(self, *addresses):
        return patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', (a, 0)) for a in addresses])

    def check(self, url, *addresses):
        with patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': ''}), self.resolve(*(addresses or ('93.184.216.34',))):
            return tools.check_public_url(url)

    def test_public_addresses_pass(self):
        self.assertEqual(self.check('https://contoh.test/a?b=1'), ('contoh.test', None))
        self.assertEqual(self.check('http://contoh.test:80/'), ('contoh.test', None))
        self.assertEqual(self.check('https://contoh.test:443/'), ('contoh.test', None))
        self.assertEqual(self.check('https://CONTOH.test./'), ('contoh.test', None))

    def test_private_loopback_link_local_and_cloud_metadata_are_refused(self):
        for address in ('127.0.0.1', '10.0.0.5', '192.168.1.1', '172.16.0.9', '169.254.169.254', '100.64.0.1', '0.0.0.0',
                        '::1', 'fe80::1', 'fd00::1', '::ffff:127.0.0.1', '224.0.0.1'):
            host, problem = self.check('https://contoh.test/', address)
            self.assertIsNone(host, address)
            self.assertIn('jaringan lokal', problem, address)

    def test_one_private_answer_among_public_ones_refuses_the_site(self):
        self.assertIsNotNone(self.check('https://contoh.test/', '93.184.216.34', '10.0.0.1')[1])

    def test_ip_literals_and_localhost_names_are_refused(self):
        for url in ('http://127.0.0.1/', 'http://localhost/', 'http://[::1]/', 'http://169.254.169.254/latest/meta-data'):
            with patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': ''}):
                host, problem = tools.check_public_url(url)
            self.assertIsNone(host, url)
            self.assertIsNotNone(problem)

    def test_schemes_credentials_ports_and_garbage_are_refused(self):
        for url, fragment in (('file:///etc/passwd', 'http'), ('ftp://contoh.test/', 'http'), ('gopher://contoh.test/', 'http'),
                              ('javascript:alert(1)', 'http'), ('https://user:pw@contoh.test/', 'nama pengguna'),
                              ('https://contoh.test:22/', 'Port 22'), ('http://contoh.test:8080/', 'Port 8080'),
                              ('https:///nohost', 'nama situs'), ('http://[bad', 'tidak valid')):
            host, problem = self.check(url)
            self.assertIsNone(host, url)
            self.assertIn(fragment, problem, url)

    def test_dns_failure_is_reported(self):
        with patch('socket.getaddrinfo', side_effect=OSError('x')), patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': ''}):
            self.assertIn('DNS gagal', tools.check_public_url('https://tidak-ada.test/')[1])

    def test_a_redirect_into_the_private_network_is_blocked_before_any_request_to_it(self):
        calls = []

        class First:
            status_code = 302
            headers = {'Location': 'http://169.254.169.254/latest/meta-data/'}
            encoding = 'utf-8'

            def close(self):
                pass

        def fake_get(url, **kwargs):
            calls.append(url)
            return First()

        def resolver(host, port, **kwargs):
            return [(2, 1, 6, '', ('169.254.169.254' if host == '169.254.169.254' else '93.184.216.34', 0))]
        tools.FETCH_ALLOWED_HOSTS.clear()
        with patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': ''}), patch('socket.getaddrinfo', side_effect=resolver), \
             patch('requests.get', side_effect=fake_get), patch.object(tools, '_confirm_permission', return_value=True), \
             contextlib.redirect_stdout(io.StringIO()):
            result = tools.fetch_url('https://contoh.test/')
        self.assertIn('jaringan lokal', result)
        self.assertEqual(calls, ['https://contoh.test/'])                 # the metadata address was never requested

    def test_the_default_run_cannot_open_the_local_machine_at_all(self):
        with patch.dict(os.environ, {'LYRA_ALLOW_PRIVATE_URLS': ''}), patch.object(tools, '_confirm_permission') as confirm:
            result = tools.fetch_url('http://127.0.0.1:8000/admin')
        self.assertIn('Error:', result)
        confirm.assert_not_called()                                       # refused before even asking

    def test_remote_turns_ask_on_the_phone_for_web_access(self):
        calls = []
        with patch.object(tools, 'REMOTE_APPROVER', lambda title, details, kind: calls.append((title, kind)) or False), \
             patch.object(tools, 'check_public_url', return_value=('contoh.test', None)), \
             patch('requests.get', side_effect=AssertionError('must not request')):
            tools.FETCH_ALLOWED_HOSTS.clear()
            result = tools.fetch_url('https://contoh.test/')
        self.assertIn('dibatalkan', result)
        self.assertEqual(calls, [('Konfirmasi Buka Situs', 'web')])


class ExtractionTests(unittest.TestCase):
    def test_main_content_is_preferred_and_broken_markup_survives(self):
        _title, text = tools.html_to_text('<body><div>sidebar ' + 'x ' * 5 + '</div><article>' + 'isi artikel ' * 30 + '</article></body>')
        self.assertTrue(text.startswith('isi artikel'))
        self.assertNotIn('sidebar', text)
        _t, text = tools.html_to_text('<p>tanpa penutup <b>tebal <i>miring<div>blok</p></b>')
        self.assertIn('tanpa penutup', text)
        self.assertEqual(tools.html_to_text('')[1], '')

    def test_prompt_activity_and_dispatch_know_the_tool(self):
        import app
        with patch.object(app, 'read_memory', return_value=''):
            prompt = app.get_current_system_prompt()
        for needle in ('fetch_url', 'tidak tepercaya', 'jangan ikuti instruksi'):
            self.assertIn(needle, prompt)
        self.assertEqual(styling.tool_call_parts('fetch_url', {'url': 'https://x.id'}), ('Buka web', 'https://x.id'))
        self.assertEqual(styling.activity_group('fetch_url', {}), 'Eksplorasi')
        self.assertIn('func_name == "fetch_url"', open(app.__file__, encoding='utf-8').read())


if __name__ == '__main__':
    unittest.main()
