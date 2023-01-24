from copy import deepcopy
from tempfile import NamedTemporaryFile
import textwrap
import unittest
from unittest import mock

from escpos.printer import Serial
from zinemachine.zine import Zine
from zinemachine.markup import MarkupText, StrToken, Parser, MarkupGroup


class TestZineWrapMarkup(unittest.TestCase):
    def test_wrapMarkup_noop(self):
        text = 'hello world'
        wrapped = textwrap.wrap(text, width=12)
        markup = MarkupText(StrToken(text))

        result = Zine.wrapMarkup(deepcopy(markup), wrapped)
        self.assertEqual(markup, result)

    def test_wrapMarkup(self):
        text = 'hello world'
        wrapped = textwrap.wrap(text, width=6)
        markup = MarkupText(StrToken(text))

        result = Zine.wrapMarkup(deepcopy(markup), wrapped)

        expected = MarkupText(StrToken('hello\nworld'))
        self.assertEqual(expected, result)

    def test_wrapMarkup_whitespace(self):
        text = ' hello world '
        wrapped = textwrap.wrap(text, width=6)
        markup = MarkupText(StrToken(text))

        result = Zine.wrapMarkup(deepcopy(markup), wrapped)

        expected = MarkupText(StrToken(' hello\nworld\n '))
        self.assertEqual(expected, result)

    def test_wrapMarkup2(self):
        # self.parser.feed('hello <u>world</u> bye')
        # wrapped = textwrap.wrap(self.parser.text, width=6)
        # result = Zine.wrapMarkup(self.parser.stack, wrapped)
        # expected = MarkupText([StrToken('hello ', pos=(1, 0)),
        #                       MarkupText(StrToken('world', pos=(1, 9)), {'underline': 1}, pos=(1, 6)),
        #                       StrToken(' bye', pos=(1, 17))],
        #                       pos=(1, 0))

        # text = 'hello <u>world</u> bye'
        wrapped = textwrap.wrap('hello world bye', width=6)
        markup = MarkupText([StrToken('hello '),
                            MarkupText(StrToken('world'), {'underline': 1}),
                            StrToken(' bye')])

        result = Zine.wrapMarkup(deepcopy(markup), wrapped)

        expected = MarkupText([StrToken('hello\n'),
                              MarkupText(StrToken('world'), {'underline': 1}),
                              StrToken('\nbye')])
        self.assertEqual(expected, result)


class TestZinePrint(unittest.TestCase):
    def setUp(self):
        self.mockPrinter = mock.create_autospec(Serial)

    def tearDown(self):
        self.zineFile.close()

    def test_text(self):
        self.zineFile = NamedTemporaryFile()
        self.zineFile.writelines([b'this is a test\n',
                                  b'do not be alarmed\n',
                                  b'\n',
                                  b'thank you, goodbye\n'])
        self.zineFile.flush()

        self.zine = Zine(self.zineFile.name,
                         'test-category',
                         {
                             'title': 'test zine',
                             'description': 'for testing purposes',
                         })

        self.zine.printZine(self.mockPrinter)
        self.mockPrinter.set.assert_called_with(**Zine.defaultStyles)
        self.mockPrinter.text.assert_has_calls([mock.call('this is a test\ndo not be alarmed\n\nthank you, goodbye\n\n')])

    def test_text_underlined(self):
        self.zineFile = NamedTemporaryFile()
        self.zineFile.writelines([b'<u>this is a test\n',
                                  b'do not be alarmed</u>\n',
                                  b'\n',
                                  b'thank you, goodbye\n'])
        self.zineFile.flush()

        self.zine = Zine(self.zineFile.name,
                         'test-category',
                         {
                             'title': 'test zine',
                             'description': 'for testing purposes',
                         })

        self.zine.printZine(self.mockPrinter)
        self.mockPrinter.set.assert_has_calls([
                                              mock.call(**Zine.defaultStyles),
                                              mock.call(**(Zine.defaultStyles | {'underline': 1})),
                                              ])
        self.mockPrinter.text.assert_has_calls([
                                               mock.call('this is a test\ndo not be alarmed'),
                                               mock.call('\n\nthank you, goodbye\n\n'),
                                               ])
