""" zinemachine.markup
Zine Markup parser and AST

TODO: unexpected behavior after parser.close() with malformed markup
    add sensible fallbacks for malformed markup in general
"""

from typing import Union, Optional, List
from html.parser import HTMLParser


defaultAttrs = {
    'align': 'left',
    'width': 1,
    'height': 1,
    'font': 'a',
    'bold': True,
    'underline': 0,
    'invert': False,
    'flip': False
}


class StartTag:
    """Zine Markup AST Node - start tag (e.g. <img src="pic.png">)
    """
    tag: str
    attrs: dict

    def __init__(self, tag: str, attrs=dict()):
        self.tag = tag
        self.attrs = attrs

    def __eq__(self, other):
        if not isinstance(other, StartTag):
            return NotImplemented

        return self.tag == other.tag \
            and self.attrs == other.attrs

    def __repr__(self):
        return f'StartTag(tag={self.tag}, attrs={self.attrs})'


class MarkupText:
    """Zine Markup AST Node - one or more sections of formatted text. may contain nested MarkupText nodes
    """

    text: [Union[str, 'MarkupText']]
    attrs: dict

    def __init__(self, text: Union[str, 'MarkupText', List[Union[str, 'MarkupText']]], attrs=dict()):
        if not isinstance(text, list):
            text = [text]

        self.text = text
        self.attrs = attrs

    def __eq__(self, other):
        if not isinstance(other, MarkupText):
            return NotImplemented

        return self.text == other.text \
            and self.attrs == other.attrs

    def __repr__(self):
        return f'MarkupText(attrs={self.attrs}, text={self.text})'


class MarkupImage:
    """Zine Markup AST Node - image with optional caption
    """
    src: str
    caption: Optional[MarkupText]

    def __init__(self, src: str, caption: Optional[MarkupText] = None):
        """
        src -- path to image
        caption -- the image caption.
            default attrs align="center"
        """
        self.src = src
        self.caption = caption

    def __eq__(self, other):
        if not isinstance(other, MarkupImage):
            return NotImplemented

        return self.src == other.src \
            and self.caption == other.caption

    def __repr__(self):
        return f'MarkupImage(src={self.src}, caption={self.caption})'


class Parser(HTMLParser):
    """
    Parses zine markup into an AST for printer commands

    Supported tags:
        Underline <u>Underlined</u>
        <img src="./cooking1.gif">Image Caption</img>

    Usage:
        parser = Parser()
        parser.feed('hello <b>world</b>')
        # parser.stack == [MarkupText('hello'), MarkupText('world', {'bold':True})]
    """
    stack: [Union[StartTag, MarkupText, MarkupImage]]

    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(StartTag(tag, dict(attrs)))

    def handle_data(self, data):
        if len(self.stack) > 0:
            top = self.stack[-1]
            if isinstance(top, MarkupText) and len(top.attrs) == 0:
                # if the top of the stack is a MarkupText with no attrs, add the data to it instead of creating a new instance
                top.text.append(data)

        self.stack.append(MarkupText(data))

    def handle_endtag(self, tag):
        # walk back until we find the matching endtag
        for i in reversed(range(len(self.stack))):
            startTag = self.stack[i]
            if not isinstance(startTag, StartTag):
                continue

            if startTag.tag != tag:
                # interleaving not allowed
                raise Exception("markup parse error: starting tag '{}' does not match closing tag '{}'".format(startTag.tag, tag))

            # found the opening tag
            subexpressions = self.stack[i+1:]
            self.stack = self.stack[:i]

            match tag:
                case 'u':
                    underlineAttrs = {'underline': 1}
                    if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                            (len(subexpressions[0].attrs) == 0 or subexpressions[0].attrs == underlineAttrs):
                        # if there is only one subexpression and it is a MarkupText with identical or no attributes, use it's text instead of nesting the entire object
                        subexpressions = subexpressions[0].text
                    self.stack.append(MarkupText(subexpressions, underlineAttrs))
                    return
                case 'img':
                    if 'src' not in startTag.attrs:
                        raise Exception("markup parse error: 'img' missing attribute 'src'")

                    captionAttrs = {'align': 'center'}

                    if len(subexpressions) == 0:
                        self.stack.append(MarkupImage(startTag.attrs['src'], None))
                        return

                    # check if subexpressions are valid nodes (MarkupText)
                    for subexpr in subexpressions:
                        if not isinstance(subexpr, MarkupText):
                            raise Exception("markup parse error: '{}' is not allowed in an 'img' tag".format(type(subexpr).__name__))

                    if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                            (len(subexpressions[0].attrs) == 0 or subexpressions[0].attrs == captionAttrs):
                        # if there is only one subexpression and it is a MarkupText with identical? or no attributes, use it's text instead of nesting the entire object
                        subexpressions = subexpressions[0].text

                    caption = MarkupText(subexpressions, captionAttrs)
                    self.stack.append(MarkupImage(startTag.attrs['src'], caption))
                    return
                case _:
                    raise Exception("markup parse error: unknown tag '<{}>'".format(tag))

        raise Exception("markup parse error: no matching opening tag for '</{}>'".format(tag))
