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
        self._controller_sensor_error = 0
        self._lastControllerStatus = 0
        self._lastSettled = 1
        self._lastModus = 0
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
            poti = self.potentiometer*100
            reglerAn = self.control_enabled
            if reglerAn:
                manuell = self.control_manual_selection
                if not manuell:
                    modus = 1
                else:
                    m = self.control_input
                    if m == 1:
                        modus = 2
                    else:
                        modus = 3
            else:
                modus = 0
            if modus != self._lastModus:
                if modus == 1:
                    self.event('Gebläsedrehzahl wird manuell eingestellt.', dname='E', sname='Reglerstatus', priority=0)
                elif modus == 2:
                    self.event('Gebläsedrehzahl wird auf den Volumenstrom geregelt.', dname='E', sname='Reglerstatus', priority=0)
                elif modus == 3:
                    self.event('Gebläsedrehzahl wird auf den Luftdrucksensor geregelt.', dname='E', sname='Reglerstatus', priority=0)
                else:
                    self.event('Gebläse abgeschaltet.', sname='E', dname='Reglerstatus', priority=0)
            self._lastModus = modus
            if modus in [0,1]:
                status = 0
            else:
                not_settled = self.controller_not_settled
                if not_settled:
                    if self.controller_timed_out:
                        status = -1 #rot
                        if status != self._lastControllerStatus:
                            self.event('Regler ist nicht eingeschwungen.', sname='E', dname='Reglerstatus', priority=2)
                    elif self.set_value_out_of_range:
                        status = -2 #rot
                    else:
                        status = 2 #orange
                else:
                    status = 1 #grün
                    if self._lastSettled != not_settled:
                        self.event('Regler wieder eingeschwungen.', sname='E', dname='Reglerstatus', priority=0)


                self._lastSettled = not_settled
            self._lastControllerStatus = status

            failure = 0
            if self.overtemperature:
                failure += 1
            if self.bmp_sensor_fault:
                failure +=3
            if self.hvac_sensor_fault:
                failure +=5

            if failure != self._controller_sensor_error:
                overtemp = False
                bmp_sensor_fault = False
                hvac_sensor_fault = False
                if failure == 0:
                    # no error
                    pass
                elif failure == 1:
                    overtemp = True
                elif failure == 3:
                    bmp_sensor_fault = True
                elif failure == 5:
                    hvac_sensor_fault = True
                elif failure == 4:
                    overtemp = True
                    bmp_sensor_fault = True
                elif failure == 6:
                    overtemp = True
                    hvac_sensor_fault = True
                elif failure == 8:
                    bmp_sensor_fault = True
                    hvac_sensor_fault = True
                elif failure == 9:
                    overtemp = True
                    bmp_sensor_fault = True
                    hvac_sensor_fault = True

                if overtemp:
                    self.event('Temperatur im Schacht zu hoch!', sname='E', dname='Temperatur1', priority=2)
                if bmp_sensor_fault:
                    self.event('Sensorfehler (BMP) an Messstelle E!', sname='E', dname='Temperatur1', priority=2)
                if hvac_sensor_fault:
                    self.event('Sensorfehler (HVAC) an Messstelle E!', sname='E', dname='Temperatur1', priority=2)
                self._controller_sensor_error = failure


            sensor_data = {
                'E': {'Drehzahl': [rpm, 'Hz'], 'Luftdruck': [pressure, 'hPa'], 'Temperatur1': [temp1, '°C'], 'Temperatur2': [temp2, '°C'], 'Durchfluss': [flow, 'm³/s'], 'Solldruck': [pressureDes, 'hPa'], 'Sollfluss': [flowDes, 'm³/s'], 'Reglerstatus': [status, ''], 'Sensorfehler': [failure,'']},
                'Bedienelement': {'Modus': [modus,''], 'Potentiometer':[poti, '%'], 'PotiVerwenden': [self.set_control_with_potentiometer, '']}
            }
            #print(sensor_data)
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)


if __name__ == '__main__':
    try:
        a = Plugin(stream=None, plot=None, event=None)
    except KeyboardInterrupt:
        a.run = False
