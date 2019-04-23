try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

from .holdPeak_VC820.vc820py.vc820 import MultimeterMessage
import serial
import sys
from threading import Thread
import traceback
import os

from PyQt5 import uic
from PyQt5 import QtWidgets
import logging as log
log.basicConfig(level=log.DEBUG)
logging = log.getLogger(__name__)

devicename = "HoldPeak"
default_device = 'COM7'
SERIAL_BAUDRATE = 2400
SERIAL_BYTESIZE = 8
SERIAL_TIMEOUT = 1


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        # Data-logger thread
        self.run = False  # False -> stops thread
        self.__updater = Thread(target=self.updateT)    # Actualize data
        # self.updater.start()

    def __openPort(self, portname=default_device):
        self.datanames = ['Data']     # Names for every data-stream

        # Communication setup
        #self.portname = "/dev/ttyUSB0"
        #self.portname = "COM7"
        self.portname = portname
        #################################################################################
        # os.system("sudo chmod a+rw /dev/ttyUSB0")
        # #######
        # uncomment this line if you do not set device rules:
        # > sudo nano /etc/udev/rules.d/50-myusb.rules
        # > * SUBSYSTEMS=="usb", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", GROUP="users", MODE="0666"
        # > [Strg+O, Strg+X]
        # > sudo udevadm control --reload
        # Ref: http://ask.xmodulo.com/change-usb-device-permission-linux.html
        #################################################################################
        try:
            self.serial_port = serial.Serial(
                self.portname, baudrate=SERIAL_BAUDRATE, parity='N', bytesize=SERIAL_BYTESIZE, timeout=SERIAL_TIMEOUT, rtscts=1, dsrdtr=1)
            # dtr and rts settings required for adapter
            self.serial_port.dtr = True
            self.serial_port.rts = False
            # -------------
            return True
        except:
            tb = traceback.format_exc()
            logging.debug(tb)
            return False

    # THIS IS YOUR THREAD
    def updateT(self):
        last_value = 0
        jump_allowed = True
        while self.run:
            valid, value, unit = self.get_data()
            if unit == "V":
                datanames = ["Spannung"]
            elif unit == "A":
                datanames = ["Strom"]
            elif unit == "Ohm":
                datanames = ["Widerstand"]
            elif unit == "°C":
                datanames = ["Temperatur"]
            elif unit == "F":
                datanames = ["Kapazität"]
            elif unit == "Hz":
                datanames = ["Frequenz"]
            else:
                datanames = [unit]
            if valid:
                if abs(last_value-value)>=2 and not jump_allowed:
                    #self.stream([last_value],  datanames,  self.devicename, unit)
                    jump_allowed = True
                else:
                    self.stream([value],  datanames,  self.devicename, unit)
                    jump_allowed = False
                last_value = value

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/holdPeak_VC820/portSelectWidget.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openPortCallback)
        self.__openPortCallback()
        return self.widget

    def __openPortCallback(self):
        if self.run:
            self.run = False
            self.widget.pushButton.setText("Verbinden")
        else:
            port = self.widget.comboBox.currentText()
            if self.__openPort(port):
                self.run = True
                self.__updater = Thread(target=self.updateT)    # Actualize data
                self.__updater.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.run = False
                self.widget.pushButton.setText("Fehler")

    def get_data(self):
        test = self.serial_port.read(1)
        if len(test) != 1:
            logging.error("recieved incomplete data, skipping...", file=sys.stderr)
            return False, None, None
        if MultimeterMessage.check_first_byte(test[0]):
            data = test + self.serial_port.read(MultimeterMessage.MESSAGE_LENGTH-1)
        else:
            logging.error("received incorrect data (%s), skipping..." % test.hex(), file=sys.stderr)
            return False, None, None
        if len(data) != MultimeterMessage.MESSAGE_LENGTH:
            logging.error("received incomplete message (%s), skipping..." % data.hex(), file=sys.stderr)
            return False, None, None
        try:
            message = MultimeterMessage(data)
            #message.value = message.get_base_reading()
        except ValueError as e:
            logging.debug(e)
            logging.error("Error decoding: %s on message %s" % (str(e), data.hex()))
            return False, None, None
        # logging.debug(str(message))
        # return True, message.value, message.unit
        return True, round(message.value*message.multiplier, 10), message.base_unit


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
