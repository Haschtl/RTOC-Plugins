try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
import os
import sys

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
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        def _getControllerData(self):
            diff = 0
            while self.run:
                if diff < 1/self.samplerate:
                    time.sleep(1/self.samplerate-diff)
                start_time = time.time()

                self.reglerModus = "Druck"
                self.reglerActiv = False
                self.potiEnabled = False
                self.pressure_P = 0
                self.pressure_I = 0
                self.pressure_D = 0
                self.flow_P = 0
                self.flow_I = 0
                self.flow_D = 0
                self.pressureRange = [0, 10]
                self.flowRange = [0, 10]

                eFrequency = 0
                ePressure = 0
                eFlow = 0
                pressureDesired = 0
                flowDesired = 0
                frequencyDesired = 0

                rpiTemp = self._get_cpu_temperature()
                # Stream all measurements
                self.stream(list=[
                    [eFrequency, 'eFrequency', 'U/min'],
                    [ePressure, 'ePressure', 'bar'],
                    [eFlow, 'eFlow', 'm³/min'],
                    [pressureDesired, 'pressureDesired', 'bar'],
                    [flowDesired, 'flowDesired', 'm³/min'],
                    [frequencyDesired, 'frequencyDesired', 'U/min'],
                    [rpiTemp, 'CPU', '°C']
                ])
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
