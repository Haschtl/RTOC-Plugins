try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import sys
import traceback

from PyQt5 import uic
from PyQt5 import QtWidgets
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    import minimalmodbus
except ImportError:
    sys.exit("\nERROR\nminimalmodbus for Python3 not found!\nPlease install with 'pip3 install minimalmodbus'")

devicename = "DPS5020"
default_device = '/dev/ttyUSB0'

SERIAL_BAUDRATE = 9600
SERIAL_BYTESIZE = 8
SERIAL_TIMEOUT = 2
SAMPLERATE = 1

class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.smallGUI = True

        self.__data = None
        self.smallGUI = True
        self._locked = False
        self._power = False
        self.__serialBaudrate = SERIAL_BAUDRATE
        self.__serialByteSize = SERIAL_BYTESIZE
        self.__serialTimeOut = SERIAL_TIMEOUT
        self._CV = True  # False = CC

        # Data-logger thread
        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)
        # self.updater.start()

    def __openPort(self, portname=default_device):
        self.__datanames = ['VOut', 'IOut', "POut", "VIn",
                            "VSet", "ISet"]     # Names for every data-stream
        self.__dataY = [0, 0, 0, 0, 0, 0]
        # Represents the unit of the current
        self.__dataunits = ['V', 'A', 'W', 'V', 'V', 'V']
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
            self.__powerSupply = minimalmodbus.Instrument(self.portname, 1)
            self.__powerSupply.serial.baudrate = self.__serialBaudrate
            self.__powerSupply.serial.bytesize = self.__serialByteSize
            self.__powerSupply.serial.timeout = self.__serialTimeOut
            self.__powerSupply.mode = minimalmodbus.MODE_RTU
            # -------------
            return True
        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            return False

    # THIS IS YOUR THREAD
    def _updateT(self):
            valid, values = self._get_data()
            self.__dataY = values
            if valid:
                self.stream(y=self.__dataY, snames=self.__datanames, unit=self.__dataunits)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/DPS5020/dps5020.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openPortCallback)
        self.widget.currBox.editingFinished.connect(self._setCurrAction)
        self.widget.voltBox.editingFinished.connect(self._setVoltAction)
        self.widget.maxCurrBox.editingFinished.connect(self._setMaxCurrAction)
        self.widget.maxVoltBox.editingFinished.connect(self._setMaxVoltAction)
        self.widget.maxPowBox.editingFinished.connect(self._setMaxPowAction)
        self.__openPortCallback()
        self._setLabels()
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
        try:
            with self.lockPerpetialTimer:
                self.__data = self.__powerSupply.read_registers(0, 11)
            # data[0] U-set x100 (R/W)
            # data[1] I-set x100 (R/W)
            # data[2] U-out x100
            # data[3] I-out x100
            # data[4] P-out x100
            # data[5] U-in x100
            # data[6] lock/unlock 1/0 (R/W)
            # data[7] Protected 1/0
            # data[8] operating mode CC/CV 1/0
            # data[9] on/off 1/0 (R/W)
            # data[10] display intensity 1..5 (R/W)
            if self.__data[6] == 1:
                self._locked = True
            else:
                self._locked = False
            if self.__data[8] == 1:
                self._CV = False
            else:
                self._CV = True
            if self.__data[9] == 1:
                self._power = True
            else:
                self._power = False
                ['VOut', 'IOut', "POut", "VIn", "VSet", "ISet"]
            self._setLabels()
            return True, [self.__data[2]/100, self.__data[3]/100, self.__data[4]/100, self.__data[5]/100, self.__data[0]/100, self.__data[1]/100]
        except Exception:
            tb = traceback.format_exc()
            logging.debug(tb)
            return False, []

    def setPower(self, value=False):
        if self.run:
            logging.info("Changing power-state")
            # onoff=self.__powerSupply.read_register(9)
            # self.powerButton.setChecked(bool(onoff))
            with self.lockPerpetialTimer:
                if value:
                    self.__powerSupply.write_register(9, 1)
                    self.__event("Power on")
                else:
                    self.__powerSupply.write_register(9, 0)
                    self.__event("Power off")
            self._power = value

    def setLocked(self, value=True):
        if self.run:
            logging.info("Changing locked-state")
            # onoff=self.__powerSupply.read_register(6)
            # self.powerButton.setChecked(bool(onoff))
            with self.lockPerpetialTimer:
                if value:
                    self.__powerSupply.write_register(6, 1)
                else:
                    self.__powerSupply.write_register(6, 0)
            self._locked = value

    def setVoltage(self, value=0):
        if self.run:
            with self.lockPerpetialTimer:
                self.__powerSupply.write_register(0, int(value*100))

    def setCurrent(self, value=0):
        with self.lockPerpetialTimer:
            self.__powerSupply.write_register(1, int(value*100))

    def _setCurrAction(self):
        value = self.widget.currBox.value()
        self.setCurrent(value)

    def _setVoltAction(self):
        value = self.widget.voltBox.value()
        self.setCurrent(value)

    def _setMaxCurrAction(self):
        value = self.widget.maxCurrBox.value()

    def _setMaxVoltAction(self):
        value = self.widget.maxVoltBox.value()

    def _setMaxPowAction(self):
        value = self.widget.maxPowBox.value()

    def _setLabels(self):
        # if self.__data:
            #    if self.widget.currBox.value()!=self.__data[1]/100:
            #        self.widget.currBox.setValue(self.__data[1]/100)
            #    if self.widget.voltBox.value()!=self.__data[0]/100:
            #        self.widget.voltBox.setValue(self.__data[0]/100)
        pass
        # self.widget.maxCurrBox.setValue(self.gen_level)
        # self.widget.maxVoltBox.setValue(self.offset)
        # self.widget.maxPowBox.setValue(self.phase)


if __name__ == "__main__":
    standalone = Plugin()
