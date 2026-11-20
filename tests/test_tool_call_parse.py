import unittest

import app


class ParseToolJsonTests(unittest.TestCase):
    def test_trailing_comma_and_fence(self):
        raw = '```json\n{"name":"read_file","arguments":{"filepath":"a.py",}}\n```'
        self.assertEqual(app.parse_tool_json(raw)["arguments"], {"filepath": "a.py"})

    def test_raw_newline_in_string(self):
        data = app.parse_tool_json('{"name":"write_file","arguments":{"filepath":"a","content":"x\ny"}}')
        self.assertEqual(data["arguments"]["content"], "x\ny")

    def test_truncated_object_is_closed(self):
        data = app.parse_tool_json('{"name":"list_directory","arguments":{"path":"."')
        self.assertEqual(data["arguments"], {"path": "."})

    def test_garbage_raises_value_error(self):
        with self.assertRaises(ValueError):
            app.parse_tool_json("bukan json")

    def test_missing_closing_tag(self):
        text, call = app.extract_tool_call('halo <tool_call>{"name":"read_file"')
        self.assertEqual(text, "halo")
        self.assertEqual(call, '{"name":"read_file"')


class RawBlockTests(unittest.TestCase):
    def test_write_file_content_outside_json(self):
        body = 'print("halo \\n")\nx = {"a": 1}\n'
        reply = ('Membuat file.\n<tool_call>\n{"name":"write_file","arguments":{"filepath":"a.py"}}\n</tool_call>\n'
                 '<file_content>\n' + body + '</file_content>')
        text, call = app.extract_tool_call(reply)
        self.assertEqual(text, "Membuat file.")
        data = app.parse_tool_json(call)
        args = app.merge_raw_args(data["name"], data["arguments"], reply)
        self.assertEqual(args["content"], body)
        self.assertEqual(args["filepath"], "a.py")

    def test_edit_file_old_and_new(self):
        reply = ('<tool_call>{"name":"edit_file","arguments":{"filepath":"a.html"}}</tool_call>\n'
                 '<old_text>\n<p class="x">lama</p>\n</old_text>\n<new_text>\n<p class="x">baru</p>\n</new_text>')
        _, call = app.extract_tool_call(reply)
        data = app.parse_tool_json(call)
        args = app.merge_raw_args(data["name"], data["arguments"], reply)
        self.assertEqual(args["old"], '<p class="x">lama</p>')
        self.assertEqual(args["new"], '<p class="x">baru</p>')

    def test_unclosed_block_takes_rest(self):
        reply = '<tool_call>{"name":"write_file","arguments":{"filepath":"a"}}</tool_call>\n<file_content>\nabc'
        self.assertEqual(app.extract_raw_args(reply), {"content": "abc"})

    def test_old_json_style_still_works(self):
        reply = '<tool_call>{"name":"write_file","arguments":{"filepath":"a","content":"isi"}}</tool_call>'
        _, call = app.extract_tool_call(reply)
        data = app.parse_tool_json(call)
        args = app.merge_raw_args(data["name"], data["arguments"], reply)
        self.assertEqual(args["content"], "isi")

    def test_other_tools_untouched(self):
        args = app.merge_raw_args("read_file", {"filepath": "a"}, "<file_content>\nx\n</file_content>")
        self.assertEqual(args, {"filepath": "a"})


if __name__ == "__main__":
    unittest.main()
