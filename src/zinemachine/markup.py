""" zinemachine.markup
Zine Markup parser and AST

TODO: unexpected behavior after parser.close() with malformed markup
    add sensible fallbacks for malformed markup in general
"""

from typing import Union, Optional, List
from html.parser import HTMLParser

Position = tuple[int, int]


class StartTag:
    """Zine Markup AST Node - start tag (e.g. <img src="pic.png">)
    """
    tag: str
    attrs: dict
    pos: Optional[Position]

    def __init__(self, tag: str, attrs=dict(), pos: Optional[Position] = None):
        self.tag = tag
        self.attrs = attrs
        self.pos = pos

    def __eq__(self, other):
        if not isinstance(other, StartTag):
            return NotImplemented

        return self.tag == other.tag \
            and self.attrs == other.attrs \
            and self.pos == other.pos

    def __repr__(self):
        return f'StartTag(tag={self.tag}, attrs={self.attrs}, pos={self.pos})'


class StrToken:
    text: str
    pos: Optional[Position]

    def __init__(self, text: str, pos: Optional[Position] = None):
        self.text = text
        self.pos = pos

    def __repr__(self):
        return f'StrToken(text={self.text}, pos={self.pos})'

    def __eq__(self, other):
        if not isinstance(other, StrToken):
            return NotImplemented

        return self.text == other.text \
            and self.pos == other.pos


class MarkupText:
    """Zine Markup AST Node - one or more sections of formatted text. may contain nested MarkupText nodes
    """

    text: List[Union[str, StrToken, 'MarkupText']]
    styles: dict
    pos: Optional[Position]

    def __init__(self, text: Union[StrToken, 'MarkupText', List[Union[str, StrToken, 'MarkupText']]], styles=dict(), pos: Optional[Position] = None):
        if not isinstance(text, list):
            text = [text]

        #self.text = [(t if not isinstance(t, str) else StrToken(t)) for t in text]
        self.text = text
        self.styles = styles
        self.pos = pos

    def __eq__(self, other):
        if not isinstance(other, MarkupText):
            return NotImplemented

        return self.text == other.text \
            and self.styles == other.styles \
            and self.pos == other.pos

    def __repr__(self):
        return f'MarkupText(styles={self.styles}, pos={self.pos}, text={self.text})'


class MarkupImage:
    """Zine Markup AST Node - image with optional caption
    """
    src: str
    caption: Optional[MarkupText]
    pos: Optional[Position]

    def __init__(self, src: str, caption: Optional[MarkupText] = None, pos: Optional[Position] = None):
        """
        src -- path to image
        caption -- the image caption.
            default styles align="center"
        """
        self.src = src
        self.caption = caption
        self.pos = pos

    def __eq__(self, other):
        if not isinstance(other, MarkupImage):
            return NotImplemented

        return self.src == other.src \
            and self.caption == other.caption \
            and self.pos == other.pos

    def __repr__(self):
        return f'MarkupImage(src={self.src}, pos={self.pos}, caption={self.caption})'


AstNode = Union[StartTag, MarkupText, MarkupImage, 'MarkupGroup']


class MarkupGroup:
    """ Zine Markup AST Node - generic group containing zero or more children nodes
    Only used at the top level of the AST currently
    """
    children: List[AstNode]

    def __init__(self, children: List[AstNode]):
        self.children = children

    def __eq__(self, other):
        if not isinstance(other, MarkupGroup):
            return NotImplemented

        return self.children == other.children

    def __repr__(self):
        return f'MarkupGroup(children={self.children})'


class Parser(HTMLParser):
    """
    Parses zine markup into an AST for printer commands

    stack -- list of markup objects to be printed
    text -- contains the full plaintext of the zine with all markup removed

    Zine Markup tags:
        <u>Underlined</u>
        <img src="./cooking1.gif">Image Caption</img>

    Usage:
        parser = Parser()
        parser.feed('hello <b>world</b>')
        # parser.stack == [MarkupText('hello'), MarkupText('world', {'bold':True})]
    """
    stack: List[AstNode]
    text: str

    def __init__(self):
        super().__init__()
        self.stack = []
        self.text = ''

    def handle_starttag(self, tag, attrs):
        self.stack.append(StartTag(tag, dict(attrs), pos=self.getpos()))

    def handle_data(self, data):
        self.text += data
        plaintext = StrToken(data, pos=self.getpos())
        if len(self.stack) > 0:
            top = self.stack[-1]
            if isinstance(top, MarkupText) and len(top.styles) == 0:
                # if the top of the stack is a MarkupText with no styles, add the data to it instead of creating a new instance
                top.text.append(plaintext)
                return

        self.stack.append(MarkupText(plaintext, pos=self.getpos()))

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

            if tag == 'u' or tag == 'u2':
                underlineStyles = {'underline': 1}
                if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                        (len(subexpressions[0].styles) == 0 or subexpressions[0].styles == underlineStyles):
                    # if there is only one subexpression and it is a MarkupText with identical or no attributes, use its text instead of nesting the entire object
                    subexpressions = subexpressions[0].text
                self.stack.append(MarkupText(subexpressions, underlineStyles, pos=startTag.pos))
                return
            elif tag == 'img':
                if 'src' not in startTag.attrs:
                    raise Exception("markup parse error: 'img' missing attribute 'src'")

                captionStyles = {'align': 'center'}

                if len(subexpressions) == 0:
                    self.stack.append(MarkupImage(startTag.attrs['src'], None, pos=startTag.pos))
                    return

                # check if subexpressions are valid nodes (MarkupText)
                for subexpr in subexpressions:
                    if not isinstance(subexpr, MarkupText):
                        raise Exception("markup parse error: '{}' is not allowed in an 'img' tag".format(type(subexpr).__name__))

                captionPos = subexpressions[0].pos if len(subexpressions) > 0 else startTag.pos

                if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                        (len(subexpressions[0].styles) == 0 or subexpressions[0].styles == captionStyles):
                    # if there is only one subexpression and it is a MarkupText with identical? or no attributes, use it's text instead of nesting the entire object
                    subexpressions = subexpressions[0].text

                caption = MarkupText(subexpressions, captionStyles, pos=captionPos)
                self.stack.append(MarkupImage(startTag.attrs['src'], caption, pos=startTag.pos))
                return
            else:
                raise Exception("markup parse error: unknown tag '<{}>'".format(tag))

        raise Exception("markup parse error: no matching opening tag for '</{}>'".format(tag))
