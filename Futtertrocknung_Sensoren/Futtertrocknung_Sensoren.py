try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import Adafruit_DHT
import board
import busio
import adafruit_ccs811
import os
import json

devicename = "Sensoren"

dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)
ccs2 = adafruit_ccs811.CCS811(i2c)
ccs1 = adafruit_ccs811.CCS811(i2c, 0x5B)
DHT_pins = {"A": 24, "B": 23, "C": 27, "D": 17}

_sensorErrors = {
    'A': {'CCS': False, 'DHT': False},
    'B': {'CCS': False, 'DHT': False},
    'C': {'DHT': False},
    'D': {'DHT': False},
}

# Sensor warning ranges
sensorRange = {
    'A': {'CCS': {'Temperatur': [-100, 40], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 100]},
          'DHT': {'Temperatur': [-100, 40], 'Feuchtigkeit': [5, 80]}},
    'B': {'CCS': {'Temperatur': [-100, 40], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 100]},
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
        self.samplerate = 1

        # Sensor error flags
        self._sensorErrors = _sensorErrors
        self._sensorRangeHit = _sensorRangeHit
        self.loadConfig()

        self.thread = Thread(target=self._sensorThread)
        self.thread.start()

    def _waitForSensors(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs1.data_ready:
            pass
        temp = ccs1.temperature
        ccs1.temp_offset = temp - 25.0
        while not ccs2.data_ready:
            pass
        temp2 = ccs2.temperature
        ccs2.temp_offset = temp2 - 25.0

    def saveConfig(self):
        packagedir = self.getDir(__file__)
        config = {}
        config['sensorCalib'] = self.sensorCalib
        config['sensorRange'] = self.sensorRange
        with open(packagedir+"config.json", 'w', encoding="utf-8") as fp:
            json.dump(config, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def loadConfig(self):
        packagedir = self.getDir(__file__)
        if os.path.exists(packagedir+"/config.json"):
            try:
                with open("config.json", encoding="UTF-8") as jsonfile:
                    config = json.load(jsonfile, encoding="UTF-8")

                self.sensorCalib = config['sensorCalib']
                self.sensorRange = config['sensorRange']
            except:
                print('Error loading config')
                self.sensorCalib = sensorCalib
                self.sensorRange = sensorRange
        else:
            print('No config-file found.')
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
        old = self._sensorRangeHit[messstelle][sensor][signal]
        if value > self.sensorRange[messstelle][sensor][signal][1] and not old:
            self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value))+u+' zu hoch!',
                       sname=sensor, dname=messstelle.upper(), priority=1)
            self._sensorRangeHit[messstelle][sensor][signal] = True
        elif value < self.sensorRange[messstelle][sensor][signal][0] and not old:
            self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value))+u+' zu niedrig!',
                       sname=sensor, dname=messstelle.upper(), priority=1)
        elif old and value >= self.sensorRange[messstelle][sensor][signal][0] and value <= self.sensorRange[messstelle][sensor][signal][1]:
            self.event(name+' an Messstelle '+messstelle.upper()+' ist mit '+str(round(value)) + u+' wieder in gutem Bereich!',
                       sname=sensor, dname=messstelle.upper(), priority=0)
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
        try:
            co2_a = ccs1.eco2
            tvoc_a = ccs1.tvoc
            if processed:
                co2_a = self._processSensor('A', 'CCS', 'CO2-Gehalt', co2_a)
                tvoc_a = self._processSensor('A', 'CCS', 'TVOC-Gehalt', tvoc_a)
                self._sensorErrorEvent('A', 'CCS', False)
        except:
            self._sensorErrorEvent('A', 'CCS', True)
        try:
            co2_b = ccs2.eco2
            tvoc_b = ccs2.tvoc
            if processed:
                co2_b = self._processSensor('B', 'CCS', 'CO2-Gehalt', co2_b)
                tvoc_b = self._processSensor('B', 'CCS', 'TVOC-Gehalt', tvoc_b)
                self._sensorErrorEvent('B', 'CCS', False)
        except:
            self._sensorErrorEvent('B', 'CCS', True)

        aHumid, aTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['A'], 10, 0)
        bHumid, bTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['B'], 10, 0)
        cHumid, cTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['C'], 10, 0)
        dHumid, dTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['D'], 10, 0)

        if processed:
            aHumid = self._processSensor('A', 'DHT', 'Feuchtigkeit', aHumid)
            aTemp = self._processSensor('A', 'DHT', 'Temperatur', aTemp)
            bHumid = self._processSensor('B', 'DHT', 'Feuchtigkeit', bHumid)
            bTemp = self._processSensor('B', 'DHT', 'Temperatur', bTemp)
            cHumid = self._processSensor('C', 'DHT', 'Feuchtigkeit', cHumid)
            cTemp = self._processSensor('C', 'DHT', 'Temperatur', cTemp)
            dHumid = self._processSensor('D', 'DHT', 'Feuchtigkeit', dHumid)
            dTemp = self._processSensor('D', 'DHT', 'Temperatur', dTemp)

        rpiTemp = self._get_cpu_temperature()

        rpiTemp = self._processSensor('Bedienelement', 'Intern', 'CPU-Temperatur', rpiTemp)

        sensor_data = {
            'A': {'Temperatur': [aTemp, '°C'], 'CO2-Gehalt': [co2_a, 'ppm'], 'TVOC-Gehalt': [tvoc_a, 'ppm'], 'Temperatur2': [aTemp, '°C'], 'Feuchtigkeit': [aHumid, '%']},
            'B': {'Temperatur': [bTemp, '°C'], 'CO2-Gehalt': [co2_b, 'ppm'], 'TVOC-Gehalt': [tvoc_b, 'ppm'], 'Temperatur': [bTemp, '°C'], 'Feuchtigkeit': [bHumid, '%']},
            'C': {'Temperatur': [cTemp, '°C'], 'Feuchtigkeit': [cHumid, '%']},
            'D': {'Temperatur': [dTemp, '°C'], 'Feuchtigkeit': [dHumid, '%']},
            'Bedienelement': {'CPU-Temperatur': [rpiTemp, '°C']},
        }
        return sensor_data

    def _sensorThread(self):
        self._waitForSensors()
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            sensor_data = self._getAllSensors()
            self.stream(list=sensor_data)
            diff = (time.time() - start_time)

    def _get_cpu_temperature(self):
        tFile = open('/sys/class/thermal/thermal_zone0/temp')
        temp = float(tFile.read())
        tempC = temp/1000
        return tempC