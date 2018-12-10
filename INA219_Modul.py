try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from ..LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import time
from ina219 import INA219
from ina219 import DeviceRangeError

devicename = "INA219_Modul"

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.2

SAMPLERATE = 1/60# frequency in Hz (1/sec)
I2C_ADDRESS = 0x41


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=I2C_ADDRESS)
        self.ina.configure(self.ina.RANGE_16V)
        self.run = True
        self.samplerate = samplerate            # frequency in Hz (1/sec)
        self.datanames = ['Bus Voltage', 'Bus Current', 'Power', 'Shunt Voltage']
        self.dataunits = ['V', 'mA','mW','mV']
        self.data = [0,0,0,0]
        self.status = False

        pullDataThread = Thread(target=self.getINA219_data)
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
            if self.status:
                self.stream(self.data, self.datanames, devicename, self.dataunits)
            diff = (time.time() - start_time)

    def getINA219_data(self):
        while self.run:
            time.sleep(1/self.samplerate)
            self.ina.wake()
            self.data[0] = self.ina.voltage()
	        try:
                self.data[1] = self.ina.current()
                self.data[2] = self.ina.power()
                self.data[3] = self.ina.shunt_voltage()
                self.status = True
            except DeviceRangeError as e:
                # Current out of device range with specified shunt resister
                print(e)
                self.event(text='Current out of device range with specified shunt resistor',sname=devicename, priority=1)
                self.status = False
            self.ina.sleep()
