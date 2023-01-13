from unittest import TestCase, skip

from zinemachine.markup import Parser, MarkupText, MarkupImage


class TestParser(TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_text(self):
        self.parser.feed('hello')
        expected = [
            MarkupText('hello')
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline(self):
        self.parser.feed('<u>hello</u>')
        expected = [
            MarkupText('hello', {'underline': 1})
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline(self):
        self.parser.feed('hello <u>world</u>')
        expected = [
            MarkupText('hello '),
            MarkupText('world', {'underline': 1})
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline_text(self):
        self.parser.feed('<u>hello</u> world')
        expected = [
            MarkupText('hello', {'underline': 1}),
            MarkupText(' world')
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline_text(self):
        self.parser.feed('hello <u>world</u> goodbye')
        expected = [
            MarkupText('hello '),
            MarkupText('world', {'underline': 1}),
            MarkupText(' goodbye')
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image(self):
        self.parser.feed('<img src="pic.png"></img>')
        expected = [
            MarkupImage('pic.png')
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption(self):
        self.parser.feed('<img src="pic.png">hello</img>')
        expected = [
            MarkupImage('pic.png', MarkupText('hello', {'align': 'center'}))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline(self):
        self.parser.feed('<img src="pic.png"><u>hello</u></img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText(
                            MarkupText('hello', {'underline': 1}),
                            {'align': 'center'}))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline2(self):
        self.parser.feed('<img src="pic.png"><u>hello</u> world</img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText([
                                   MarkupText('hello', {'underline': 1}),
                                   MarkupText(' world')],
                                   {'align': 'center'}))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline3(self):
        self.parser.feed('<img src="pic.png">a <u>b</u> c <u>d</u></img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText([
                                   MarkupText('a '),
                                   MarkupText('b', {'underline': 1}),
                                   MarkupText(' c '),
                                   MarkupText('d', {'underline': 1})],
                                   {'align': 'center'}))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_unknown_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<unknown></unknown>')

    @skip('fails')
    def test_hanging_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<u>')

    def test_no_opening_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('</u>')

    @skip('fails')
    def test_invalid_tag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<u</u>')
