try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import numpy as np
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

devicename = "FAKE"
ACTIVE_SAMPLERATE = 10



class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = ACTIVE_SAMPLERATE

        self._sensor_data = {
            'A': {'Temperatur': [None, '°C'], 'CO2-Gehalt': [None, 'ppm'], 'TVOC-Gehalt': [None, 'ppm'], 'Temperatur2': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'B': {'Temperatur': [None, '°C'], 'CO2-Gehalt': [None, 'ppm'], 'TVOC-Gehalt': [None, 'ppm'], 'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'C': {'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'D': {'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'Bedienelement': {'CPU-Temperatur': [None, '°C']},
        }

        self._thread = Thread(target=self._sensorThread)
        self._thread.start()

    def r(self):
        return np.random.random()
    def _getAllSensors(self, processed=True):
        self._sensor_data = {
            'A': {'Temperatur': [self.r(), '°C'], 'CO2-Gehalt': [self.r(), 'ppm'], 'TVOC-Gehalt': [self.r(), 'ppm'], 'Temperatur2': [self.r(), '°C'], 'Feuchtigkeit': [self.r(), '%']},
            'B': {'Temperatur': [self.r(), '°C'], 'CO2-Gehalt': [self.r(), 'ppm'], 'TVOC-Gehalt': [self.r(), 'ppm'], 'Temperatur': [self.r(), '°C'], 'Feuchtigkeit': [self.r(), '%']},
            'C': {'Temperatur': [self.r(), '°C'], 'Feuchtigkeit': [self.r(), '%']},
            'D': {'Temperatur': [self.r(), '°C'], 'Feuchtigkeit': [self.r(), '%']},
            'Bedienelement': {'CPU-Temperatur': [self.r(), '°C']},
            'E': {'Drehzahl': [self.r(), 'Hz'], 'Luftdruck': [self.r(), 'hPa'], 'Temperatur1': [self.r(), '°C'], 'Temperatur2': [self.r(), '°C'], 'Durchfluss': [self.r(), 'm³/s'], 'Solldruck': [self.r(), 'hPa'], 'Sollfluss': [self.r(), 'm³/s'], 'Reglerstatus': [1, ''], 'Sensorfehler': [self.r(),'']},
            'Bedienelement': {'Modus': [0,''], 'Potentiometer':[0, '%'], 'PotiVerwenden': [0, '']
        }}

        return self._sensor_data

    def _sensorThread(self):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            sensor_data = self._getAllSensors()
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)


if __name__ == '__main__':
    dev = Plugin(stream=None, plot=None, event=None)
