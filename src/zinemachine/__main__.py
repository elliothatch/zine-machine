import os
import sys
import argparse
import signal
from .zinemachine import ZineMachine
from .profile import LMP201
from .consoleprintermanager import ConsolePrinterManager
from .bluetoothprintermanager import BluetoothPrinterManager
from .zinevalidator import ZineValidator
from .zine import Zine

from pathlib import PurePath


BUTTON_BLUE_PIN = 16
BUTTON_YELLOW_PIN = 20
BUTTON_GREEN_PIN = 19
BUTTON_PINK_PIN = 26

RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
ENDC = '\033[0m'

def initZineMachine(args):
    if args.stdio:
        zineMachine = ZineMachine(ConsolePrinterManager(), secondsPerCharacter=0.0, basePrintTime=0.0)
        return zineMachine
    else:
        zineMachine = ZineMachine(BluetoothPrinterManager(LMP201()))
        return zineMachine


def validateZines(args):
    validator = ZineValidator() if args.resize is None else ZineValidator(resizeImages=True, maxImageWidth=args.resize)
    diagnostics = validator.validateDirectory(args.file)
    if len(diagnostics[0]) > 0:
        sys.exit(1)
    elif len(diagnostics[1]) > 0:
        sys.exit(2)

def printZines(args):
    zineMachine = initZineMachine(args)
    pathParts = PurePath(args.file).parts
    category = pathParts[1] if len(pathParts) >= 2 else pathParts[0] if len(pathParts) >= 1 else None
    zine = Zine(args.file, category)
    zineMachine.printZine(zine)

def serveZines(args):
    zineMachine = initZineMachine(args)
    zineMachine.initIndex(args.zines_dir)

    print('{} zines loaded'.format(sum([len(v) for v in zineMachine.categories.values()])))
    for k, v in zineMachine.categories.items():
        print('{}: {}'.format(k, len(v)))
        for p, z in v.items():
            print('   {}'.format(z.metadata['title']), end="")
            # print('   path: {}'.format(z.path))
            # print("   category: {}".format(z.category))
            # print("   metadata:")
            # for m, mv in z.metadata.items():
            #     print("      {}: {}".format(m, mv))

            print()

        print()

    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)

    from .inputmanager import InputManager
    inputManager = InputManager()

    for c in args.category:
        if len(c) != 2:
            raise Exception('-c must have 2 inputs: CATEGORY PIN')

        pin = (BUTTON_BLUE_PIN if c[1] == 'blue' else
               BUTTON_YELLOW_PIN if c[1] == 'yellow' else
               BUTTON_GREEN_PIN if c[1] == 'green' else
               BUTTON_PINK_PIN if c[1] == 'pink' else
               int(c[1]))

        inputManager.addButton(pin, c[1])
        inputManager.addChord(frozenset([pin]), lambda chord,holdTime,category=c[0]: zineMachine.printRandomZineFromCategory(category))

    def restart(chord, holdTime):
        try:
            zineMachine.printText("Resetting. Please wait...\n\n\n")
        except Exception as e:
            print(e)
        print("Exiting...")
        os._exit(0)

    def shutdown(chord, holdTime):
        try:
            zineMachine.printText("Shutting down...\n\n\n")
        except Exception as e:
            print(e)
        print("Shutting down...")
        result = os.system("sudo shutdown now")
        if result != 0:
            try:
                zineMachine.printText("Shutdown failed.\n\n\n")
            except Exception as e:
                print(e)
            print("Shutdown failed.")


    inputManager.addChord(frozenset([BUTTON_YELLOW_PIN, BUTTON_GREEN_PIN, BUTTON_PINK_PIN]), restart, holdTime=5.0)
    inputManager.addChord(frozenset([BUTTON_BLUE_PIN, BUTTON_YELLOW_PIN, BUTTON_GREEN_PIN, BUTTON_PINK_PIN]), shutdown, holdTime=5.0)


    zineCount = sum([len(v) for v in zineMachine.categories.values()])
    zineMachine.printText(f"{zineCount} zines loaded. Ready to print!\n\n\n\n\n\n")
    signal.pause()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='zine-machine',
        description='Press a button to print a zine on a receipt printer')


    parser.add_argument('command', help='command to execute')
    parser.add_argument('-v', '--version', action='store_true', help='Show version and exit')

    subparsers = parser.add_subparsers(title='commands', required=True)

    # validate
    validateParser = subparsers.add_parser('validate', help='Validate zines for formatting or printability issues')
    validateParser.add_argument('file', nargs='?', default='zines',
        help='File or directory to validate (default: $PWD/%(const)s)')

    validateParser.add_argument('--resize', nargs='?', type=int, const=576, metavar='MAXWIDTH_PX',
        help='Automatically resize images that are larger than the provided width. If --resize is provided with no value, defaults to %(const)s). A backup is saved as {FILE}.orig')

    validateParser.set_defaults(func=validateZines)

    # print
    printParser = subparsers.add_parser('print', help='Print a single zine and exit')

    printParser.add_argument('file', help='The zine to print')
    printParser.add_argument('--stdio', action='store_true', help='Print zine to console stdio instead of a receipt printer')
    # printParser.add_argument('--profile', help='File containing a JSON profile for the printer model')
    printParser.set_defaults(func=printZines)

    # serve
    serveParser = subparsers.add_parser('serve', help='Listen for GPIO button inputs and print zines according to category')
    serveParser.add_argument('zines_dir', nargs='?', default='zines',
        help='Directory containing zine categories (default: $PWD/%(const)s)')
    serveParser.add_argument('-c', '--category', action='append', nargs='*', help='CATEGORY PIN - bind button PIN to print random zine in CATEGORY')
    serveParser.add_argument('--stdio', action='store_true', help='Print zine to console stdio instead of a receipt printer')
    # serveParser.add_argument('--profile', help='File containing a JSON profile for the printer model')
    serveParser.set_defaults(func=serveZines)


    if len(sys.argv) < 2:
        parser.print_help()
        exit(1)

    args = parser.parse_args(sys.argv)

    args.func(args)
    exit(0)


    """
    from .inputmanager import InputManager
    inputManager = InputManager()
    inputManager.addButton(BUTTON_BLUE_PIN, 'blue')
    inputManager.addButton(BUTTON_YELLOW_PIN, 'yellow')
    inputManager.addButton(BUTTON_GREEN_PIN, 'green')
    inputManager.addButton(BUTTON_PINK_PIN, 'pink')

    def printInput(pins, holdTime):
        names = [inputManager.buttons[pin].name for pin in pins]
        print(f"{names}, {holdTime}")

    allPins = [BUTTON_BLUE_PIN, BUTTON_YELLOW_PIN, BUTTON_GREEN_PIN, BUTTON_PINK_PIN]

    allPermutations = set()

    # test pressRelease
    for pin in allPins:
        allPermutations.add(frozenset([pin]))

        for pin2 in allPins:
            if pin2 == pin:
                continue
            allPermutations.add(frozenset([pin, pin2]))

            for pin3 in allPins:
                if pin3 == pin or pin3 == pin2:
                    continue
                allPermutations.add(frozenset([pin, pin2, pin3]))
                for pin4 in allPins:
                    if pin4 == pin or pin4 == pin2 or pin4 == pin3:
                        continue
                    allPermutations.add(frozenset([pin, pin2, pin3, pin4]))

    for p in allPermutations:
        inputManager.addChord(p, printInput)
        inputManager.addChord(p, printInput, holdTime=1.0)
        inputManager.addChord(p, printInput, holdTime=2.0)
    """

    print("Ready.")

    # zineMachine.printRandomZineFromCategory('diy')
    # zine = zineMachine.categories['test']['zines/test/formatted.zine']
    # zine = zineMachine.categories['test']['zines/test/image-test/image-test.zine']
    # zine = zineMachine.categories['test']['zines/test/lorem-ipsum-2500.zine']
    # zine = zineMachine.categories['queer-stuff']['zines/queer-stuff/DestroyGender.zine']
    # zine = zineMachine.categories['diy']['zines/diy/primitivecooking/primitivecooking.zine']

    # zine.printHeader(zineMachine.printerManager.printer)
    # zineMachine.printerManager.printer.device.flush()
    # zine.printZine(zineMachine.printerManager.printer)
    # zineMachine.printerManager.printer.device.flush()
    # zine.printFooter(zineMachine.printerManager.printer)
    # zineMachine.printerManager.printer.device.flush()


    # zine.printHeader(zineMachine.printer)
    # zine.printZine(zineMachine.printer)
    # zine.printFooter(zineMachine.printer)

    # print('\033[0m')
    # print("Done")


    # zineMachine.printZine(zineMachine.categories['Theory']['categories/Theory/revolutionary-organisations-and-individual-commitment-monsieur-dupont.zine'])
    # zineMachine.printZine(zineMachine.categories['DIY']['categories/DIY/how-to-make-a-zine-machine-entry.zine'])
    # zineMachine.printZine(zineMachine.categories['DIY']['categories/DIY/test2.zine'])
    # zineMachine.printer.text("\n\n")

    signal.pause()
