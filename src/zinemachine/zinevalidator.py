import sys
import os
from .markup import MarkupError, Parser, Position, MarkupGroup, MarkupText, MarkupImage, StrToken
from typing import List, Set, Optional

from escpos.image import EscposImage

class ZineValidationDiagnostic(object):
    """Base class for zine validation errors"""

    pos: Optional[Position]
    """(line,col) error position in source file"""

    text: str
    """the text of the line the error occured on"""

    def __init__(self, level: str, message: str, text: str, pos: Optional[Position]=None):
        self.level = level
        self.message = message
        self.pos = pos
        self.text = text

    def __str__(self):
        posStr = f"{self.pos[0]}:{self.pos[1]}: " if self.pos else ""
        colPointer = " "*(self.pos[1]-1) + "^\n" if self.pos else ""
        return f"{posStr}{self.level}: {self.message}\n{self.text}\n{colPointer}"

class ZineValidationError(ZineValidationDiagnostic):
    def __init__(self, message: str, text: str, pos: Optional[Position]=None):
        super().__init__('error', message, text, pos=pos)

class ZineValidationWarning(ZineValidationDiagnostic):
    def __init__(self, message: str, text: str, pos: Optional[Position]=None):
        super().__init__('warning', message, text, pos=pos)

class HeaderWarning(ZineValidationWarning):
    def __init__(self, message: str):
        super().__init__(message, "", (1,1))

class InvalidHeaderError(ZineValidationError):
    def __init__(self, message: str, text: str, pos: Optional[Position]=None):
        super().__init__(message, text, pos=pos)

class UnsupportedCharacterError(ZineValidationError):
    character: str
    text: str
    def __init__(self, text: str, character: str, pos: Optional[Position]=None):
        super().__init__(f"Unprintable character '{character}'", text, pos=pos)
        self.character = character

class InvalidImageError(ZineValidationError):
    def __init__(self, message: str, text: str, src: str, pos: Optional[Position]=None):
        super().__init__(message, text, pos=pos)



YELLOW = '\033[93m'
ENDC = '\033[0m'

defaultValidCharacters = {'\t', '\n', '\x0b', '\x0c', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~', '\x80', '\xa0', '¡', '¢', '£', '¤', '¥', '¦', '§', '¨', '©', 'ª', '«', '¬', '\xad', '®', '¯', '°', '±', '²', '³', '´', 'µ', '¶', '·', '¸', '¹', 'º', '»', '¼', '½', '¾', '¿', 'À', 'Á', 'Â', 'Ã', 'Ä', 'Å', 'Æ', 'Ç', 'È', 'É', 'Ê', 'Ë', 'Ì', 'Í', 'Î', 'Ï', 'Ð', 'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', '×', 'Ø', 'Ù', 'Ú', 'Û', 'Ü', 'Ý', 'Þ', 'ß', 'à', 'á', 'â', 'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é', 'ê', 'ë', 'ì', 'í', 'î', 'ï', 'ð', 'ñ', 'ò', 'ó', 'ô', 'õ', 'ö', '÷', 'ø', 'ù', 'ú', 'û', 'ü', 'ý', 'þ', 'ÿ', 'Ă', 'ă', 'Ą', 'ą', 'Ć', 'ć', 'Č', 'č', 'Ď', 'ď', 'Đ', 'đ', 'Ę', 'ę', 'Ě', 'ě', 'ı', 'Ĺ', 'ĺ', 'Ľ', 'ľ', 'Ł', 'ł', 'Ń', 'ń', 'Ň', 'ň', 'Ő', 'ő', 'Œ', 'œ', 'Ŕ', 'ŕ', 'Ř', 'ř', 'Ś', 'ś', 'Ş', 'ş', 'Š', 'š', 'Ţ', 'ţ', 'Ť', 'ť', 'Ů', 'ů', 'Ű', 'ű', 'Ÿ', 'Ź', 'ź', 'Ż', 'ż', 'Ž', 'ž', 'ƒ', 'ˆ', 'ˇ', '˘', '˙', '˛', '˜', '˝', 'Γ', 'Θ', 'Σ', 'Φ', 'Ω', 'α', 'δ', 'ε', 'π', 'σ', 'τ', 'φ', '–', '—', '‗', '‘', '’', '‚', '“', '”', '„', '†', '‡', '•', '…', '‰', '‹', '›', 'ⁿ', '₧', '€', '™', '∙', '√', '∞', '∩', '≈', '≡', '≤', '≥', '⌐', '⌠', '⌡', '─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '═', '║', '╒', '╓', '╔', '╕', '╖', '╗', '╘', '╙', '╚', '╛', '╜', '╝', '╞', '╟', '╠', '╡', '╢', '╣', '╤', '╥', '╦', '╧', '╨', '╩', '╪', '╫', '╬', '▀', '▄', '█', '▌', '▐', '░', '▒', '▓', '■', '\uf8f0', '\uf8f1', '\uf8f2', '\uf8f3', '｡', '｢', '｣', '､', '･', 'ｦ', 'ｧ', 'ｨ', 'ｩ', 'ｪ', 'ｫ', 'ｬ', 'ｭ', 'ｮ', 'ｯ', 'ｰ', 'ｱ', 'ｲ', 'ｳ', 'ｴ', 'ｵ', 'ｶ', 'ｷ', 'ｸ', 'ｹ', 'ｺ', 'ｻ', 'ｼ', 'ｽ', 'ｾ', 'ｿ', 'ﾀ', 'ﾁ', 'ﾂ', 'ﾃ', 'ﾄ', 'ﾅ', 'ﾆ', 'ﾇ', 'ﾈ', 'ﾉ', 'ﾊ', 'ﾋ', 'ﾌ', 'ﾍ', 'ﾎ', 'ﾏ', 'ﾐ', 'ﾑ', 'ﾒ', 'ﾓ', 'ﾔ', 'ﾕ', 'ﾖ', 'ﾗ', 'ﾘ', 'ﾙ', 'ﾚ', 'ﾛ', 'ﾜ', 'ﾝ', 'ﾞ', 'ﾟ'}
"""set of characters printable by the receipt printer"""

defaultPrinterWidthPixels = 576

def validateZine(path: str, validCharacters: Set[str]=defaultValidCharacters) -> List[ZineValidationDiagnostic]:
    """
    Validates a .zine file.
    A zine is considered invalid for any of the following reasons:
     - it does not contain a well formatted header
     - invalid or incomplete markup
     - contains any unprintable characters for the selected printer profile
     - image src missing
     - image too wide for selected printer profile

    Warnings are issued for the reasons:
     - Missing header
    """

    errors = []

    # print("Opening file {}".format(args.filename), file=sys.stderr)
    with open(path, encoding="utf-8") as f:
        foundHeader = False
        foundText = False
        textOffset = None
        textLineOffset = 0
        text = ""
        requiredMetadata = set(['title'])
        metadataKeys = set()
        for i, line in enumerate(iter(f.readline, '')):
        # for i, line in enumerate(f, 1):
            for j, c in enumerate(line, 1):
                if c not in validCharacters:
                    errors.append(UnsupportedCharacterError(line, c, pos=(i + 1, j + 1)))

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
                        errors.append(HeaderWarning("Header missing"))
                        foundText = True
                else:
                    # we are in the header
                    if line.strip() == '-----':
                        # found the end of the header
                        foundText = True
                        continue
                    else:
                        splitIndex = line.find(':')
                        if splitIndex == -1:
                            errors.append(InvalidHeaderError("Expected ':' in key:value pair", line, pos=(i+1, 1)))
                        else:
                            if len(line[0:splitIndex].strip()) == 0:
                                errors.append(InvalidHeaderError("Missing key in key:value pair", line, pos=(i+1, 1)))
                                continue
                            if len(line[splitIndex+1:-1].strip()) == 0:
                                errors.append(InvalidHeaderError("Missing value in key:value pair", line, pos=(i+1, splitIndex+1)))
                                continue

                            metadataKeys.add(line[0:splitIndex].lower())
                            continue
                            foundText = True

            if textOffset == None:
                # found the beginning of the text
                textOffset = f.tell()
                text = line
                textLineOffset = i

            # finish processing unsupported characters check

        missingMetadata = requiredMetadata - metadataKeys
        for m in missingMetadata:
            errors.append(HeaderWarning(f"Missing required metadata field '{m}'"))
        if textOffset != None:
            f.seek(textOffset)
            text += f.read()

        f.seek(0)
        lines = f.readlines() #TODO: read all the lines into an array on the first pass

        parser = Parser()

        parser.feed(text)
        markup = MarkupGroup(parser.stack, pos=(1,1))
        for err in parser.errors:
            filePos = (err.pos[0] + textLineOffset, err.pos[1] + 1)
            err.pos = filePos
            err.level = 'error'
            err.text = lines[filePos[0]-1]
            errors.append(err)

        errors += validateMarkup(markup, lines, path, textLineOffset)

        return errors

def validateMarkup(markup, lines, path, lineOffset) -> List[ZineValidationDiagnostic]:
    filePos = (markup.pos[0] + lineOffset, markup.pos[1] + 1)
    if isinstance(markup, MarkupGroup):
        errors = []
        for child in markup.children:
            errors += validateMarkup(child, lines, path, lineOffset)
        return errors
    if isinstance(markup, MarkupText):
        errors = []
        for subtext in markup.text:
            errors += validateMarkup(subtext, lines, path, lineOffset)
        return errors
    if isinstance(markup, MarkupImage):
        try:
            image = EscposImage(os.path.join(os.path.dirname(path), markup.src))
            if image.width > defaultPrinterWidthPixels:
                return [InvalidImageError(f"Image too wide for printer ({image.width}px, expecting <={defaultPrinterWidthPixels}px)", lines[filePos[0]-1], markup.src, filePos)]

            return []
        except Exception as err:
            return [InvalidImageError(str(err), lines[filePos[0]-1], markup.src, filePos)]

    return []
