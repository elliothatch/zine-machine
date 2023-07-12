from .consoleprinter import ConsolePrinter

class ConsolePrinterManager(object):
    """ Implements the PrinterManager interface"""
    def __init__(self):
        self.printerType = 'console'
        self.printer = ConsolePrinter()
        self.online = True

    def connect(self):
        return True
