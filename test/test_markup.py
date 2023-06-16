import unittest

from zinemachine.markup import Parser, MarkupText, MarkupImage, StrToken


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_text(self):
        self.parser.feed('hello')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 0)), pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline(self):
        self.parser.feed('<u>hello</u>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 3)), {'underline': 1}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline2(self):
        self.parser.feed('<u2>hello</u2>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 4)), {'underline': 2}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_bold(self):
        self.parser.feed('<b>hello</b>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 3)), {'bold': True}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_h1(self):
        self.parser.feed('<h1>hello</h1>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 4)), {'double_width': True, 'double_height': True}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_invert(self):
        self.parser.feed('<invert>hello</invert>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 8)), {'invert': True}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_flip(self):
        self.parser.feed('<flip>hello</flip>')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 6)), {'flip': True}, pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline(self):
        self.parser.feed('hello <u>world</u>')
        expected = [
            MarkupText(StrToken('hello ', pos=(1, 0)), pos=(1, 0)),
            MarkupText(StrToken('world', pos=(1, 9)), {'underline': 1}, pos=(1, 6))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_underline_text(self):
        self.parser.feed('<u>hello</u> world')
        expected = [
            MarkupText(StrToken('hello', pos=(1, 3)), {'underline': 1}, pos=(1, 0)),
            MarkupText(StrToken(' world', pos=(1, 12)), pos=(1, 12))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_text_underline_text(self):
        self.parser.feed('hello <u>world</u> goodbye')
        expected = [
            MarkupText(StrToken('hello ', pos=(1, 0)), pos=(1, 0)),
            MarkupText(StrToken('world', pos=(1, 9)), {'underline': 1}, pos=(1, 6)),
            MarkupText(StrToken(' goodbye', pos=(1, 18)), pos=(1, 18))
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
                        MarkupText(StrToken('hello', pos=(1, 19)), {'align': 'center'}, pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_image_caption_underline(self):
        self.parser.feed('<img src="pic.png"><u>hello</u></img>')
        expected = [
            MarkupImage('pic.png',
                        MarkupText(
                            MarkupText(StrToken('hello', pos=(1, 22)), {'underline': 1}, pos=(1, 19)),
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
                                   MarkupText(StrToken('hello', pos=(1, 22)), {'underline': 1}, pos=(1, 19)),
                                   MarkupText(StrToken(' world', pos=(1, 31)), pos=(1, 31))],
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
                                   MarkupText(StrToken('a ', pos=(1, 19)), pos=(1, 19)),
                                   MarkupText(StrToken('b', pos=(1, 24)), {'underline': 1}, pos=(1, 21)),
                                   MarkupText(StrToken(' c ', pos=(1, 29)), pos=(1, 29)),
                                   MarkupText(StrToken('d', pos=(1, 35)), {'underline': 1}, pos=(1, 32))],
                                   {'align': 'center'},
                                   pos=(1, 19)),
                        pos=(1, 0))
        ]
        self.assertEqual(expected, self.parser.stack)

    def test_multiline(self):
        self.parser.feed('\nhello\n\n<u>\nworld\n\n</u>\n')
        expected = [
            MarkupText(StrToken('\nhello\n\n', pos=(1, 0)), pos=(1, 0)),
            MarkupText(StrToken('\nworld\n\n', pos=(4, 3)), {'underline': 1}, pos=(4, 0)),
            MarkupText(StrToken('\n', pos=(7, 4)), pos=(7, 4))
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

    def test_mismatchedTag(self):
        with self.assertRaises(Exception):
            self.parser.feed('<u>hello</b>')
