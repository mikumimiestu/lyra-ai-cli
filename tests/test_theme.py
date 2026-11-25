import os
import unittest
from unittest.mock import patch

import app
import styling


class ThemeDetectionTests(unittest.TestCase):
    def detect(self, env, saved='', queried=None):
        with patch.dict(os.environ, env, clear=False), \
                patch.object(styling, '_saved_theme', lambda: saved), \
                patch.object(styling, '_query_terminal_background', lambda timeout=0.25: queried):
            for name in ('LYRA_THEME', 'LYRA_LIGHT_THEME', 'COLORFGBG'):
                if name not in env:
                    os.environ.pop(name, None)
            return styling._detect_dark_bg()

    def test_default_is_dark(self):
        self.assertTrue(self.detect({}))

    def test_env_overrides_everything(self):
        self.assertFalse(self.detect({'LYRA_THEME': 'light'}, saved='dark', queried=0.0))
        self.assertTrue(self.detect({'LYRA_THEME': 'dark'}, saved='light', queried=1.0))
        self.assertFalse(self.detect({'LYRA_LIGHT_THEME': '1'}))

    def test_saved_choice_beats_detection(self):
        self.assertFalse(self.detect({}, saved='light', queried=0.0))
        self.assertTrue(self.detect({}, saved='gelap', queried=1.0))

    def test_colorfgbg(self):
        self.assertFalse(self.detect({'COLORFGBG': '0;15'}))
        self.assertFalse(self.detect({'COLORFGBG': '0;default;15'}))
        self.assertTrue(self.detect({'COLORFGBG': '15;0'}))

    def test_terminal_answer_beats_colorfgbg(self):
        self.assertFalse(self.detect({}, queried=0.95))
        self.assertTrue(self.detect({}, queried=0.1))
        self.assertTrue(self.detect({'COLORFGBG': '0;15'}, queried=0.1))     # COLORFGBG bisa usang; jawaban terminal menang

    def test_reason_is_reported(self):
        with patch.dict(os.environ, {'LYRA_THEME': 'light'}):
            self.assertEqual(styling._detect_theme(), (False, 'LYRA_THEME=light'))

    def test_parse_osc11(self):
        self.assertAlmostEqual(styling._parse_osc11('\x1b]11;rgb:ffff/ffff/ffff\x1b\\'), 1.0, places=2)
        self.assertAlmostEqual(styling._parse_osc11('\x1b]11;rgb:0000/0000/0000\x07'), 0.0, places=2)
        self.assertLess(styling._parse_osc11('rgb:30/30/36'), 0.3)
        self.assertIsNone(styling._parse_osc11('bukan jawaban'))


class ThemeCommandTests(unittest.TestCase):
    def run_command(self, choice, config=None):
        config = {} if config is None else config
        saved = []
        with patch.object(app, 'save_config', lambda data: saved.append(dict(data))):
            message = app.handle_theme_command(config, choice)
        return message, config, saved

    def test_choose_light_and_back_to_auto(self):
        message, config, saved = self.run_command('terang')
        self.assertEqual(config['theme'], 'light')
        self.assertIn('/restart', message)
        message, config, saved = self.run_command('otomatis', {'theme': 'light', 'api_key': 'x'})
        self.assertNotIn('theme', config)
        self.assertEqual(config['api_key'], 'x')

    def test_no_argument_reports_current_theme(self):
        message, config, saved = self.run_command('')
        self.assertIn('Tema sekarang', message)
        self.assertEqual(saved, [])


class MarkdownNestingTests(unittest.TestCase):
    def render(self, text):
        names = {'BOLD': '<B>', 'WHITE': '', 'RESET': '</>', 'ITALIC': '<I>', 'ITALIC_OFF': '</I>'}
        with patch.multiple(styling, **names):
            return styling.format_inline_markdown(text)

    def test_italic_inside_bold_leaves_no_stray_asterisks(self):
        self.assertEqual(self.render('**tebal ⬅️ *miring***'), '<B>tebal ⬅️ <I>miring</I></>')
        self.assertEqual(self.render('**a *b* c** d'), '<B>a <I>b</I> c</> d')
        self.assertEqual(self.render('***semua***'), '<B><I>semua</I></>')

    def test_plain_stars_are_left_alone(self):
        self.assertEqual(self.render('2 * 3 dan 4*5*6'), '2 * 3 dan 4*5*6')
        self.assertEqual(self.render('*a* dan *b*'), '<I>a</I> dan <I>b</I>')


class BandContrastTests(unittest.TestCase):
    def test_band_sets_an_explicit_text_colour(self):
        self.assertIn('\x1b[38;2;', styling.BAND_FG) if styling.USE_COLOR else self.assertEqual(styling.BAND_FG, '')


if __name__ == '__main__':
    unittest.main()
