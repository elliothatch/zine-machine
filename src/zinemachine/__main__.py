import argparse
import signal
from .zinemachine import ZineMachine
from .profile import LMP201

BUTTON_BLUE_PIN = 16
BUTTON_YELLOW_PIN = 20
BUTTON_GREEN_PIN = 19
BUTTON_PINK_PIN = 26

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='zine-machine',
        description='Press a button to print a zine on a receipt printer')

    parser.add_argument('-c', action='append', nargs='*', help='CATEGORY PIN - bind button PIN to print random zine in CATEGORY')
    parser.add_argument('--dry', default=False, help='dry run - print to stdout instead of the receipt printer')

    args = parser.parse_args()

    zineMachine = ZineMachine(LMP201())

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
    zineMachine.initPrinter()

    zineMachine.dryRun = args.dry
    zineMachine.echoStdOut = args.dry

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

    # zineMachine.printZine(zineMachine.categories['Theory']['categories/Theory/revolutionary-organisations-and-individual-commitment-monsieur-dupont.zine'])
    # zineMachine.printZine(zineMachine.categories['DIY']['categories/DIY/how-to-make-a-zine-machine-entry.zine'])
    # zineMachine.printZine(zineMachine.categories['DIY']['categories/DIY/test2.zine'])
    # zineMachine.printer.text("\n\n")

    signal.pause()
