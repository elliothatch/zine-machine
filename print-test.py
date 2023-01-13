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

def testPrintB():
    p.set(font="b")
    p.text(testStr)

    p.set(font="b", align="center")
    p.text("align=center\n")

    p.set(font="b", align="right")
    p.text("align=right\n")

    p.set(font="b", text_type="B")
    p.text("text_type=B\n")

    p.set(font="b", text_type="U")
    p.text("text_type=U\n")

    p.set(font="b", text_type="U2")
    p.text("text_type=U2\n")

    p.set(font="b", text_type="BU")
    p.text("text_type=BU\n")

    p.set(font="b", text_type="BU2")
    p.text("text_type=BU2\n")

    p.set(font="b", invert=True)
    p.text("invert=True\n")

    p.set(font="b", flip=True)
    p.text("flip=True\n")

def testPrintALarge():
    p.set(width=2, height=2)
    p.text(testStr)

    p.set(width=2, height=2, align="center")
    p.text("align=center\n")

    p.set(width=2, height=2, align="right")
    p.text("align=right\n")

    p.set(width=2, height=2, text_type="B")
    p.text("text_type=B\n")

    p.set(width=2, height=2, text_type="U")
    p.text("text_type=U\n")

    p.set(width=2, height=2, text_type="U2")
    p.text("text_type=U2\n")

    p.set(width=2, height=2, text_type="BU")
    p.text("text_type=BU\n")

    p.set(width=2, height=2, text_type="BU2")
    p.text("text_type=BU2\n")

    p.set(width=2, height=2, invert=True)
    p.text("invert=True\n")

    p.set(width=2, height=2, flip=True)
    p.text("flip=True\n")


def testPrintBLarge():
    p.set(width=2, height=2, font="b")
    p.text(testStr)

    p.set(width=2, height=2, font="b", align="center")
    p.text("align=center\n")

    p.set(width=2, height=2, font="b", align="right")
    p.text("align=right\n")

    p.set(width=2, height=2, font="b", text_type="B")
    p.text("text_type=B\n")

    p.set(width=2, height=2, font="b", text_type="U")
    p.text("text_type=U\n")

    p.set(width=2, height=2, font="b", text_type="U2")
    p.text("text_type=U2\n")

    p.set(width=2, height=2, font="b", text_type="BU")
    p.text("text_type=BU\n")

    p.set(width=2, height=2, font="b", text_type="BU2")
    p.text("text_type=BU2\n")

    p.set(width=2, height=2, font="b", invert=True)
    p.text("invert=True\n")

    p.set(width=2, height=2, font="b", flip=True)
    p.text("flip=True\n")

def testPrintQR():
    p.qr("QR size 1", size=1)
    p.qr("QR size 4", size=4)
    p.qr("QR size 8", size=8)
    p.qr("QR size 16", size=16)

def testPrintDensity():
    for i in range(0,9):
        p.set(density=i)
        p.text("density=" + str(i))
        p.text("density=" + str(i))
        p.text("density=" + str(i))
        p.text("density=" + str(i))
        p.text("density=" + str(i))
        p.text("\n")

def testPrintImage():
    p.image("test.png")

resetFormatting()
p.text("\n\n")

p.text('kožušček \u5317\u4EB0')

#testPrintA()
#testPrintB()
#testPrintALarge()
#testPrintBLarge()
#testPrintQR()
#testPrintImage()

resetFormatting()
p.text("\n\n\n")

#testPrintDensity()

# doesn't work?
#p.barcode("123456", "UPC-E")


