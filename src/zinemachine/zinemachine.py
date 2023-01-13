import os
import pathlib
import string
import time
import random
import sys
from datetime import date
import textwrap
from escpos.printer import Serial
from serial.serialutil import SerialException
import RPi.GPIO as GPIO

from .button import Button

YELLOW = '\033[93m'
ENDC = '\033[0m'


def printZineMachineLogo(p):
    # p.set(underline=2, double_width=True, double_height=True)
    # p.text("╔╤▓▓╤╗\n")
    # p.set(double_width=True, double_height=True)
    # p.text("╠╧══╧╣\n╚════╝")

    p.set(double_width=True, double_height=True)
    p.text("╔╤")
    p.set(underline=2, double_width=True, double_height=True)
    p.text("▓▓")
    p.set(double_width=True, double_height=True)
    p.text("╤╗\n╠╧══╧╣\n╚════╝\n")


class Zine(object):
    def __init__(self, path, category, metadata):
        if not isinstance(path, str):
            raise TypeError("expected path to have type 'str' but got '{}'".format(type(path)))
        if not isinstance(category, str):
            raise TypeError("expected category to have type 'str' but got '{}'".format(type(category)))
        if not isinstance(metadata, dict):
            raise TypeError("expected metadata to have type 'dict' but got '{}'".format(type(metadata)))

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


def tryConnectBt(p, retries, timeout):
    """
    tries to check if the printer is online.
    the printer is considered offline if it is not ready to print or there is no paper.

    this relies on the serial connection already being established. if we can't connect to the printer at all the library throws an exception. then we should crash and let systemd restart the process.

    trying to recreate the serial connection in code is really slow because the library already handles trying to resend the data, so we don't bother

    retries - number of times to retry connection
    timeout - seconds to wait between retries
    @returns True on success, False after all retries fail
    """
    for i in range(retries + 1):
        # printerStatus = p.query_status(constants.RT_STATUS_ONLINE)
        # if(len(printerStatus) > 0):
        # and printerStatus[0] == 18

        if(p.is_online()):
            return True

        print("Printer offline. Retrying in {}s... ({}/{})".format(timeout, i, retries))
        sys.stdout.flush()
        time.sleep(timeout)

    return False


class ZineMachine(object):
    """
        categories - {categoryName: {filePath: Zine}}
        buttons - {categoryName: Button}
        randomZines - {categoryName: {index: number, zines: Zine[]}} zines in a category are added to this list and shuffled. the next random zine selected is at the given index, which is incremented after selection
    """

    def __init__(self, profile, chordDelay=200/1000):
        self.categories = dict()
        self.profile = profile
        self.buttons = dict()
        self.chordDelay = chordDelay
        # self.chordTimer = Timer(chordTime, self.

        self.randomZines = dict()

        self.dryRun = False
        self.echoStdOut = False

        GPIO.setmode(GPIO.BCM)

    def bindButton(self, category, pin):
        def onPressed(button):
            print("'{}' button pressed (pin {})".format(button.name, button.pin))
            self.printRandomZineFromCategory(button.name, dryRun=self.dryRun, echoStdOut=self.echoStdOut)

        self.buttons[category] = Button(
            pin,
            name=category,
            onPressed=onPressed
            # onPressed=lambda button: print("{} pressed".format(b.name)),
            # onReleased=lambda button: print("{} released".format(b.name))
        )

        print("Bound button on pin {} to category '{}'".format(pin, category))

    # def addButtonChord(self, buttons):
        """
        bind a callback function to the pressing/releasing of a chord of buttons
        the buttons used must have been previously bound to a zine category with bindButton

        when a button is pressed, start self.chordTimer for self.chordDelay. if the timer is already running, reset it and start over.
        when the timer expires, an action is taken based on which buttons are still pressed (so accidentally tapping the wrong button is not considered, although it will extend the chord delay)

        buttons - {buttonName} - the names of the buttons
        """

    def printRandomZineFromCategory(self, category, **kwargs):
        if category not in self.randomZines:
            # initialize random list
            c = self.categories.get(category)
            if c is None or len(c) == 0:
                raise ValueError("No zines in category '{}'".format(category))

            self.randomZines[category] = {'index': 0, 'zines': list(c.values())}
            print("Shuffling {} zines in category {}".format(len(self.randomZines[category]['zines']), category))
            random.shuffle(self.randomZines[category]['zines'])

        index = self.randomZines[category]['index']
        zineCount = len(self.randomZines[category]['zines'])
        zine = self.randomZines[category]['zines'][index]
        print("Printing random zine ({}/{}) from category '{}'".format(index+1, zineCount, category))

        self.randomZines[category]['index'] = (index + 1) % zineCount

        self.printZine(zine, **kwargs)

    def initIndex(self, path='categories'):
        for root, dirs, files in os.walk(path):
            if root != path:
                p = pathlib.PurePath(root)
                baseCategory = p.parts[1]
                if baseCategory not in self.categories:
                    self.categories[baseCategory] = {}

                fullCategory = "/".join(p.parts[1:])

                for f in files:
                    zineExts = ['.zine', '.txt']
                    if os.path.splitext(f)[1] not in zineExts:
                        continue

                    p = os.path.join(root, f)
                    self.categories[baseCategory][p] = Zine(p, fullCategory, Zine.extractMetadata(p))

    def initPrinter(self):
        # 9600 Baud, 8N1, Flow Control Enabled
        self.printer = Serial(
            profile=self.profile,
            devfile='/dev/rfcomm0',
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1.00,
            dsrdtr=True)

        # wait for bluetooth connection to establish
        isOnline = False
        try:
            isOnline = tryConnectBt(self.printer, 5, 1)
        except SerialException as err:
            print("Failed to connect to printer via Serial connection: {}".format(str(err)))

        if(not isOnline):
            print("Printer offline. Exiting...")
            sys.exit(1)

        print("Printer ready")

    def printHeader(self, zine, dryRun=False, echoStdOut=False):
        print(zine.metadata)
        border = {
            'top':         "╔═╦══════════════════════════════════════════╦═╗",
            'top-left':    "╠═╝ ",                        'top-right': " ╚═╣",
            'left':        "║ ",                                'right': " ║",
            'bottom-left': "╠═╗ ",                     'bottom-right': " ╔═╣",
            'bottom':      "╚═╩══════════════════════════════════════════╩═╝"
        }

        width = 48
        topWidth = width - (len(border['top-left']) + len(border['top-right']))
        innerWidth = width - (len(border['left']) + len(border['right']))
        bottomWidth = width - (len(border['bottom-left']) + len(border['bottom-right']))

        title = [line.center(topWidth if i == 0 else innerWidth) for i, line in enumerate(textwrap.wrap(zine.metadata.get('title') or '', width=topWidth))]

        # description = textWrapper.wrap(zine.metadata.get('"description') or '')
        datepublished = date.fromisoformat(zine.metadata['datepublished']) if 'datepublished' in zine.metadata else None
        author = zine.metadata.get('author')

        byline = [line.center(innerWidth) for line in textwrap.wrap(", ".join(([author] if author else [])
                                                                    + ([str(datepublished.year)] if datepublished else [])), width=innerWidth)]
        # todo: wrap category
        category = zine.category.center(bottomWidth)

        if echoStdOut:
            print(border['top'], end='')
            print()

        if not dryRun:
            self.printer.text(border['top'])
            self.printer.text('\n')

        for i, line in enumerate(title):
            if i == 0:
                if echoStdOut:
                    print(border['top-left'], end='')
                    print(line, end='')
                    print(border['top-right'], end='')
                    print()

                if not dryRun:
                    self.printer.text(border['top-left'])
                    self.printer.text(line)
                    self.printer.text(border['top-right'])
                    self.printer.text('\n')
            else:
                if echoStdOut:
                    print(border['left'], end='')
                    print(line, end='')
                    print(border['right'], end='')
                    print()

                if not dryRun:
                    self.printer.text(border['left'])
                    self.printer.text(line)
                    self.printer.text(border['right'])
                    self.printer.text('\n')

        if echoStdOut:
            for line in byline:
                print(border['left'], end='')
                print(line, end='')
                print(border['right'], end='')
                print()

            print(border['bottom-left'], end='')
            print(category, end='')
            print(border['bottom-right'], end='')
            print()
            print(border['bottom'], end='')
            print()

        if not dryRun:
            for line in byline:
                self.printer.text(border['left'])
                self.printer.text(line)
                self.printer.text(border['right'])
                self.printer.text('\n')

            self.printer.text(border['bottom-left'])
            self.printer.text(category)
            self.printer.text(border['bottom-right'])
            self.printer.text('\n')
            self.printer.text(border['bottom'])
            self.printer.text('\n')

    def printZine(self, zine, dryRun=False, echoStdOut=False, **kwargs):
        """
        kwargs passed to TextWrapper
        """
        if not isinstance(zine, Zine):
            raise TypeError("expected zine to have type 'Zine' but got '{}'".format(type(zine)))

        kwargsDefault = {'width': 48, 'expand_tabs': True, 'tabsize': 4}

        print("Printing zine '{}'".format(zine.path))

        self.printer.set(align="left", width=1, height=1, font="a", bold=True, underline=0, invert=False, flip=False)

        with open(zine.path, encoding="utf-8") as f:
            # print header
            self.printHeader(zine, dryRun=dryRun, echoStdOut=echoStdOut)

            textWrapper = textwrap.TextWrapper(**{**kwargsDefault, **kwargs})

            # check for file header
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

                # process line of text
                wrapped = textWrapper.wrap(line)
                for l in wrapped:
                    if echoStdOut:
                        print(l)
                    if not dryRun:
                        self.printer.text(l)
                        self.printer.text("\n")
                if(len(wrapped) == 0):
                    if echoStdOut:
                        print()
                    if not dryRun:
                        self.printer.text("\n")

            self.printFooter(zine, dryRun=dryRun, echoStdOut=echoStdOut)
            self.printer.text("\n\n\n\n\n")

    def printFooter(self, zine, dryRun=False, echoStdOut=False):
        if not dryRun:
            printZineMachineLogo(self.printer)


def printCodepages(p):
    cpages = list(p.magic.encoder.codepages.keys())
    for page in cpages:
        print(page)
        # if(page == "Unknown"):
        #     continue

        p.charcode('AUTO')
        p.text("\n")
        p.text(page)
        p.text("\n")
        p.charcode(page)

        for c in range(128):
            p.magic.driver._raw(bytes([c + 128]))

        p.charcode('AUTO')
        p.text("\n")


def debugCodepagesUnicode(p):
    """ tries to print all the characters in each codepage by using the unicode codepoints that map to them, and outputs the codepage the library used """

    unknownEncodings = ["Unknown", "CP851", "CP853", "CP1098", "CP774", "CP772", "RK1048"]
    cpages = list(p.magic.encoder.codepages.keys())

    for page in cpages:
        if(page in unknownEncodings):
            continue
        p.text(page)
        p.text("\n")
        print(page)
        print(p.magic.encoding)

        for c in p.magic.encoder._get_codepage_char_list(page):
            p.text(c)
            print("{} {}".format(c, p.magic.encoding))

        p.text("\n\n")
        print("")

    p.text("\n")

    # print(encoder._get_codepage_char_map(page))
    # print("")
    # print("".join(encoder._get_codepage_char_list(page)))


# returns a set of all the printable characters in all supported codepages
def getPrintableCharacters(p):
    cpages = list(p.magic.encoder.codepages.keys())

    # start with printable ascii characters
    printableChars = set(string.printable)

    unknownEncodings = ["Unknown", "CP851", "CP853", "CP1098", "CP774", "CP772", "RK1048"]
    for page in cpages:
        if(page in unknownEncodings):
            continue
        printableChars |= set(p.magic.encoder._get_codepage_char_list(page))

    return printableChars


def printFile(p, path):
    textWrapper = textwrap.TextWrapper(width=48, expand_tabs=True, tabsize=4)
    print("Printing '{}'".format(path))
    with open(path, encoding="utf-8") as f:
        p.text("=" * 48)
        p.text("\n\n")

        for line in f:
            wrapped = textWrapper.wrap(line)
            for l in wrapped:
                print(l)
                p.text(l)
                p.text("\n")
            if(len(wrapped) == 0):
                print()
                p.text("\n")

        p.text("=" * 48)
        p.text("\n\n\n")


def resetFormatting(p):
    p.set(align="left", width=1, height=1, font="a", bold=False, underline=0, invert=False, flip=False)


def testPrint(p, text, **kwargs):
    settings = [
        {},
        {'bold': True},
        {'underline': 1},
        {'underline': 2},
        {'bold': True, 'underline': 1},
        {'bold': True, 'underline': 2},
        {'invert': True},
        # {'flip': True}
    ]

    for s in settings:
        combinedSettings = {**kwargs, **s}
        p.set(**combinedSettings)
        # p.text(combinedSettings)
        p.text("\n")
        p.text(text)
        p.text("\n")
