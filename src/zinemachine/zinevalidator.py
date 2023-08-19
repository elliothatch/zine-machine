import sys
import os
import math
from .markup import MarkupError, Parser, Position, MarkupGroup, MarkupText, MarkupImage, StrToken
from typing import List, Set, Optional, Tuple

from escpos.image import EscposImage
from PIL import Image

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

class ZineValidationFix(ZineValidationDiagnostic):
    def __init__(self, message: str, text: str, pos: Optional[Position]=None):
        super().__init__('fix', message, text, pos=pos)

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

class ResizeImageFix(ZineValidationFix):
    def __init__(self, text: str, src: str, oldSize: Tuple[int, int], newSize: Tuple[int, int], pos: Optional[Position]=None):
        super().__init__(f"Resize image '{os.path.abspath(src)}' (orignal saved to '{os.path.abspath(src)}.orig'): {oldSize[0]}x{oldSize[1]}px -> {newSize[0]}x{newSize[1]}px", text, pos=pos)



RED = '\033[91m'
YELLOW = '\033[93m'
GREEN = "\033[0;32m"
BOLD = '\033[1m'
ENDC = '\033[0m'

class ZineValidator(object):
    defaultValidCharacters = {'\t', '\n', '\x0b', '\x0c', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~', '\x80', '\xa0', '¡', '¢', '£', '¤', '¥', '¦', '§', '¨', '©', 'ª', '«', '¬', '\xad', '®', '¯', '°', '±', '²', '³', '´', 'µ', '¶', '·', '¸', '¹', 'º', '»', '¼', '½', '¾', '¿', 'À', 'Á', 'Â', 'Ã', 'Ä', 'Å', 'Æ', 'Ç', 'È', 'É', 'Ê', 'Ë', 'Ì', 'Í', 'Î', 'Ï', 'Ð', 'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', '×', 'Ø', 'Ù', 'Ú', 'Û', 'Ü', 'Ý', 'Þ', 'ß', 'à', 'á', 'â', 'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é', 'ê', 'ë', 'ì', 'í', 'î', 'ï', 'ð', 'ñ', 'ò', 'ó', 'ô', 'õ', 'ö', '÷', 'ø', 'ù', 'ú', 'û', 'ü', 'ý', 'þ', 'ÿ', 'Ă', 'ă', 'Ą', 'ą', 'Ć', 'ć', 'Č', 'č', 'Ď', 'ď', 'Đ', 'đ', 'Ę', 'ę', 'Ě', 'ě', 'ı', 'Ĺ', 'ĺ', 'Ľ', 'ľ', 'Ł', 'ł', 'Ń', 'ń', 'Ň', 'ň', 'Ő', 'ő', 'Œ', 'œ', 'Ŕ', 'ŕ', 'Ř', 'ř', 'Ś', 'ś', 'Ş', 'ş', 'Š', 'š', 'Ţ', 'ţ', 'Ť', 'ť', 'Ů', 'ů', 'Ű', 'ű', 'Ÿ', 'Ź', 'ź', 'Ż', 'ż', 'Ž', 'ž', 'ƒ', 'ˆ', 'ˇ', '˘', '˙', '˛', '˜', '˝', 'Γ', 'Θ', 'Σ', 'Φ', 'Ω', 'α', 'δ', 'ε', 'π', 'σ', 'τ', 'φ', '–', '—', '‗', '‘', '’', '‚', '“', '”', '„', '†', '‡', '•', '…', '‰', '‹', '›', 'ⁿ', '₧', '€', '™', '∙', '√', '∞', '∩', '≈', '≡', '≤', '≥', '⌐', '⌠', '⌡', '─', '│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '═', '║', '╒', '╓', '╔', '╕', '╖', '╗', '╘', '╙', '╚', '╛', '╜', '╝', '╞', '╟', '╠', '╡', '╢', '╣', '╤', '╥', '╦', '╧', '╨', '╩', '╪', '╫', '╬', '▀', '▄', '█', '▌', '▐', '░', '▒', '▓', '■', '\uf8f0', '\uf8f1', '\uf8f2', '\uf8f3', '｡', '｢', '｣', '､', '･', 'ｦ', 'ｧ', 'ｨ', 'ｩ', 'ｪ', 'ｫ', 'ｬ', 'ｭ', 'ｮ', 'ｯ', 'ｰ', 'ｱ', 'ｲ', 'ｳ', 'ｴ', 'ｵ', 'ｶ', 'ｷ', 'ｸ', 'ｹ', 'ｺ', 'ｻ', 'ｼ', 'ｽ', 'ｾ', 'ｿ', 'ﾀ', 'ﾁ', 'ﾂ', 'ﾃ', 'ﾄ', 'ﾅ', 'ﾆ', 'ﾇ', 'ﾈ', 'ﾉ', 'ﾊ', 'ﾋ', 'ﾌ', 'ﾍ', 'ﾎ', 'ﾏ', 'ﾐ', 'ﾑ', 'ﾒ', 'ﾓ', 'ﾔ', 'ﾕ', 'ﾖ', 'ﾗ', 'ﾘ', 'ﾙ', 'ﾚ', 'ﾛ', 'ﾜ', 'ﾝ', 'ﾞ', 'ﾟ'}
    """set of characters printable by the receipt printer"""
    defaultMaxImageWidth = 576
    """maximum width the printer can print"""

    def __init__(self, validCharacters: Set[str]=defaultValidCharacters, maxImageWidth: int=defaultMaxImageWidth, resizeImages=False, resizeFilter=Image.Resampling.LANCZOS):
        self.validCharacters = validCharacters
        self.maxImageWidth = maxImageWidth
        self.resizeImages = resizeImages
        self.resizeFilter = resizeFilter

    def validateZine(self, path: str) -> List[ZineValidationDiagnostic]:
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
         - Missing title metadata
        """

        errors = []

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
                    if c not in self.validCharacters:
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

            errors += self.validateMarkup(markup, lines, path, textLineOffset)

            return errors

    def validateMarkup(self, markup, lines, path, lineOffset) -> List[ZineValidationDiagnostic]:
        filePos = (markup.pos[0] + lineOffset, markup.pos[1] + 1)
        if isinstance(markup, MarkupGroup):
            errors = []
            for child in markup.children:
                errors += self.validateMarkup(child, lines, path, lineOffset)
            return errors
        if isinstance(markup, MarkupText):
            errors = []
            for subtext in markup.text:
                errors += self.validateMarkup(subtext, lines, path, lineOffset)
            return errors
        if isinstance(markup, MarkupImage):
            try:
                imagePath = os.path.join(os.path.dirname(path), markup.src)
                image = EscposImage(imagePath)
                if image.width > self.maxImageWidth:
                    if self.resizeImages == False:
                        return [InvalidImageError(f"Image too wide for printer ({image.width}px, expecting <={self.maxImageWidth}px)", lines[filePos[0]-1], markup.src, pos=filePos)]

                    # resize
                    # copy the original file
                    image.img_original.save(imagePath + '.orig', format=image.img_original.format)
                    sizeRatio = self.maxImageWidth / image.img_original.width
                    newSize = (self.maxImageWidth, math.floor(image.img_original.height * sizeRatio))
                    resized = image.img_original.resize(newSize, resample=self.resizeFilter)
                    resized.save(imagePath)

                    return [ResizeImageFix(lines[filePos[0]-1], markup.src, image.img_original.size, newSize, pos=filePos)]

                return []
            except Exception as err:
                return [InvalidImageError(str(err), lines[filePos[0]-1], markup.src, filePos)]

        return []

    @staticmethod
    def printValidationDiagnostics(path, diagnostics):
        errors = []
        warnings = []
        fixes = []
        for e in diagnostics:
            color = ""
            if e.level == 'error':
                color = RED
                errors.append(e)
            elif e.level == 'warning':
                color = YELLOW
                warnings.append(e)
            elif e.level == 'fix':
                color = GREEN
                fixes.append(e)

            print(f"{path}:{e.pos[0]}:{e.pos[1]} {color}{e.level}{ENDC}: {BOLD}{type(e).__name__}: {e.message}{ENDC}")
            if len(e.text) > 0:
                print(f"   {e.text}", end="")
                print(f"   {' ' * (e.pos[1] - 1)}^")

        return (errors, warnings, fixes)

    def validateDirectory(self, path: str) -> Tuple[List[ZineValidationError], List[ZineValidationWarning], List[ZineValidationFix]]:
        """
        Validates all zine files in a directory or single file and outputs the results to console.
        Returns (errors, warnings)
        """
        print(f"Validating '{os.path.abspath(path)}'...")

        if os.path.isdir(path):
            invalidZines = []
            allErrors = []
            allWarnings = []
            allFixes = []
            for root, dirs, files in os.walk(path):
                # ignore hidden directories
                dirs[:] = [d for d in dirs if not d[0] == '.']
                # ignore hidden files
                files = [f for f in files if not f[0] == '.']
                for f in files:
                    zineExts = ['.zine', '.txt']
                    if os.path.splitext(f)[1] not in zineExts:
                        continue

                    path = os.path.join(root, f)
                    print(f"{path}... ", end="")
                    diagnostics = self.validateZine(path)
                    if len(diagnostics) == 0:
                        print("OK")
                        continue

                    invalidZines.append((path, diagnostics))
                    errors = []
                    warnings = []
                    fixes = []
                    for diagnostic in diagnostics:
                        if diagnostic.level == 'error':
                            errors.append(diagnostic)
                        elif diagnostic.level == 'warning':
                            warnings.append(diagnostic)
                        else:
                            fixes.append(diagnostic)

                    allErrors += errors
                    allWarnings += warnings
                    allFixes += fixes

                    if len(errors) > 0:
                        print(RED, end="")
                    elif len(warnings) > 0:
                        print(YELLOW, end="")
                    elif len(fixes) > 0:
                        print(GREEN, end="")
                    print(f"{len(errors)} errors. {len(warnings)} warnings. {len(fixes)} fixes.{ENDC}")

            for zine in invalidZines:
                ZineValidator.printValidationDiagnostics(zine[0], zine[1])

            if len(allErrors) > 0:
                print(RED, end="")
            elif len(allWarnings) > 0:
                print(YELLOW, end="")
            elif len(allFixes) > 0:
                print(GREEN, end="")
            print(f"Validation complete. {len(invalidZines)} zines failed validation. {len(allErrors)} errors. {len(allWarnings)} warnings. {len(allFixes)} fixes.{ENDC}")

            return (allErrors, allWarnings, allFixes)
        else:
            # single file
            diagnostics = self.validateZine(path)
            groupedDiagnostics = ZineValidator.printValidationDiagnostics(path, diagnostics)
            if len(groupedDiagnostics[0]) > 0:
                print(RED, end="")
            elif len(groupedDiagnostics[1]) > 0:
                print(YELLOW, end="")
            elif len(groupedDiagnostics[2]) > 0:
                print(GREEN, end="")
            print(f"Validation complete. {len(groupedDiagnostics[0])} errors. {len(groupedDiagnostics[1])} warnings. {len(groupedDiagnostics[2])} fixes.{ENDC}")

            return groupedDiagnostics
