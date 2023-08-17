""" zinemachine.markup
Zine Markup parser and AST

TODO: unexpected behavior after parser.close() with malformed markup
    add sensible fallbacks for malformed markup in general
"""

from typing import Union, Optional, List
from html.parser import HTMLParser

Position = tuple[int, int]

class MarkupError(Exception):
    def __init__(self, message: str, pos: Optional[Position]=None):
        super().__init__()
        self.message = message
        self.pos = pos


class UnknownTagError(MarkupError):
    def __init__(self, tag, pos: Optional[Position]=None):
        super().__init__(f"Unknown Tag '{tag}'", pos=pos)
        self.tag = tag

class InvalidAttributeError(MarkupError):
    def __init__(self, message: str, tag: str, attribute: str, pos: Optional[Position]=None):
        super().__init__(message, pos=pos)
        self.tag = tag
        self.attribute = attribute

class InvalidTagError(MarkupError):
    def __init__(self, message: str, tag: str, pos: Optional[Position]=None):
        super().__init__(message, pos=pos)
        self.tag = tag

class MissingOpeningTagError(MarkupError):
    def __init__(self, tag: str, pos: Optional[Position]=None):
        super().__init__(f"Missing opening tag '<{tag}>'", pos=pos)
        self.tag = tag

class MissingClosingTagError(MarkupError):
    def __init__(self, tag: str, pos: Optional[Position]=None):
        super().__init__(f"Missing closing tag '</{tag}>'", pos=pos)
        self.tag = tag

class MismatchedTagError(MarkupError):
    def __init__(self, openingTag: str, closingTag: str, pos: Optional[Position]=None):
        super().__init__(f"Closing tag '</{closingTag}>' does not match opening tag '<{openingTag}>'", pos=pos)
        self.openingTag = openingTag
        self.closingTag = closingTag


class StartTag:
    """Zine Markup AST Node - start tag (e.g. <img src="pic.png">)"""
    tag: str
    attrs: dict
    pos: Optional[Position]

    def __init__(self, tag: str, attrs=dict(), pos: Optional[Position]=None):
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

    def __init__(self, text: str, pos: Optional[Position]=None):
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
    TODO: wrong types: markup text actually can contain list[AstNode]. we might want to prevent certain nodes from being nested in a MarkupText node, and force them to be seperated under a parent MarkupGroup instead
    """

    text: List[Union[StrToken, 'MarkupText']]
    styles: dict
    pos: Optional[Position]

    def __init__(self, text: Union[StrToken, 'MarkupText', List[Union[StrToken, 'MarkupText']]], styles=dict(), pos: Optional[Position]=None):
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
    """Zine Markup AST Node - image with optional caption"""
    src: str
    caption: Optional[MarkupText]
    pos: Optional[Position]

    def __init__(self, src: str, caption: Optional[MarkupText]=None, pos: Optional[Position]=None):
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
    pos: Optional[Position]

    def __init__(self, children: List[AstNode], pos: Optional[Position]=None):
        self.children = children
        self.pos = pos

    def __eq__(self, other):
        if not isinstance(other, MarkupGroup):
            return NotImplemented

        return self.children == other.children

    def __repr__(self):
        return f'MarkupGroup(children={self.children}, pos={self.pos})'


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
    errors: List[MarkupError]

    def __init__(self):
        super().__init__()
        self.stack = []
        self.text = ''
        self.errors = []

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
                self.errors.append(MismatchedTagError(startTag.tag, tag, self.getpos()))

            # found the opening tag
            subexpressions = self.stack[i+1:]
            self.stack = self.stack[:i]

            # normal formatting tags
            textFormattingTags = ['u', 'u2', 'b', 'h1', 'invert', 'flip']
            if tag in textFormattingTags:
                tagStyles = \
                    {'underline': 1} if tag == 'u' else \
                    {'underline': 2} if tag == 'u2' else \
                    {'bold': True} if tag == 'b' else \
                    {'double_width': True, 'double_height': True, 'align': 'center'} if tag == 'h1' else \
                    {'invert': True} if tag == 'invert' else \
                    {'flip': True} if tag == 'flip' else \
                    {}

                if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                        (len(subexpressions[0].styles) == 0 or subexpressions[0].styles == tagStyles):
                    # if there is only one subexpression and it is a MarkupText with identical or no attributes, use its text instead of nesting the entire object
                    subexpressions = subexpressions[0].text
                self.stack.append(MarkupText(subexpressions, tagStyles, pos=startTag.pos))
                return
            elif tag == 'img':
                if 'src' not in startTag.attrs:
                    self.errors.append(InvalidAttributeError("'<img>' tag missing required attribute 'src'", 'img', 'src', pos=self.getpos()))
                    return

                captionStyles = {'align': 'center'}

                if len(subexpressions) == 0:
                    self.stack.append(MarkupImage(startTag.attrs['src'], None, pos=startTag.pos))
                    return

                # check if subexpressions are valid nodes (MarkupText)
                for subexpr in subexpressions:
                    if not isinstance(subexpr, MarkupText):
                        self.errors.append(InvalidTagError(f"'{type(subexpr).__name__}' node is not allowed in an 'img' tag", 'img', pos=self.getpos()))
                        return

                captionPos = subexpressions[0].pos if len(subexpressions) > 0 else startTag.pos

                if len(subexpressions) == 1 and isinstance(subexpressions[0], MarkupText) and \
                        (len(subexpressions[0].styles) == 0 or subexpressions[0].styles == captionStyles):
                    # if there is only one subexpression and it is a MarkupText with identical? or no attributes, use it's text instead of nesting the entire object
                    subexpressions = subexpressions[0].text

                caption = MarkupText(subexpressions, captionStyles, pos=captionPos)
                self.stack.append(MarkupImage(startTag.attrs['src'], caption, pos=startTag.pos))
                return
            else:
                self.errors.append(UnknownTagError(tag, pos=self.getpos()))
                return

        self.errors.append(MissingOpeningTagError(tag, pos=self.getpos()))
