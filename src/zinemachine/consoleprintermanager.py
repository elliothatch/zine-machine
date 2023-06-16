from .consoleprinter import ConsolePrinter

""" Implements the PrinterManager interface"""
class ConsolePrinterManager(object):
    def __init__(self):
        self.printerType = 'console'
        self.printer = ConsolePrinter()
        self.online = True

    def connect(self):
        return True
