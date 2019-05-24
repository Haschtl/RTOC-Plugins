# WIRD ZUSAMMEN MIT FUTTERTROCKNUNG_SENSOREN LANGSAM

try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
import os
import sys
from threading import Thread, Timer
import traceback
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

userpath = os.path.expanduser('~/heutrocknung/Lüftersteuerung/API')
if not os.path.exists(userpath):
    logging.error('WRONG DIR TO IMPORT Controller API')
    sys.exit(1)
else:
    try:
        sys.path.insert(0, userpath)
        from controller_api import controller
    except ImportError:
        logging.error('Could not import Controller API from '+userpath)
        sys.exit(1)

devicename = "Controller"

ACTIVE_SAMPLERATE = 10
PASSIVE_SAMPLERATE = 0.1


class Plugin(LoggerPlugin, controller):
    def __init__(self, stream=None, plot=None, event=None):
        #super(Plugin, self).__init__(stream, plot, event)
        LoggerPlugin.__init__(self, stream, plot, event)
        controller.__init__(self)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = ACTIVE_SAMPLERATE
        self._controller_sensor_error = 0
        self._lastControllerStatus = 0
        self._lastSettled = 1
        self._lastModus = 0
        self._lastDisplayState = -1
        # self._thread = Thread(target=self._getControllerData)
        # self._thread.start()
        self._thread = _perpetualTimer(self.samplerate, self._getControllerData)
        self._thread.start()
        self._displayThread = Thread(target=self._checkDisplayThread)
        self._displayThread.start()

    def _getControllerData(self):
        # diff = 0
        # while self.run:
        #     if diff < 1/self.samplerate:
        #         time.sleep(1/self.samplerate-diff)
        #     start_time = time.time()
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
                    self.event('Gebläsedrehzahl wird manuell eingestellt.', dname='E', sname='Reglerstatus', priority=0, id='manuell_drehz')
                elif modus == 2:
                    self.event('Gebläsedrehzahl wird auf den Volumenstrom geregelt.', dname='E', sname='Reglerstatus', priority=0, id='volumen_regler')
                elif modus == 3:
                    self.event('Gebläsedrehzahl wird auf den Luftdrucksensor geregelt.', dname='E', sname='Reglerstatus', priority=0, id='druck_regler')
                else:
                    self.event('Gebläse abgeschaltet.', dname='E', sname='Reglerstatus', priority=0, id='geblaese_aus')
            self._lastModus = modus
            if modus in [0,1]:
                status = 0
            else:
                not_settled = self.controller_not_settled
                if not_settled:
                    if self.controller_timed_out:
                        status = -1 #rot
                        if status != self._lastControllerStatus:
                            self.event('Regler ist nicht eingeschwungen.', dname='E', sname='Reglerstatus', priority=2, id='regler_instabil')
                    elif self.set_value_out_of_range:
                        status = -2 #rot
                    else:
                        status = 2 #orange
                else:
                    status = 1 #grün
                    if self._lastSettled != not_settled and self._lastControllerStatus == -1:
                        self.event('Regler wieder eingeschwungen.', dname='E', sname='Reglerstatus', priority=0, id='regler_stabil')


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
                    self.event('Temperatur im Schacht zu hoch!', dname='E', sname='Fehler', priority=2, id='zu_heiss')
                if bmp_sensor_fault:
                    self.event('Sensorfehler (BMP) an Messstelle E!', dname='E', sname='Fehler', priority=2, id='druck_sensorfehler')
                if hvac_sensor_fault:
                    self.event('Sensorfehler (HVAC) an Messstelle E!', dname='E', sname='Fehler', priority=2, id='volumen_sensorfehler')
                self._controller_sensor_error = failure


            sensor_data = {
                'E': {'Drehzahl': [rpm, 'Hz'], 'Luftdruck': [pressure, 'hPa'], 'Temperatur1': [temp1, '°C'], 'Temperatur2': [temp2, '°C'], 'Durchfluss': [flow, 'm³/s'], 'Solldruck': [pressureDes, 'hPa'], 'Sollfluss': [flowDes, 'm³/s'], 'Reglerstatus': [status, ''], 'Sensorfehler': [failure,'']},
                'Bedienelement': {'Modus': [modus,''], 'Potentiometer':[poti, '%'], 'PotiVerwenden': [self.set_control_with_potentiometer, '']}
            }

            #logging.debug(sensor_data)
            self.stream(list=sensor_data)
            # diff = (time.time() - start_time)

    def _checkDisplayThread(self):
        while self.run:
            with open("/sys/class/backlight/rpi_backlight/bl_power", "r") as f:
                text = f.read()
            state = bool(text)
            logging.debug(state)
            if state == '1\n':
                self.samplerate = PASSIVE_SAMPLERATE
                if self._lastDisplayState != 1:
                    if self._thread:
                        self._thread.cancel()
                    self._thread = _perpetualTimer(self.samplerate, self._getControllerData)
                    self._thread.start()
                    logging.info('Samplerate changed to'+str(self.samplerate))
                self._lastDisplayState = 1
            else:
                self.samplerate = ACTIVE_SAMPLERATE
                if self._lastDisplayState != 0:
                    if self._thread:
                        self._thread.cancel()
                    self._thread = _perpetualTimer(self.samplerate, self._getControllerData)
                    self._thread.start()
                    logging.info('Samplerate changed to'+str(self.samplerate))
                self._lastDisplayState = 0
            time.sleep(0.2)

    def close(self):
        self.run = False
        if self._thread:
            self._thread.cancel()


class _perpetualTimer():  # Sollte optional noch QTimer sin!!!

    def __init__(self, t, hFunction):
        self._t = t
        self._hFunction = hFunction
        self._thread = Timer(self._t, self._handle_function)

    def _handle_function(self):
        self._hFunction()
        self._thread = Timer(self._t, self._handle_function)
        self._thread.start()

    def start(self):
        self._thread.start()

    def cancel(self):
        self._thread.cancel()


if __name__ == '__main__':
    try:
        a = Plugin(stream=None, plot=None, event=None)
    except KeyboardInterrupt:
        a.run = False
