try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

from .holdPeak_VC820.vc820py.vc820 import MultimeterMessage
import serial
import sys
import traceback

from PyQt5 import uic
from PyQt5 import QtWidgets
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

devicename = "HoldPeak"
default_device = 'COM7'
SERIAL_BAUDRATE = 2400
SERIAL_BYTESIZE = 8
SERIAL_TIMEOUT = 1
SAMPLERATE = 1

class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self._last_value = 0
        self._jump_allowed = True
        # Data-logger thread
        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)
        # self.updater.start()

    def __openPort(self, portname=default_device):
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
            self._serial_port = serial.Serial(
                self.portname, baudrate=SERIAL_BAUDRATE, parity='N', bytesize=SERIAL_BYTESIZE, timeout=SERIAL_TIMEOUT, rtscts=1, dsrdtr=1)
            # dtr and rts settings required for adapter
            self._serial_port.dtr = True
            self._serial_port.rts = False
            # -------------
            return True
        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            return False

    # THIS IS YOUR THREAD
    def _updateT(self):
        valid, value, unit = self._get_data()
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
            if abs(self._last_value-value) >= 2 and not self._jump_allowed:
                self._jump_allowed = True
            else:
                self.stream(y=[value], snames=datanames,  unit=unit)
                self._jump_allowed = False
            self._last_value = value

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
            self.cancel()
            self.widget.pushButton.setText("Verbinden")
        else:
            port = self.widget.comboBox.currentText()
            if self.__openPort(port):
                self.start()
                self.widget.pushButton.setText("Beenden")
            else:
                self.cancel()
                self.widget.pushButton.setText("Fehler")

    def _get_data(self):
        test = self._serial_port.read(1)
        if len(test) != 1:
            logging.error("recieved incomplete data, skipping...", file=sys.stderr)
            return False, None, None
        if MultimeterMessage.check_first_byte(test[0]):
            data = test + self._serial_port.read(MultimeterMessage.MESSAGE_LENGTH-1)
        else:
            logging.error("received incorrect data (%s), skipping..." % test.hex(), file=sys.stderr)
            return False, None, None
        if len(data) != MultimeterMessage.MESSAGE_LENGTH:
            logging.error("received incomplete message (%s), skipping..." %
                          data.hex(), file=sys.stderr)
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
