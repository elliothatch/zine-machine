import os
import sys
import argparse
import signal
from .zinemachine import ZineMachine
from .profile import LMP201
from .consoleprintermanager import ConsolePrinterManager
from .bluetoothprintermanager import BluetoothPrinterManager
from .zinevalidator import validateZine

BUTTON_BLUE_PIN = 16
BUTTON_YELLOW_PIN = 20
BUTTON_GREEN_PIN = 19
BUTTON_PINK_PIN = 26

RED = '\033[91m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
ENDC = '\033[0m'

def printValidationDiagnostics(path, diagnostics):
    errors = 0
    warnings = 0
    for e in diagnostics:
        color = ""
        if e.level == 'error':
            color = RED
            errors += 1 
        elif e.level == 'warning':
            color = YELLOW
            warnings += 1 

        print(f"{path}:{e.pos[0]}:{e.pos[1]} {color}{e.level}{ENDC}: {BOLD}{type(e).__name__}: {e.message}{ENDC}")
        if len(e.text) > 0:
            print(f"   {e.text}", end="")
            print(f"   {' ' * (e.pos[1] - 1)}^")

    return (errors, warnings)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='zine-machine',
        description='Press a button to print a zine on a receipt printer')

    parser.add_argument('-c', action='append', nargs='*', help='CATEGORY PIN - bind button PIN to print random zine in CATEGORY')
    # parser.add_argument('--dry', default=False, help='dry run - print to stdout instead of the receipt printer')
    parser.add_argument('--printer')
    # TODO: add file output that just prints a file and exits. remove keyboardbutton and add flag to enable/disable gpio
    parser.add_argument('--nogpio', action='store_true')

    parser.add_argument('--validate', nargs='?', const='zines')
    # if provided with no arguments, validates all zines in the './zines' directory. one argument can be provided to specify a specific zine or directory to validate

    args = parser.parse_args()

    if args.validate:
        # parser = argparse.ArgumentParser(
            # prog='sanitize-text',
            # description='Read a text file and outputs an altered version to stdout where unsupported unicode characters are replaced by similar glyphs. Also prints warnings to stderr for characters that couldn\'t be converted')

        # parser.add_argument('filename')
        # parser.add_argument('-o', '--output')

        # args = parser.parse_args()

        print(f"Validating '{os.path.abspath(args.validate)}'...")

        if os.path.isdir(args.validate):
            invalidZines = []
            totalErrors = 0
            totalWarnings = 0
            for root, dirs, files in os.walk(args.validate):
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
                    diagnostics = validateZine(path)
                    if len(diagnostics) == 0:
                        print("OK")
                        continue

                    invalidZines.append((path, diagnostics))
                    errorCount = sum(1 for d in diagnostics if d.level == 'error')
                    warningCount = sum(1 for d in diagnostics if d.level == 'warning')
                    totalErrors += errorCount
                    totalWarnings += warningCount
                    if errorCount > 0:
                        print(RED, end="")
                    else:
                        print(YELLOW, end="")
                    print(f"{errorCount} errors. {warningCount} warnings.{ENDC}")

            for zine in invalidZines:
                printValidationDiagnostics(zine[0], zine[1])

            if totalErrors > 0:
                print(RED, end="")
            elif totalWarnings > 0:
                print(YELLOW, end="")
            print(f"Validation complete. {len(invalidZines)} zines failed validation. {totalErrors} errors. {totalWarnings} warnings.{ENDC}")
            if totalErrors > 0:
                sys.exit(1)
            elif totalWarnings > 0:
                sys.exit(2)
            sys.exit(0)
        else:
            # single file
            path = args.validate
            diagnostics = validateZine(path)
            diagnosticCounts = printValidationDiagnostics(path, diagnostics)
            if diagnosticCounts[0] > 0:
                print(RED, end="")
            elif diagnosticCounts[1] > 0:
                print(YELLOW, end="")
            print(f"Validation complete. {diagnosticCounts[0]} errors. {diagnosticCounts[1]} warnings.{ENDC}")

            if diagnosticCounts[0] > 0:
                sys.exit(1)
            elif diagnosticCounts[1] > 0:
                sys.exit(2)
            sys.exit(0)

    printerManager = None

    if args.printer == "console":
        printerManager = ConsolePrinterManager()
    else:
        printerManager = BluetoothPrinterManager(LMP201())

    zineMachine = ZineMachine(printerManager, enableGPIO=not args.nogpio)

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

    # zine = zineMachine.categories['test']['zines/test/formatted.zine']
    zine = zineMachine.categories['test']['zines/test/image-test/image-test.zine']
    # zine = zineMachine.categories['queer-stuff']['zines/queer-stuff/DestroyGender.zine']
    # zine = zineMachine.categories['diy']['zines/diy/primitivecooking/primitivecooking.zine']

    zine.printHeader(zineMachine.printerManager.printer)
    zine.printZine(zineMachine.printerManager.printer)
    zine.printFooter(zineMachine.printerManager.printer)

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
