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

devicename = "Futtertrocknung"

dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)
ccs2 = adafruit_ccs811.CCS811(i2c)
ccs1 = adafruit_ccs811.CCS811(i2c, 0x5B)
DHT_pins = {"A": 24, "B": 23, "C": 27, "D": 17}


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        # Sensor error flags
        self._sensorErrors = {
            'A': {'CCS': False, 'DHT': False},
            'B': {'CCS': False, 'DHT': False},
            'C': {'DHT': False},
            'D': {'DHT': False},
        }

        # Sensor warning ranges
        self.sensorRange = {
            'A': {'CCS': {'Temperatur': [0, 1000], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 1000]},
                  'DHT': {'Temperatur': [0, 1000], 'Feuchtigkeit': [0, 1000]}},
            'B': {'CCS': {'Temperatur': [0, 1000], 'CO2-Gehalt': [0, 1000], 'TVOC-Gehalt': [0, 1000]},
                  'DHT': {'Temperatur': [0, 1000], 'Feuchtigkeit': [0, 1000]}},
            'C': {'DHT': {'Temperatur': [0, 1000], 'Feuchtigkeit': [0, 1000]}},
            'D': {'DHT': {'Temperatur': [0, 1000], 'Feuchtigkeit': [0, 1000]}},
        }

        self._sensorRangeHit = {
            'A': {'CCS': {'Temperatur': False, 'CO2-Gehalt': False, 'TVOC-Gehalt': False},
                  'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
            'B': {'CCS': {'Temperatur': False, 'CO2-Gehalt': False, 'TVOC-Gehalt': False},
                  'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
            'C': {'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
            'D': {'DHT': {'Temperatur': False, 'Feuchtigkeit': False}},
        }

        # Sensor calibration offsets
        self.sensorCalib = {
            'A': {'CCS': {'Temperatur': 0, 'CO2-Gehalt': 0, 'TVOC-Gehalt': 0},
                  'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
            'B': {'CCS': {'Temperatur': 0, 'CO2-Gehalt': 0, 'TVOC-Gehalt': 0},
                  'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
            'C': {'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
            'D': {'DHT': {'Temperatur': 0, 'Feuchtigkeit': 0}},
        }

        # Controller sachen
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
        pass

    def loadConfig(self):
        pass

    def calibrateTemperature(self):
        self._calibrate('Temperatur')

    def calibrateHumidity(self):
        self._calibrate('Feuchtigkeit')

    def calibrateCO2(self):
        self._calibrate('CO2-Gehalt')

    def _calibrate(self, signal):
        sensor_data = self._getAllSensors()
        count = 0
        sum = 0
        for dev in sensor_data.keys():
            if signal in sensor_data[dev].keys():
                sum += sensor_data[dev][signal]
                count += 1
        if count != 0:
            mean = sum/count

        for dev in self.sensorCalib.keys():
            for sensor in self.sensorCalib[dev].keys():
                if signal in self.sensorCalib[dev][sensor].keys():
                    self.sensorCalib[dev][sensor][signal] = mean-sensor_data[dev][signal]

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

    def _getAllSensors(self):
        try:
            co2_a = ccs1.eco2
            tvoc_a = ccs1.tvoc
            co2_a = self._processSensor('A', 'CCS', 'CO2-Gehalt', co2_a)
            tvoc_a = self._processSensor('A', 'CCS', 'TVOC-Gehalt', tvoc_a)
            self._sendErrorEvent('A', 'CCS', False)
        except:
            self._sendErrorEvent('A', 'CCS', True)
        try:
            co2_b = ccs2.eco2
            tvoc_b = ccs2.tvoc
            co2_b = self._processSensor('B', 'CCS', 'CO2-Gehalt', co2_b)
            tvoc_b = self._processSensor('B', 'CCS', 'TVOC-Gehalt', tvoc_b)
            self._sendErrorEvent('B', 'CCS', False)
        except:
            self._sendErrorEvent('B', 'CCS', True)

        aHumid, aTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['A'], 10, 0)
        bHumid, bTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['B'], 10, 0)
        cHumid, cTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['C'], 10, 0)
        dHumid, dTemp = Adafruit_DHT.read_retry(dht22, DHT_pins['D'], 10, 0)

        aHumid = self._processSensor('A', 'DHT', 'Feuchtigkeit', aHumid)
        aTemp = self._processSensor('A', 'DHT', 'Temperatur', aTemp)
        bHumid = self._processSensor('B', 'DHT', 'Feuchtigkeit', bHumid)
        bTemp = self._processSensor('B', 'DHT', 'Temperatur', bTemp)
        cHumid = self._processSensor('C', 'DHT', 'Feuchtigkeit', cHumid)
        cTemp = self._processSensor('C', 'DHT', 'Temperatur', cTemp)
        dHumid = self._processSensor('D', 'DHT', 'Feuchtigkeit', dHumid)
        dTemp = self._processSensor('D', 'DHT', 'Temperatur', dTemp)

        rpiTemp = self._get_cpu_temperature()

        # sensor_data = [
        #     [co2_b, 'bCO2', 'ppm'],
        #     [tvoc_b, 'bTVOC', 'ppm'],
        #     [aHumid, 'aHumid', '%'],
        #     [aTemp, 'aTemp', '°C'],
        #     [bHumid, 'bHumid', '%'],
        #     [bTemp, 'bTemp', '°C'],
        #     [cHumid, 'cHumid', '%'],
        #     [cTemp, 'cTemp', '°C'],
        #     [dHumid, 'dHumid', '%'],
        #     [dTemp, 'dTemp', '°C'],
        #     [rpiTemp, 'CPU', '°C']
        #     ]

        sensor_data = {
            'A': {'Temperatur': [aTemp, '°C'], 'CO2-Gehalt': [co2_a, 'ppm'], 'TVOC-Gehalt': [tvoc_a, 'ppm'], 'Temperatur2': [aTemp, '°C'], 'Feuchtigkeit': [aHumid, '%']},
            'B': {'Temperatur': [bTemp, '°C'], 'CO2-Gehalt': [co2_b, 'ppm'], 'TVOC-Gehalt': [tvoc_b, 'ppm'], 'Temperatur': [bTemp, '°C'], 'Feuchtigkeit': [bHumid, '%']},
            'C': {'Temperatur': [cTemp, '°C'], 'Feuchtigkeit': [cHumid, '%']},
            'D': {'Temperatur': [dTemp, '°C'], 'Feuchtigkeit': [dHumid, '%']},
            'Bedienelement': {'CPU-Temperatur': [rpiTemp,'°C']},
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

    def _get_cpu_temperature(self):
        tFile = open('/sys/class/thermal/thermal_zone0/temp')
        temp = float(tFile.read())
        tempC = temp/1000
        return tempC

    def setActive(self, active=True):
        pass

    def setMode(self, mode=0):  # manuell, druck, durchfluss
        pass

    def setPID(self, mode, p, i, d):
        pass

    def setDesired(self, mode, value):
        pass
