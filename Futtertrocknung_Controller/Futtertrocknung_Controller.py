try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
import os
import sys
from threading import Thread

userpath = os.path.expanduser('~/heutrocknung/Lüftersteuerung/API')
if not os.path.exists(userpath):
    print('WRONG DIR TO IMPORT Controller API')
    sys.exit(1)
else:
    try:
        sys.path.insert(0, userpath)
        from controller_api import controller
    except ImportError:
        print('Could not import Controller API from '+userpath)
        sys.exit(1)

devicename = "Controller"


class Plugin(LoggerPlugin, controller):
    def __init__(self, stream=None, plot=None, event=None):
        #super(Plugin, self).__init__(stream, plot, event)
        LoggerPlugin.__init__(self, stream, plot, event)
        controller.__init__(self)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        self._thread = Thread(target=self._getControllerData)
        self._thread.start()

    def _getControllerData(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()

            # Stream all measurements
            sensor_data = {
                'E': {'Drehzahl': [self.rpm, 'U/min'], 'Luftdruck': [self.air_pressure, 'bar'], 'Temperatur1': [self.temperature1, '°C'], 'Temperatur2': [self.temperature2, '°C'], 'Durchfluss': [self.flow_rate, 'm³/s']}
            }
            #print(sensor_data)
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)

        # def setActive(self, active=True):
        #     pass
        #
        # def setMode(self, mode=0):  # manuell, druck, durchfluss
        #     pass
        #
        # def setPID(self, mode, p, i, d):
        #     pass
        #
        # def setDesired(self, mode, value):
        #     pass
