import os
import sys
import argparse
import signal
from .zinemachine import ZineMachine
from .profile import LMP201
from .consoleprintermanager import ConsolePrinterManager
from .bluetoothprintermanager import BluetoothPrinterManager
from .zinevalidator import ZineValidator

BUTTON_BLUE_PIN = 16
BUTTON_YELLOW_PIN = 20
BUTTON_GREEN_PIN = 19
BUTTON_PINK_PIN = 26

RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
ENDC = '\033[0m'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='zine-machine',
        description='Press a button to print a zine on a receipt printer')

    parser.add_argument('-c', action='append', nargs='*', help='CATEGORY PIN - bind button PIN to print random zine in CATEGORY')
    # parser.add_argument('--dry', default=False, help='dry run - print to stdout instead of the receipt printer')
    parser.add_argument('--printer')
    # TODO: add file output that just prints a file and exits. remove keyboardbutton and add flag to enable/disable gpio
    parser.add_argument('--nogpio', action='store_true')

    parser.add_argument('--validate', nargs='?', const='zines', metavar='PATH',
                        help='Check a zine file or directory of zines for formatting/printability issues, then exit. If specified with no value, uses $PWD/%(const)s')
    # if provided with no arguments, validates all zines in the './zines' directory. one argument can be provided to specify a specific zine or directory to validate

    parser.add_argument('--resize', nargs='?', type=int, const=576, metavar='MAXWIDTH_PX',
                        help='If using --validate, also resize images that are larger than the provided width (default: %(const)s)')

    args = parser.parse_args()

    if args.validate:
        validator = ZineValidator() if args.resize is None else ZineValidator(resizeImages=True, maxImageWidth=args.resize)
        diagnostics = validator.validateDirectory(args.validate)
        if len(diagnostics[0]) > 0:
            sys.exit(1)
        elif len(diagnostics[1]) > 0:
            sys.exit(2)

        sys.exit(0)

    printerManager = None

    if args.printer == "console":
        printerManager = ConsolePrinterManager()
    else:
        printerManager = BluetoothPrinterManager(LMP201())

    zineMachine = ZineMachine(printerManager, enableGPIO=not args.nogpio)

    if args.printer == "console":
        zineMachine.secondsPerCharacter = 0

    zineMachine.initIndex()
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


    # zineMachine.dryRun = args.dry
    # zineMachine.echoStdOut = args.dry

    # print(args)
    # zineMachine.bindButton('Test', BUTTON_BLUE_PIN)
    for c in args.c:
        if len(c) != 2:
            raise Exception('-c must have 2 inputs: CATEGORY PIN')

        pin = (BUTTON_BLUE_PIN if c[1] == 'blue' else
               BUTTON_YELLOW_PIN if c[1] == 'yellow' else
               BUTTON_GREEN_PIN if c[1] == 'green' else
               BUTTON_PINK_PIN if c[1] == 'pink' else
               int(c[1]))

        zineMachine.bindButton(c[0], pin)

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
