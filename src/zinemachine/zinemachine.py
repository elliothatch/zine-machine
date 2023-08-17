import math
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
from threading import Lock

from .zine import Zine
from .markup import Parser

YELLOW = '\033[93m'
ENDC = '\033[0m'

class ZineMachine(object):
    """
        categories - {categoryName: {filePath: Zine}}
        randomZines - {categoryName: {index: number, zines: Zine[]}} zines in a category are added to this list and shuffled. the next random zine selected is at the given index, which is incremented after selection
        secondsPerCharacter: estimate for how long it takes to print a single character on the printer. used to block button presses until the print is complete.
    """

    def __init__(self, printerManager, secondsPerCharacter=0.0022, basePrintTime=2.0):
        self.printerManager = printerManager
        self.categories = dict()
        self.secondsPerCharacter = secondsPerCharacter
        self.basePrintTime = basePrintTime
        self.printing = False
        self.printLock = Lock()
        """printLock is only used to lock the the printing flag. we don't want to queue up multiple prints"""

        self.randomZines = dict()

    def printText(self, text, styles=Zine.defaultStyles):
        """print some text. queues up after the current print is complete with busy waiting"""
        while self.printing == True:
            time.sleep(0.5)

        with self.printLock:
            self.printing = True
            self.printerManager.printer.set(**styles)
            self.printerManager.printer.text(text)
            self.printerManager.printer.device.flush()
            self.printing = False

    def printZine(self, zine, ignoreLock=False):
        """ignoreLock - when true, we assert that we have already acquired the print priority and we should skip the locking check (i.e. started the print in printRandomZineFromCategory)"""
        try:
            if ignoreLock is False:
                with self.printLock:
                    if self.printing is True:
                        print(f"{YELLOW}Printing already in progress. Ignoring request to print '{zine.path}'{ENDC}")
                        return

                    self.printing = True

            # estimate print time, to prevent printing another zine before this one is finished 
            # printZine automatically initializes markup when needed, but we manually load it here so we can get the length of the text for the time estimate
            zine.initMarkup()
            printTime = self.secondsPerCharacter * len(zine.text) + self.basePrintTime
            print(f"{len(zine.text)} characters long. Estimated print time: {printTime} seconds.")

            print("Printing...")
            zine.printZine(self.printerManager.printer)
            self.printerManager.printer.device.flush()

            time.sleep(printTime)

            with self.printLock:
                self.printing = False

            zine.clearCache()
            print("Done printing.")
        except Exception as e:
            raise e
        finally:
            self.printing = False

    def printRandomZineFromCategory(self, category):
        with self.printLock:
            if self.printing is True:
                print(f"{YELLOW}Printing already in progress. Ignoring request to print '{category}'{ENDC}")
                return

            self.printing = True

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
        print(f"Printing random zine ({index+1}/{zineCount}) from category '{category}': {zine.metadata['title']}")

        self.randomZines[category]['index'] = (index + 1) % zineCount

        self.printZine(zine, ignoreLock=True)

    def initIndex(self, path):
        for root, dirs, files in os.walk(path):
            # ignore hidden directories
            dirs[:] = [d for d in dirs if not d[0] == '.']
            # ignore hidden files
            files = [f for f in files if not f[0] == '.']
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
                    zine = Zine(p, fullCategory)
                    zine.loadMetadata()
                    self.categories[baseCategory][p] = zine

    def initPrinter(self):
        connected = self.printerManager.connect()
        if(not connected):
            print("Printer offline. Exiting...")
            sys.exit(1)

        print("Printer ready")


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
