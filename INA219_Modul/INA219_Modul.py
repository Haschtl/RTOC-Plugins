try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import time
from ina219 import INA219
from ina219 import DeviceRangeError
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

devicename = "INA219_Modul"

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.2

SAMPLERATE = 1/60# frequency in Hz (1/sec)
I2C_ADDRESS = 0x41


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self._ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=I2C_ADDRESS)
        self._ina.configure(self._ina.RANGE_16V)
        self.run = True
        self.samplerate = SAMPLERATE            # frequency in Hz (1/sec)
        self._datanames = ['Bus Voltage', 'Bus Current', 'Power', 'Shunt Voltage']
        self._dataunits = ['V', 'mA','mW','mV']
        self._data = [0,0,0,0]
        self._status = False

        pullDataThread = Thread(target=self._getINA219_data)
        pullDataThread.start()

        self.__updater = Thread(target=self.__updateT)    # Actualize data
        self.__updater.start()

    def __updateT(self):
        diff = 0
        self.gen_start = time.time()
        while self.run:  # All should be inside of this while-loop, because self.run == False should stops this plugin
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            if self._status:
                self.stream(self._data, self._datanames, devicename, self._dataunits)
            diff = (time.time() - start_time)

    def _getINA219_data(self):
        while self.run:
            time.sleep(1/self.samplerate)
            self._ina.wake()
            self._data[0] = self._ina.voltage()
            try:
                self._data[1] = self._ina.current()
                self._data[2] = self._ina.power()
                self._data[3] = self._ina.shunt_voltage()
                self._status = True
            except DeviceRangeError as e:
                # Current out of device range with specified shunt resister
                logging.debug(e)
                self.event(text='Current out of device range with specified shunt resistor',sname=devicename, priority=1)
                self._status = False
            self._ina.sleep()
