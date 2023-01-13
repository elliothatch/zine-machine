import unittest

from zinemachine.markup import Parser, MarkupText, MarkupImage


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_text(self):
        self.parser.feed('hello')
        expected = [
            MarkupText('hello', pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline(self):
        self.parser.feed('<u>hello</u>')
        expected = [
            MarkupText('hello', {'underline': 1}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline(self):
        self.parser.feed('hello <u>world</u>')
        expected = [
            MarkupText('hello ', pos=(1, 0)),
            MarkupText('world', {'underline': 1}, pos=(1, 6))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline_text(self):
        self.parser.feed('<u>hello</u> world')
        expected = [
            MarkupText('hello', {'underline': 1}, pos=(1, 0)),
            MarkupText(' world', pos=(1, 12))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline_text(self):
        self.parser.feed('hello <u>world</u> goodbye')
        expected = [
            MarkupText('hello ', pos=(1, 0)),
            MarkupText('world', {'underline': 1}, pos=(1, 6)),
            MarkupText(' goodbye', pos=(1, 18))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image(self):
        self.parser.feed('<img src="pic.png"></img>')
        expected = [
            MarkupImage('pic.png', pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption(self):
        self.parser.feed('<img src="pic.png">hello</img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText('hello', {'align': 'center'}, pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline(self):
        self.parser.feed('<img src="pic.png"><u>hello</u></img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText(
                            MarkupText('hello', {'underline': 1}, pos=(1, 19)),
                            {'align': 'center'},
                            pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline2(self):
        self.parser.feed('<img src="pic.png"><u>hello</u> world</img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText([
                                   MarkupText('hello', {'underline': 1}, pos=(1, 19)),
                                   MarkupText(' world', pos=(1, 31))],
                                   {'align': 'center'},
                                   pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline3(self):
        self.parser.feed('<img src="pic.png">a <u>b</u> c <u>d</u></img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText([
                                   MarkupText('a ', pos=(1, 19)),
                                   MarkupText('b', {'underline': 1}, pos=(1, 21)),
                                   MarkupText(' c ', pos=(1, 29)),
                                   MarkupText('d', {'underline': 1}, pos=(1, 32))],
                                   {'align': 'center'},
                                   pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_multiline(self):
        self.parser.feed('\nhello\n\n<u>\nworld\n\n</u>\n')
        expected = [
            MarkupText('\nhello\n\n', pos=(1, 0)),
            MarkupText('\nworld\n\n', {'underline': 1}, pos=(4, 0)),
            MarkupText('\n', pos=(7, 4))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_unknown_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<unknown></unknown>')

    @unittest.skip('fails')
    def test_hanging_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<u>')

    def test_no_opening_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('</u>')

    @unittest.skip('fails')
    def test_invalid_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<u</u>')
