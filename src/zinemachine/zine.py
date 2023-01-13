import math
import os
import pathlib
import sys
import textwrap

from .markup import Parser, MarkupImage, MarkupText

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

    def __init__(self, path, category, metadata):
        if not isinstance(path, str):
            raise TypeError("expected path to have type 'str' but got '{}'".format(type(path)))
        if not isinstance(category, str):
            raise TypeError("expected category to have type 'str' but got '{}'".format(type(category)))
        if not isinstance(metadata, dict):
            raise TypeError("expected metadata to have type 'dict' but got '{}'".format(type(metadata)))

        self.maxFileSizeKb = 1024
        self.textwrapOptions = {
            'width': 48,
            'expand_tabs': True,
            'tabsize': 4
        }
        self.imageOptions = {
            'fragmentHeight': 960,
            'center': True
        }

        self.path = path
        self.category = category
        self.metadata = metadata

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

                # found to the beginning of the text
                text = line + f.read(self.maxFileSizeKb)

                if f.read(1) != '':
                    print(f"Warning: exceeded max file size. only processing the first {self.maxFileSizeKb}Kb/{math.floor(os.fstat(f).st_size/1000)}Kb of zine '{self.path}'",
                          file=sys.stderr)
                break

        parser.feed(text)
        wrapped = textwrap.wrap("".join(parser.text), **self.textwrapOptions)
        return [parser.stack, wrapped]

    def printMarkup(self, markup, baseStyles=dict()):
        # TODO: so now we have to keep the AST and the textwrapped text in sync?
        # I think we need to make a token for each data string and use them to match strs
        # or we approximate and try to correct for extra newlines as we encounter them
        if isinstance(markup, MarkupText):
            for subtext in markup.text:
                if isinstance(subtext, str):
                    self.printer.set(**(baseStyles | markup.styles))
                    self.printer.text(subtext)
                elif isinstance(subtext, MarkupText()):
                    self.printMarkup(subtext, baseStyles)

        elif MarkupImage():
            self.printer.image(markup.src, **self.imageOptions)
            self.printMarkup(markup.caption, baseStyles)

        print("Printing zine '{}'".format(self.path))

        self.printer.set(align="left", width=1, height=1, font="a", bold=True, underline=0, invert=False, flip=False)


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
