import textwrap
from escpos.printer import Serial

""" 9600 Baud, 8N1, Flow Control Enabled """
p = Serial(devfile='/dev/rfcomm0',
           baudrate=9600,
           bytesize=8,
           parity='N',
           stopbits=1,
           timeout=1.00,
           dsrdtr=True)

testStr = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~\n"

#output = textwrap.wrap(testStr, width=48)

def resetFormatting():
    p.set(align="left", width=1, height=1, font="a", text_type="NORMAL", invert=False, flip=False)

def testPrintA():
    resetFormatting()
    p.text(testStr)

    p.set(align="center")
    p.text("align=center\n")

    p.set(align="right")
    p.text("align=right\n")

    p.set(text_type="B")
    p.text("text_type=B\n")

    p.set(text_type="U")
    p.text("text_type=U\n")

    p.set(text_type="U2")
    p.text("text_type=U2\n")

    p.set(text_type="BU")
    p.text("text_type=BU\n")

    p.set(text_type="BU2")
    p.text("text_type=BU2\n")

    p.set(invert=True)
    p.text("invert=True\n")

    p.set(flip=True)
    p.text("flip=True\n")

def printFile(path):
    textWrapper = textwrap.TextWrapper(width=48, expand_tabs=True, tabsize=4)
    print(f"opening file for print: {path}")
    with open(path, encoding="utf-8") as f:
        p.text("=" * 48)
        p.text("\n\n")
        #text = f.read()
        print("wrapping text...")
        #textWrapped = textwrap.wrap(text, width=48, replace_whitespace=False, drop_whitespace=False) 
        #print(textWrapped)
        #print(f"printing {len(textWrapped)} lines...")
        #for line in textWrapped:
        #    print(line)

        for line in f:
            wrapped = textWrapper.wrap(line)
            for l in wrapped:
                print(l)
                p.text(l)
                p.text("\n")
            if(len(wrapped) == 0):
                print()
                p.text("\n")

            #p.text(line)
            #p.text("\n")

        #for line in file:
            #p.text(line)

        p.text("=" * 48)
        p.text("\n\n\n")


printFile("./revolutionary-organisations-and-individual-commitment-monsieur-dupont.txt")
