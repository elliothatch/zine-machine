import math
import os
import pathlib
import sys
import textwrap
from typing import List
from datetime import date

from .markup import Parser, MarkupImage, MarkupText, StrToken, MarkupGroup

YELLOW = '\033[93m'
ENDC = '\033[0m'


class Zine(object):
    defaultStyles = {
        'align': 'left',
        'width': 1,
        'height': 1,
        'font': 'a',
        'bold': True,
        'underline': 0,
        'invert': False,
        'flip': False
    }

    defaultTextwrapOptions = {
        'width': 48,
        'expand_tabs': True,
        'tabsize': 4
    }

    def __init__(self, path, category, metadata):
        if not isinstance(path, str):
            raise TypeError("expected path to have type 'str' but got '{}'".format(type(path)))
        if not isinstance(category, str):
            raise TypeError("expected category to have type 'str' but got '{}'".format(type(category)))
        if not isinstance(metadata, dict):
            raise TypeError("expected metadata to have type 'dict' but got '{}'".format(type(metadata)))

        self.maxFileSizeKb = 1024
        self.imageOptions = {
            'fragmentHeight': 960,
            'center': True
        }

        self.path = path
        self.category = category
        self.metadata = metadata
        self.textwrapOptions = Zine.defaultTextwrapOptions

        self.markup = None

    @staticmethod
    def extractMetadata(path):
        metadata = {}
        with open(path, encoding="utf-8") as f:
            inHeader = False
            for line in f:
                if line.strip() == "":
                    continue

                if not inHeader:
                    if line.strip() == '-----':
                        inHeader = True
                        continue
                    else:
                        break

                splitIndex = line.find(':')
                if line.strip() == '-----' or splitIndex == -1:
                    break

                key = "".join(line[:splitIndex].lower().split())
                value = line[splitIndex + 1:].strip()

                if key in metadata:
                    print("{}Warning (Zine.extratMetadata): '{}' contains duplicate metadata field '{}'. overwriting '{}' with '{}' {}".format(YELLOW, path, key, metadata[key], value, ENDC), file=sys.stderr)

                metadata[key] = value

        return metadata

    @staticmethod
    def wrapMarkup(markup, wrappedText: List[str], wrappedTextPos=None):
        if wrappedTextPos is None:
            wrappedTextPos = [0, 0]

        if isinstance(markup, MarkupGroup):
            for child in markup.children:
                Zine.wrapMarkup(child, wrappedText, wrappedTextPos)
        if isinstance(markup, MarkupText):
            for subtext in markup.text:
                Zine.wrapMarkup(subtext, wrappedText, wrappedTextPos)
        elif isinstance(markup, MarkupImage):
            Zine.wrapMarkup(markup.caption, wrappedText, wrappedTextPos)
        elif isinstance(markup, StrToken):
            Zine.wrapStrToken(markup, wrappedText, wrappedTextPos)

        return markup

    @staticmethod
    def wrapStrToken(strToken, wrappedText, wrappedTextPos):
        """ Inserts newlines into the StrToken where each wrappedText element ends
            Also strips whitespace at the end or beginning of a line
            NOTE: leading/trailing newlines are stripped as well. These newlines will be automatically re-inserted into the markup because they are included in wrappedText as empty list elements (before wrapMarkup was called)
        """
        # list of substring ranges in the original StrToken that will be replaced in the output: (start, end, char)
        # a range is used so we can strip whitespace when necessary
        # the substitution character will always be either '\n' or '' (at the end of a line, or the beginning, respectively)
        substitutionRanges = []

        # advance through the StrToken by matching lines from wrappedText
        strTokenIndex = 0
        while strTokenIndex < len(strToken.text) and wrappedTextPos[0] < len(wrappedText):
            remainingText = strToken.text[strTokenIndex:]
            remainingLine = wrappedText[wrappedTextPos[0]][wrappedTextPos[1]:]

            textLeadingWhitespaceLength = len(remainingText) - len(remainingText.lstrip())
            lineLeadingWhitespaceLength = len(remainingLine) - len(remainingLine.lstrip())
            extraWhitespaceLength = textLeadingWhitespaceLength - lineLeadingWhitespaceLength

            if extraWhitespaceLength > 0:
                # the strToken starts with whitespace not found in the wrappedText, we need to remove it because we are at the beginning or end of a line
                substitutionRanges.append((strTokenIndex, strTokenIndex + extraWhitespaceLength, ''))
                strTokenIndex += extraWhitespaceLength
                continue

            if len(remainingLine) < len(remainingText):
                if not remainingText.startswith(remainingLine):
                    raise Exception(f"linewrap error at index {strTokenIndex} ({wrappedTextPos[0]}, {wrappedTextPos[1]}): StrToken does not match wrappedText: got '{remainingText}' but was expecting '{remainingLine}'")

                # the wrapped line is shorter than the remaining strToken, add a linebreak
                strTokenIndex += len(remainingLine)
                substitutionRanges.append((strTokenIndex, strTokenIndex, '\n'))

                wrappedTextPos[0] += 1
                wrappedTextPos[1] = 0
            else:
                if not remainingLine.startswith(remainingText):
                    raise Exception(f"linewrap error ({wrappedTextPos[0]}, {wrappedTextPos[1]}): StrToken does not match wrappedText: got '{remainingText}' but was expecting '{remainingLine}'")

                # this will always advance the index past the end of the string, ending the loop
                strTokenIndex += len(remainingText)

                # advance the wrappedTextPos without modifying strToken
                wrappedTextPos[1] += len(remainingText)

        # found all substitutions
        # build the output string
        lastIndex = 0
        output = ''
        for (start, end, c) in substitutionRanges:
            output += strToken.text[lastIndex:start] + c
            lastIndex = end

        output += strToken.text[lastIndex:]

        strToken.text = output
        return strToken

    def printZine(self, printer):
        if self.markup == None:
            print("Loading zine '{}'...".format(self.path))
            [markup, text] = self.loadMarkup()
            if self.textwrapOptions is not None:
                print("Text wrapping...")
                # break up the file into a list of seperate lines and feed each line into the textwrapper individually
                lines = "".join(text).splitlines()
                wrapped = []
                for line in lines:
                    sublines = textwrap.wrap(line, **self.textwrapOptions)
                    if len(sublines) == 0:
                        # if textwrap returned an empty array, it was given an empty line that we want to preserve in the output
                        wrapped.append('')
                        continue
                    for s in sublines:
                        wrapped.append(s)

                Zine.wrapMarkup(markup, wrapped)

        print("Printing...")
        printer.set(**Zine.defaultStyles)
        self.printMarkup(self.markup, printer, baseStyles=Zine.defaultStyles)
        printer.text('\n\n')

    def loadMarkup(self):
        """Read the zine from disk (skipping header) and parse it as markup, along with a plaintext version that has been textwrapped using self.textwrapOptions
        """
        parser = Parser()
        text = ''
        with open(self.path, encoding="utf-8") as f:
            # skip the header and find the text
            foundHeader = False
            foundText = False
            for line in f:
                if foundText is False:
                    # search for header
                    if line.strip() == "":
                        continue

                    if foundHeader is False:
                        if line.strip() == '-----':
                            foundHeader = True
                            continue
                        else:
                            # there is no header, consider the entire file text
                            foundText = True
                    else:
                        # we are in the header
                        if line.strip() == '-----':
                            # found the end of the header
                            foundText = True
                            continue
                        else:
                            splitIndex = line.find(':')
                            if splitIndex > -1:
                                # skip metadata
                                continue
                            else:
                                # the header ended abruptly
                                foundText = True

                # found the beginning of the text
                text = line + f.read(self.maxFileSizeKb * 1000)

                if f.read(1) != '':
                    print(f"Warning: exceeded max file size. only processing the first {self.maxFileSizeKb}Kb/{math.floor(os.fstat(f.fileno()).st_size/1000)}Kb of zine '{self.path}'",
                          file=sys.stderr)
                break

        parser.feed(text)
        self.markup = MarkupGroup(parser.stack)
        self.text = parser.text
        return [self.markup, parser.text]

    def printMarkup(self, markup, printer, baseStyles=dict()):
        if isinstance(markup, MarkupGroup):
            for child in markup.children:
                self.printMarkup(child, printer, baseStyles=baseStyles)
        if isinstance(markup, MarkupText):
            styles = baseStyles | markup.styles
            # if styles != baseStyles:
                # printer.set(**styles)
            printer.set(**styles)
            # TODO: remember the previous style and don't set unless necessary
            for subtext in markup.text:
                self.printMarkup(subtext, printer, baseStyles=styles)
        elif isinstance(markup, MarkupImage):
            printer.image(os.path.join(self.path, markup.src), **self.imageOptions)
            self.printMarkup(markup.caption, printer, baseStyles=baseStyles)
        elif isinstance(markup, StrToken):
            printer.text(markup.text)

    def printHeader(self, printer, width=48, border={
            'top':         "╔═╦══════════════════════════════════════════╦═╗",
            'top-left':    "╠═╝ ",                        'top-right': " ╚═╣",
            'left':        "║ ",                                'right': " ║",
            'bottom-left': "╠═╗ ",                     'bottom-right': " ╔═╣",
            'bottom':      "╚═╩══════════════════════════════════════════╩═╝"
    }):
        topWidth = width - (len(border['top-left']) + len(border['top-right']))
        innerWidth = width - (len(border['left']) + len(border['right']))
        bottomWidth = width - (len(border['bottom-left']) + len(border['bottom-right']))

        title = [line.center(topWidth if i == 0 else innerWidth) for i, line in enumerate(textwrap.wrap(self.metadata.get('title') or '', width=topWidth))]

        # description = textWrapper.wrap(zine.metadata.get('"description') or '')
        datepublished = date.fromisoformat(self.metadata['datepublished']) if 'datepublished' in self.metadata else None
        author = self.metadata.get('author')

        byline = [line.center(innerWidth) for line in textwrap.wrap(", ".join(([author] if author else [])
                                                                    + ([str(datepublished.year)] if datepublished else [])), width=innerWidth)]
        # todo: wrap category
        category = self.category.center(bottomWidth)

        printer.text(border['top'])
        printer.text('\n')

        for i, line in enumerate(title):
            if i == 0:
                printer.text(border['top-left'])
                printer.text(line)
                printer.text(border['top-right'])
                printer.text('\n')
            else:
                printer.text(border['left'])
                printer.text(line)
                printer.text(border['right'])
                printer.text('\n')

        for line in byline:
            printer.text(border['left'])
            printer.text(line)
            printer.text(border['right'])
            printer.text('\n')

        printer.text(border['bottom-left'])
        printer.text(category)
        printer.text(border['bottom-right'])
        printer.text('\n')
        printer.text(border['bottom'])
        printer.text('\n')

    def printFooter(self, printer):
        printer.set(double_width=True, double_height=True)
        printer.text("╔╤")
        printer.set(underline=2, double_width=True, double_height=True)
        printer.text("▓▓")
        printer.set(double_width=True, double_height=True)
        printer.text("╤╗\n╠╧══╧╣\n╚════╝\n")

def createZineIndex(path='zines'):
    zineIndex = dict()
    for root, dirs, files in os.walk(path):
        if root != path:
            p = pathlib.PurePath(root)
            baseCategory = p.parts[1]
            if baseCategory not in zineIndex:
                zineIndex[baseCategory] = {}

            fullCategory = "/".join(p.parts[1:])

            for f in files:
                zineExts = ['.zine', '.txt']
                if os.path.splitext(f)[1] not in zineExts:
                    continue

                p = os.path.join(root, f)
                zineIndex[baseCategory][p] = Zine(p, fullCategory, Zine.extractMetadata(p))
