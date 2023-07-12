import sys
import time
from escpos.printer import Serial
from serial.serialutil import SerialException

class BluetoothPrinterManager:
    """ Implements the PrinterManager interface"""
    def __init__(self, profile):
        self.printerType = 'bluetooth-serial'
        self.profile = profile
        self.online = False
        # 9600 Baud, 8N1, Flow Control Enabled
        self.printer = Serial(
            profile=profile,
            devfile='/dev/rfcomm0',
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1,
            dsrdtr=True)

    def connect(self, retries, timeout):
        """
        tries to check if the printer is online.
        the printer is considered offline if it is not ready to print or there is no paper.

        this relies on the serial connection already being established. if we can't connect to the printer at all the library throws an exception. then we should crash and let systemd restart the process.

        trying to recreate the serial connection in code is really slow because the library already handles trying to resend the data, so we don't bother

        retries - number of times to retry connection
        timeout - seconds to wait between retries
        @returns True on success, False after all retries fail
        """
        try:
            for i in range(retries + 1):
                # printerStatus = self.printer.query_status(constants.RT_STATUS_ONLINE)
                # if(len(printerStatus) > 0):
                # and printerStatus[0] == 18

                if(self.printer.is_online()):
                    self.online = True
                    return True

                print("Printer offline. Retrying in {}s... ({}/{})".format(timeout, i, retries))
                sys.stdout.flush()
                time.sleep(timeout)
        except SerialException as err:
            print("Failed to connect to printer via Serial connection: {}".format(str(err)))

        self.online = False
        return False
