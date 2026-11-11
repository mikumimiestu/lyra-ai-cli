import contextlib
import io
import unittest
from unittest.mock import patch

import app
import styling

NEW = {'tier': 'pro', 'used': 100000, 'limit': 300000, 'remaining': 200000, 'resets_in_seconds': 7200,
       'window_active': True, 'week_used': 500000, 'week_limit': 2700000, 'week_remaining': 2200000,
       'week_resets_in_seconds': 3 * 86400 + 3600}


class QuotaWindowTests(unittest.TestCase):
    def show(self, quota):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(app, 'uses_account_login', return_value=True), \
             patch.object(app, 'fetch_quota', return_value=quota):
            app.show_quota({})
        return styling.strip_ansi(out.getvalue())

    def test_both_windows_are_shown(self):
        page = self.show(dict(NEW))
        self.assertIn('5 jam', page)
        self.assertIn('Mingguan', page)
        self.assertIn('200,000', page)
        self.assertIn('reset dalam 2 jam', page)
        self.assertIn('3 hari 1 jam', page)

    def test_idle_window_says_it_starts_with_the_first_message(self):
        page = self.show(dict(NEW, window_active=False, resets_in_seconds=0))
        self.assertIn('dimulai saat pesan pertama', page)

    def test_old_backend_format_does_not_crash(self):
        page = self.show({'tier': 'free', 'used': 5, 'limit': 20000, 'remaining': 19995, 'resets_in_seconds': 600})
        self.assertIn('5 jam', page)
        self.assertNotIn('Mingguan', page)

    def test_footer_percent_uses_the_tighter_window(self):
        monitor = app.QuotaMonitor()
        monitor.data = dict(NEW)
        self.assertEqual(monitor.remaining_percent(), 67)                               # 5-hour: 66.7%, week: 81%
        monitor.data = dict(NEW, week_remaining=270000)
        self.assertEqual(monitor.remaining_percent(), 10)                               # weekly is the limit

    def test_duration_with_days(self):
        self.assertEqual(app.format_duration(2 * 86400 + 5 * 3600), '2 hari 5 jam')
        self.assertEqual(app.format_duration(90 * 60), '1 jam 30 menit')


if __name__ == '__main__':
    unittest.main()
