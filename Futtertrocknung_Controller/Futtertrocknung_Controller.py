# WIRD ZUSAMMEN MIT FUTTERTROCKNUNG_SENSOREN LANGSAM

try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
import os
import sys
from threading import Thread
import traceback

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
        self.samplerate = 10

        self._thread = Thread(target=self._getControllerData)
        self._thread.start()

    def _getControllerData(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            # Stream all measurements
            rpm = self.rpm
            pressure = self.air_pressure
            flow = self.flow_rate
            pressureDes = self.air_pressure_set
            flowDes = self.flow_rate_set
            temp1 = self.temperature1
            temp2 = self.temperature2
            poti = self.potentiometer
            reglerAn = self.control_enabled
            if reglerAn:
                manuell = self.control_manual_selection
                if manuell:
                    modus = 1
                else:
                    m = self.control_input
                    if m == 1:
                        modus = 2
                    else:
                        modus = 3
            else:
                modus = 0

            status = self.controller_not_settled
            if not status:
                if self.controller_timed_out or self.set_value_out_of_range or self.overtemperature or self.bmp_sensor_fault or self.hvac_sensor_fault:
                    status = -1
                else:
                    status = 0
            else:
                status = 1


            sensor_data = {
                'E': {'Drehzahl': [rpm, 'U/min'], 'Luftdruck': [pressure, 'hPa'], 'Temperatur1': [temp1, '°C'], 'Temperatur2': [temp2, '°C'], 'Durchfluss': [flow, 'm³/s'], 'Solldruck': [pressureDes, 'hPa'], 'Sollfluss': [flowDes, 'm³/s'], 'Reglerstatus': [status, '']},
                'Bedienelement': {'Modus': [modus,''], 'Potentiometer':[poti, '%']}
            }
            #print(sensor_data)
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)


if __name__ == '__main__':
    try:
        a = Plugin(stream=None, plot=None, event=None)
    except KeyboardInterrupt:
        a.run = False
