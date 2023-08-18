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
        'double_width': False,
        'double_height': False,
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

    defaultImageOptions = {
        'fragment_height': 960,
        'center': True
    }
    defaultQrCodeOptions = {
        'size': 5,
        'center': True
    }

    def __init__(self, path, category, maxFileSizeKb=1024):
        if not isinstance(path, str):
            raise TypeError("expected path to have type 'str' but got '{}'".format(type(path)))
        if not isinstance(category, str):
            raise TypeError("expected category to have type 'str' but got '{}'".format(type(category)))

        self.path = path
        self.category = category
        self.maxFileSizeKb = maxFileSizeKb

        self.metadata = None
        self.markup = None
        self.text = None

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
        if len(parser.errors) > 0:
            raise Exception(f"Zine: Markup parser errors in '{self.path}'", parser.errors)
        self.markup = MarkupGroup(parser.stack)
        self.text = parser.text
        return [self.markup, parser.text]

    def printZine(self, printer, baseStyles=defaultStyles, textwrapOptions=defaultTextwrapOptions, imageOptions=defaultImageOptions, qrCodeOptions=defaultQrCodeOptions,
        printHeaderFunc=None, printFooterFunc=None):

        if self.metadata is None:
            self.loadMetadata()

        if self.markup is None:
            self.initMarkup(textwrapOptions=textwrapOptions)

        if printHeaderFunc is None:
            printHeaderFunc = Zine.printHeader

        if printFooterFunc is None:
            printFooterFunc = Zine.printFooter

        printer.set(**baseStyles)
        printHeaderFunc(self.metadata, self.category, printer)
        Zine.printMarkup(self.markup, printer, path=self.path, baseStyles=baseStyles, imageOptions=imageOptions)
        printer.text('\n')
        printFooterFunc(printer, self.metadata, qrCodeOptions=qrCodeOptions)

    def clearCache(self):
        self.text = None
        self.markup = None

    @staticmethod
    def printMarkup(markup, printer, path='', baseStyles=dict(), imageOptions=defaultImageOptions):
        try:
            if isinstance(markup, MarkupGroup):
                for child in markup.children:
                    Zine.printMarkup(child, printer, path=path, baseStyles=baseStyles)
            if isinstance(markup, MarkupText):
                styles = baseStyles | markup.styles
                # if styles != baseStyles:
                    # printer.set(**styles)
                printer.set(**styles)
                # TODO: remember the previous style and don't set unless necessary
                for subtext in markup.text:
                    Zine.printMarkup(subtext, printer, path=path, baseStyles=styles)
            elif isinstance(markup, MarkupImage):
                printer.image(os.path.join(os.path.dirname(path), markup.src), **imageOptions)
                Zine.printMarkup(markup.caption, printer, path=path, baseStyles=baseStyles)
            elif isinstance(markup, StrToken):
                printer.text(markup.text)
        except Exception as error:
            print(f"Zine.printMarkup error ({markup.pos}, {path}) {str(error)}")
            printer.text(str(error) + "\n")

    @staticmethod
    def printHeader(metadata, category, printer, width=48, styles=defaultStyles, border={
            'top-left':          "╔═╦",    'top': "═",             'top-right': "╦═╗",
            'top-left-inner':    "╠═╝ ",                    'top-right-inner': " ╚═╣",
            'left':              "║ ",                                  'right': " ║",
            'bottom-left-inner': "╠═╗ ",                 'bottom-right-inner': " ╔═╣",
            'bottom-left':       "╚═╩", 'bottom': "═",          'bottom-right': "╩═╝"
    }):

        topWidth = width - (len(border['top-left']) + len(border['top-right']))
        topInnerWidth = width - (len(border['top-left-inner']) + len(border['top-right-inner']))
        innerWidth = width - (len(border['left']) + len(border['right']))
        bottomInnerWidth = width - (len(border['bottom-left-inner']) + len(border['bottom-right-inner']))
        bottomWidth = width - (len(border['bottom-left']) + len(border['bottom-right']))

        title = [line.center(topInnerWidth if i == 0 else innerWidth) for i, line in enumerate(textwrap.wrap(metadata.get('title', ''), width=topInnerWidth))]

        description = [line.center(innerWidth) for line in textwrap.wrap(metadata.get('description', ''), width=innerWidth)]
        # description = textWrapper.wrap(zine.metadata.get('"description') or '')
        datepublished = date.fromisoformat(metadata['datepublished']) if 'datepublished' in metadata else None
        author = metadata.get('author', None)

        byline = [line.center(innerWidth) for line in textwrap.wrap(", ".join(([author] if author else [])
                                                                    + ([str(datepublished.year)] if datepublished else [])), width=innerWidth)]
        # todo: wrap category
        #categoryText = (category if category is not None else '').center(bottomInnerWidth)

        # publisher = [line.center(innerWidth) for line in textwrap.wrap(metadata['publisher'] if 'publisher' in metadata else '', width=innerWidth)]
        publisher = [line.center(bottomInnerWidth) for line in textwrap.wrap(metadata['publisher'] if 'publisher' in metadata else '', width=innerWidth)]

        printer.set(**styles)
        # print empty line to ensure we are at the beginning of a newline
        printer.text('\n')
        printer.text(border['top-left'])
        printer.text(border['top'] * topWidth)
        printer.text(border['top-right'])
        printer.text('\n')

        for i, line in enumerate(title):
            if i == 0:
                printer.text(border['top-left-inner'])
                printer.text(line)
                printer.text(border['top-right-inner'])
                printer.text('\n')
            else:
                printer.text(border['left'])
                printer.text(line)
                printer.text(border['right'])
                printer.text('\n')

        for i, line in enumerate(description):
            printer.text(border['left'])
            printer.text(line)
            printer.text(border['right'])
            printer.text('\n')

        for l, line in enumerate(byline):
            if len(publisher) == 0 and l == len(byline) - 1:
                printer.text(border['bottom-left-inner'])
                printer.text(line.strip().center(bottomInnerWidth))
                printer.text(border['bottom-right-inner'])
                printer.text('\n')
            else:
                printer.text(border['left'])
                printer.text(line)
                printer.text(border['right'])
                printer.text('\n')

        for l, line in enumerate(publisher):
            if l < len(publisher) - 1:
                printer.text(border['left'])
                printer.text(line)
                printer.text(border['right'])
                printer.text('\n')
            else:
                printer.text(border['bottom-left-inner'])
                printer.text(line.strip().center(bottomInnerWidth))
                printer.text(border['bottom-right-inner'])
                printer.text('\n')

        #printer.text(border['bottom-left-inner'])
        #printer.text(categoryText)
        #printer.text(border['bottom-right-inner'])
        #printer.text('\n')
        printer.text(border['bottom-left'])
        printer.text(border['bottom'] * bottomWidth)
        printer.text(border['bottom-right'])
        printer.text('\n')

    @staticmethod
    def printFooter(printer, metadata, width=48, styles=defaultStyles, qrCodeOptions=defaultQrCodeOptions):
        printer.set(**styles)
        printer.text("═" * width)
        printer.text("\n")

        # extra metadata
        if 'url' in metadata:
            printer.qr(metadata['url'], **qrCodeOptions)
            printer.text(metadata['url'] + "\n")

        doublePadding = ((width//2) - 3) // 2
        printer.set(double_width=True, double_height=True)
        printer.text(" " * doublePadding)
        printer.text("╔╤")
        printer.set(underline=2, double_width=True, double_height=True)
        printer.text("▓▓")
        printer.set(double_width=True, double_height=True)
        printer.text("╤╗")
        printer.text("\n")

        printer.text(" " * doublePadding)
        printer.text("╠╧══╧╣")
        printer.text("\n")

        printer.text(" " * doublePadding)
        printer.text("╚════╝")
        printer.text("\n")

        printer.set(**styles)
        printer.text(" - Zine Machine\n")

        printer.text("\n\n\n")

    @staticmethod
    def wrapMarkup(markup, wrappedText: List[str], wrappedTextPos=None, textwrapOptions=defaultTextwrapOptions, styles=defaultStyles):
        if wrappedTextPos is None:
            wrappedTextPos = [0, 0]

        if isinstance(markup, MarkupGroup):
            for child in markup.children:
                Zine.wrapMarkup(child, wrappedText, wrappedTextPos, styles=styles)
        if isinstance(markup, MarkupText):
            newStyles = styles | markup.styles
            for subtext in markup.text:
                Zine.wrapMarkup(subtext, wrappedText, wrappedTextPos, styles=newStyles)
        elif isinstance(markup, MarkupImage):
            Zine.wrapMarkup(markup.caption, wrappedText, wrappedTextPos, styles=styles)
        elif isinstance(markup, StrToken):
            Zine.wrapStrToken(markup, wrappedText, wrappedTextPos, textwrapOptions=textwrapOptions, styles=styles)

        return markup

    @staticmethod
    def wrapStrToken(strToken, wrappedText, wrappedTextPos, textwrapOptions=defaultTextwrapOptions, styles=defaultStyles):
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

        # now that the line breaks are inserted, center/right align each line if necessary
        """ #THIS DOESN'T WORK because we assume output begins after a linebreak and ends with a linebreak. when this isn't the case (inline styling) the padding is calculated incorrectly
        if 'align' in styles:
            width = textwrapOptions['width']
            if 'double_width' in styles and styles['double_width'] is True:
                width = width//2
            lines = output.splitlines()
            aligned = []
            for line in lines:
                if styles['align'] == 'center':
                    aligned.append(line.center(width))
                elif styles['align'] == 'right':
                    aligned.append(line.rjust(width))
                else:
                    aligned.append(line)

            #output = "\n".join(aligned)
        """

        strToken.text = output
        return strToken


    def loadMetadata(self, reload=False):
        if reload:
            self.metadata = None

        if self.metadata is not None:
            return self.metadata

        self.metadata = {}

        with open(self.path, encoding="utf-8") as f:
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

                if key in self.metadata:
                    print("{}Warning (Zine.extractMetadata): '{}' contains duplicate metadata field '{}'. overwriting '{}' with '{}' {}".format(YELLOW, self.path, key, self.metadata[key], value, ENDC), file=sys.stderr)

                self.metadata[key] = value

        if 'title' not in self.metadata:
            filename = os.path.splitext(os.path.basename(self.path))[0]
            print(f"{YELLOW}Warning (Zine.extractMetadata): '{self.path}' does not define the required metadata field 'title'. Using '{filename}'{ENDC}", file=sys.stderr)
            self.metadata['title'] = filename

        return self.metadata

    def initMarkup(self, textwrapOptions=defaultTextwrapOptions):
        """
        Load markup from disk and wrap text.
        """
        print("Loading zine '{}'...".format(self.path))
        [markup, text] = self.loadMarkup()
        if textwrapOptions is not None:
            print("Text wrapping...")
            # break up the file into a list of seperate lines and feed each line into the textwrapper individually
            lines = "".join(text).splitlines()
            wrapped = []
            for line in lines:
                sublines = textwrap.wrap(line, **textwrapOptions)
                if len(sublines) == 0:
                    # if textwrap returned an empty array, it was given an empty line that we want to preserve in the output
                    wrapped.append('')
                    continue
                for s in sublines:
                    wrapped.append(s)

            Zine.wrapMarkup(markup, wrapped, textwrapOptions=textwrapOptions)

