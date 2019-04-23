try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
from threading import Thread, Timer
#import Adafruit_DHT
import board
import busio
#import ccs811 as adafruit_ccs811
#import adafruit_dht
try:
    from .bib import ccs811 as adafruit_ccs811
    from .bib import dht22
except:
    from bib import ccs811 as adafruit_ccs811
    from bib import dht22
import os
import json
import traceback
import logging as log
log.basicConfig(level=log.DEBUG)
logging = log.getLogger(__name__)

devicename = "Sensoren"
ACTIVE_SAMPLERATE = 10
PASSIVE_SAMPLERATE = 0.1

#dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)

#DHT_pins = {"A": 24, "B": 23, "C": 27, "D": 17}

DHT_A = dht22.DHTBase(False, board.D24, 10)
DHT_B = dht22.DHTBase(False, board.D23, 10)
DHT_C = dht22.DHTBase(False, board.D27, 10)
DHT_D = dht22.DHTBase(False, board.D17, 10)


_sensorErrors = {
    'A': {'CCS': False, 'DHT': False},
    'B': {'CCS': False, 'DHT': False},
    'C': {'DHT': False},
    'D': {'DHT': False},
}

# Sensor warning ranges
sensorRange = {
    'A': {'CCS': {'Temperatur': [-100, 40], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 300]},
          'DHT': {'Temperatur': [-100, 40], 'Feuchtigkeit': [5, 80]}},
    'B': {'CCS': {'Temperatur': [-100, 40], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 300]},
          'DHT': {'Temperatur': [-100, 40], 'Feuchtigkeit': [5, 80]}},
    'C': {'DHT': {'Temperatur': [-100, 40], 'Feuchtigkeit': [5, 80]}},
    'D': {'DHT': {'Temperatur': [-100, 40], 'Feuchtigkeit': [5, 80]}},
    'Bedienelement': {'Intern': {'CPU-Temperatur': [0, 60]}},
}

_sensorRangeHit = {
    'A': {'CCS': {'Temperatur': False, 'CO2-Gehalt': False, 'TVOC-Gehalt': False},
          'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
    'B': {'CCS': {'Temperatur': False, 'CO2-Gehalt': False, 'TVOC-Gehalt': False},
          'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
    'C': {'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
    'D': {'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
    'Bedienelement': {'Intern': {'CPU-Temperatur': False}},
}

# Sensor calibration offsets
sensorCalib = {
    'A': {'CCS': {'Temperatur': 0, 'CO2-Gehalt': 0, 'TVOC-Gehalt': 0},
          'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
    'B': {'CCS': {'Temperatur': 0, 'CO2-Gehalt': 0, 'TVOC-Gehalt': 0},
          'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
    'C': {'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
    'D': {'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
    'Bedienelement': {'Intern': {'CPU-Temperatur': 0}},
}


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = ACTIVE_SAMPLERATE

        try:
            self.ccs2 = adafruit_ccs811.CCS811(i2c)
        except:
            logging.error('ERROR CCS Sensor Messstelle B')
            logging.debug(traceback.format_exc())
            self.ccs2 = None
        try:
            self.ccs1 = adafruit_ccs811.CCS811(i2c, 0x5B)
        except:
            logging.error('ERROR CCS Sensor Messstelle A')
            logging.debug(traceback.format_exc())
            self.ccs1 = None

        # Sensor error flags
        self._sensorErrors = _sensorErrors
        self._sensorRangeHit = _sensorRangeHit
        self._rangeNoiseLevel = 0.05  # %
        self.loadConfig()

        self._logging = False
        self.waiter = Timer(60, self._enableLogging)
        self.waiter.start()

        self._thread = Thread(target=self._sensorThread)
        self._thread.start()

        self._displayThread = Thread(target=self._checkDisplayThread)
        self._displayThread.start()

        self._sensor_data = {
            'A': {'Temperatur': [None, '°C'], 'CO2-Gehalt': [None, 'ppm'], 'TVOC-Gehalt': [None, 'ppm'], 'Temperatur2': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'B': {'Temperatur': [None, '°C'], 'CO2-Gehalt': [None, 'ppm'], 'TVOC-Gehalt': [None, 'ppm'], 'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'C': {'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'D': {'Temperatur': [None, '°C'], 'Feuchtigkeit': [None, '%']},
            'Bedienelement': {'CPU-Temperatur': [None, '°C']},
        }

    def _waitForSensors(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        try:
            if self.ccs1 is not None:
                while not self.ccs1.data_ready:
                    pass
                temp = self.ccs1.temperature
                self.ccs1.temp_offset = temp - 25.0

            if self.ccs2 is not None:
                while not self.ccs2.data_ready:
                    pass
                temp2 = self.ccs2.temperature
                self.ccs2.temp_offset = temp2 - 25.0
        except:
            logging.debug(traceback.format_exc())

    def saveConfig(self):
        packagedir = self.getDir(__file__)
        config = {}
        config['sensorCalib'] = self.sensorCalib
        config['sensorRange'] = self.sensorRange
        with open(packagedir+"/config.json", 'w', encoding="utf-8") as fp:
            json.dump(config, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def loadConfig(self):
        packagedir = self.getDir(__file__)
        if os.path.exists(packagedir+"/config.json"):
            try:
                with open(packagedir+"/config.json", encoding="UTF-8") as jsonfile:
                    config = json.load(jsonfile, encoding="UTF-8")

                self.sensorCalib = config['sensorCalib']
                self.sensorRange = config['sensorRange']
            except:
                logging.error('Error loading config')
                self.sensorCalib = sensorCalib
                self.sensorRange = sensorRange
        else:
            logging.error('No config-file found.')
            self.sensorCalib = sensorCalib
            self.sensorRange = sensorRange

    def calibrateTemperature(self):
        self._calibrate('Temperatur')

    def calibrateHumidity(self):
        self._calibrate('Feuchtigkeit')

    def calibrateCO2(self):
        self._calibrate('CO2-Gehalt')

    def _calibrate(self, signal):
        sensor_data = self._getAllSensors(False)
        count = 0
        sum = 0
        for dev in sensor_data.keys():
            if signal in sensor_data[dev].keys():
                sum += sensor_data[dev][signal][0]
                count += 1
        if count != 0:
            mean = sum/count

        for dev in self.sensorCalib.keys():
            for sensor in self.sensorCalib[dev].keys():
                if signal in self.sensorCalib[dev][sensor].keys():
                    self.sensorCalib[dev][sensor][signal] = mean-sensor_data[dev][signal][0]

        self.saveConfig()

    def _processSensor(self, messstelle, sensor, signal, value):
        if signal == 'Temperatur':
            name = 'Temperatur'
            u = '°C'
        elif signal == 'Feuchtigkeit':
            name = 'Feuchtigkeit'
            u = '%'
        elif signal == 'CO2-Gehalt':
            name = 'CO2-Gehalt'
            u = 'ppm'
        elif signal == 'TVOC-Gehalt':
            name = 'TVOC-Gehalt'
            u = 'ppm'
        else:
            name = '?'
            u = '?'
        value += self.sensorCalib[messstelle][sensor][signal]
        fallback = self._rangeNoiseLevel*value
        old = self._sensorRangeHit[messstelle][sensor][signal]
        if self._logging:
            if value > self.sensorRange[messstelle][sensor][signal][1] and not old:
                self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value))+u+' zu hoch!',
                           sname=name, dname=messstelle.upper(), priority=1)
                self._sensorRangeHit[messstelle][sensor][signal] = True
            elif value < self.sensorRange[messstelle][sensor][signal][0] and not old:
                self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value))+u+' zu niedrig!',
                           sname=name, dname=messstelle.upper(), priority=1)
                self._sensorRangeHit[messstelle][sensor][signal] = True
            elif old and value >= self.sensorRange[messstelle][sensor][signal][0]+fallback and value <= self.sensorRange[messstelle][sensor][signal][1]-fallback:
                self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value)) + u+' wieder in gutem Bereich!',
                           sname=name, dname=messstelle.upper(), priority=0)
                self._sensorRangeHit[messstelle][sensor][signal] = False
        return value

    def _sensorErrorEvent(self, messstelle, sensor, value=True):
        old = self._sensorErrors[messstelle][sensor]
        if value is not old:
            self._sensorErrors[messstelle][sensor] = value
            if value:
                self.event('Sensorfehler ('+sensor.upper()+') an Messstelle ' +
                           messstelle.upper()+'!',
                           sname=sensor, dname=messstelle.upper(), priority=1)
            else:
                self.event('Sensorfehler ('+sensor.upper()+') an Messstelle '+messstelle.upper() +
                           ' behoben!',
                           sname=sensor, dname=messstelle.upper(), priority=0)

    def _getAllSensors(self, processed=True):
        # aHumid, aTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['A'], 1, 0)
        # bHumid, bTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['B'], 1, 0)
        # cHumid, cTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['C'], 1, 0)
        # dHumid, dTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['D'], 1, 0)

        # aHumid, aTemp = 0,0
        # bHumid, bTemp = 0,0
        # cHumid, cTemp = 0,0
        # dHumid, dTemp = 0,0
        aHumid, aTemp = self.trySensorRead(
            DHT_A, "A", "DHT", "Feuchtigkeit", "Temperatur", True, 100)
        bHumid, bTemp = self.trySensorRead(
            DHT_B, "B", "DHT", "Feuchtigkeit", "Temperatur", True, 100)
        cHumid, cTemp = self.trySensorRead(
            DHT_C, "C", "DHT", "Feuchtigkeit", "Temperatur", True, 100)
        dHumid, dTemp = self.trySensorRead(
            DHT_D, "D", "DHT", "Feuchtigkeit", "Temperatur", True, 100)

        rpiTemp = self._get_cpu_temperature()
        rpiTemp = self._processSensor('Bedienelement', 'Intern', 'CPU-Temperatur', rpiTemp)

        if self.ccs1 == None:
            try:
                self.ccs1 = adafruit_ccs811.CCS811(i2c, 0x5B)
                self._waitForSensors()
            except:
                self.ccs1 = None
        if self.ccs2 == None:
            try:
                self.ccs2 = adafruit_ccs811.CCS811(i2c)
                self._waitForSensors()
            except:
                self.ccs2 = None
        try:
            #ccs1.set_environmental_data(aHumid, aTemp)
            co2_a = self.ccs1.eco2
            tvoc_a = self.ccs1.tvoc
            if processed:
                co2_a = self._processSensor('A', 'CCS', 'CO2-Gehalt', co2_a)
                tvoc_a = self._processSensor('A', 'CCS', 'TVOC-Gehalt', tvoc_a)
                self._sensorErrorEvent('A', 'CCS', False)
        except:
            co2_a = self._sensor_data["A"]['CO2-Gehalt'][0]
            tvoc_a = self._sensor_data['A']['TVOC-Gehalt'][0]
            #self._sensorErrorEvent('A', 'CCS', True)
            logging.debug(traceback.format_exc())
        try:
            #ccs2.set_environmental_data(bHumid, bTemp)
            co2_b = self.ccs2.eco2
            tvoc_b = self.ccs2.tvoc
            if processed:
                co2_b = self._processSensor('B', 'CCS', 'CO2-Gehalt', co2_b)
                tvoc_b = self._processSensor('B', 'CCS', 'TVOC-Gehalt', tvoc_b)
                self._sensorErrorEvent('B', 'CCS', False)
        except:
            co2_b = self._sensor_data["B"]['CO2-Gehalt'][0]
            tvoc_b = self._sensor_data['B']['TVOC-Gehalt'][0]
            #self._sensorErrorEvent('B', 'CCS', True)
            logging.debug(traceback.format_exc())

        self._sensor_data = {
            'A': {'Temperatur': [aTemp, '°C'], 'CO2-Gehalt': [co2_a, 'ppm'], 'TVOC-Gehalt': [tvoc_a, 'ppm'], 'Temperatur2': [aTemp, '°C'], 'Feuchtigkeit': [aHumid, '%']},
            'B': {'Temperatur': [bTemp, '°C'], 'CO2-Gehalt': [co2_b, 'ppm'], 'TVOC-Gehalt': [tvoc_b, 'ppm'], 'Temperatur': [bTemp, '°C'], 'Feuchtigkeit': [bHumid, '%']},
            'C': {'Temperatur': [cTemp, '°C'], 'Feuchtigkeit': [cHumid, '%']},
            'D': {'Temperatur': [dTemp, '°C'], 'Feuchtigkeit': [dHumid, '%']},
            'Bedienelement': {'CPU-Temperatur': [rpiTemp, '°C']},
        }

        return self._sensor_data

    def trySensorRead(self, value1, messtelle, sensor, signal, signal2, processed=True, gain=1):
        try:
            #ccs1.set_environmental_data(aHumid, aTemp)
            # a = value1.humidity
            # b = value1.temperature
            b, a = value1.temperature_humidity
            if processed:
                a = self._processSensor(messtelle, sensor, signal, a)
                b = self._processSensor(messtelle, sensor, signal2, b)
            self._sensorErrorEvent(messtelle, sensor, False)
        except:
            a = self._sensor_data[messtelle][signal][0]
            b = self._sensor_data[messtelle][signal2][0]
            #self._sensorErrorEvent(messtelle, sensor, True)
            logging.debug(traceback.format_exc())
        return a, b

    def _sensorThread(self):
        self._waitForSensors()
        time.sleep(2)
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            sensor_data = self._getAllSensors()
            if self._logging:
                self.stream(list=sensor_data)
            diff = (time.time() - start_time)

    def _get_cpu_temperature(self):
        tFile = open('/sys/class/thermal/thermal_zone0/temp')
        temp = float(tFile.read())
        tempC = temp/1000
        return tempC

    def _enableLogging(self):
        self._logging = True

    def _checkDisplayThread(self):
        while self.run:
            with open("/sys/class/backlight/rpi_backlight/bl_power", "r") as f:
                text = f.read()
            state = bool(text)
            logging.debug(state)
            if state:
                self.samplerate = PASSIVE_SAMPLERATE
            else:
                self.samplerate = ACTIVE_SAMPLERATE
            time.sleep(0.2)

if __name__ == '__main__':
    dev = Plugin(stream=None, plot=None, event=None)
