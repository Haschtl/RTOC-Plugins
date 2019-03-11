try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin

import time
from threading import Thread
import Adafruit_DHT
import time
import board
import busio
import adafruit_ccs811
from subprocess import PIPE, Popen

devicename = "Futtertrocknung"

dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)
ccs2 = adafruit_ccs811.CCS811(i2c)
ccs1 = adafruit_ccs811.CCS811(i2c, 0x5B)
DHT_pins = {"A":24,"B":23,"C":27,"D":17}

class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        self._aCCS_Error = False
        self._bCCS_Error = False
        self._aDHT_Error = False
        self._bDHT_Error = False
        self._cDHT_Error = False
        self._dDHT_Error = False

        self.reglerModus = "Druck"
        self.reglerActiv = False
        self.potiEnabled = False
        self.fehler = []
        self.pressure_P = 0
        self.pressure_I = 0
        self.pressure_D = 0
        self.flow_P = 0
        self.flow_I = 0
        self.flow_D = 0
        self.pressureRange = [0,10]
        self.flowRange = [0,10]

        ccsT = Thread(target=self._getCCSData)
        ccsT.start()
        #ccsbt = Thread(target=self._getCCSBData)
        #ccsbt.start()

        dht22_a = Thread(target=self._getDHT22,args=(DHT_pins["A"],'aTemp', 'aHumid', self._aDHT_Error))
        dht22_a.start()
        dht22_b = Thread(target=self._getDHT22,args=(DHT_pins["B"],'bTemp', 'bHumid', self._bDHT_Error))
        dht22_b.start()
        dht22_c = Thread(target=self._getDHT22,args=(DHT_pins["C"],'cTemp', 'cHumid', self._cDHT_Error))
        dht22_c.start()
        dht22_d = Thread(target=self._getDHT22,args=(DHT_pins["D"],'dTemp', 'dHumid', self._dDHT_Error))
        dht22_d.start()

        controllerT = Thread(target = self._getControllerData)
        controllerT.start()

    def _getCCSData(self):
        diff = 0
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs1.data_ready:
            pass
        temp = ccs1.temperature
        ccs1.temp_offset = temp - 25.0

        temp2 = ccs2.temperature
        ccs2.temp_offset = temp2 - 25.0

        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            try:
                self.stream([ccs1.eco2,ccs1.tvoc],  ['aCO2', 'aTVOC'], dname=devicename, unit = ['ppm','ppm'])
                if ccs1.eco2>2000:
                    print('event')
                    self.event('CO2 Gehalt hoch', sname="aCO2", dname="Futtertrocknung", priority=1)
                if self._aCCS_Error:
                    self._aCCS_Error = False
                    self.event('CCS811 A: Sensorfehler wurde behoben', sname="aCO2", dname="Futtertrocknung", priority=0)
                    print("CCS811 A Error fixed")
            except:
                if not self._aCCS_Error:
                    self._aCCS_Error = True
                    self.event('CCS811 A: Sensorfehler!', sname="aCO2", dname="Futtertrocknung", priority=1)
                print("Error reading CCS811 A")
            try:
                self.stream([ccs2.eco2,ccs2.tvoc],  ['bCO2', 'bTVOC'], dname=devicename, unit = ['ppm','ppm'])
                if self._bCCS_Error:
                    self._bCCS_Error = False
                    self.event('CCS811 B: Sensorfehler wurde behoben', sname="bCO2", dname="Futtertrocknung", priority=0)
                    print("CCS811 B Error fixed")
            except:
                if not self._bCCS_Error:
                    self._bCCS_Error = True
                    self.event('CCS811 B: Sensorfehler!', sname="bCO2", dname="Futtertrocknung", priority=1)
                print("Error reading CCS811 B")
            diff = (time.time() - start_time)

    def _getCCSBData(self):
        diff = 0
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs2.data_ready:
            pass
        temp = ccs2.temperature
        ccs2.temp_offset = temp - 25.0

        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            try:
                self.stream([ccs2.eco2,ccs2.tvoc],  ['bCO2', 'bTVOC'], dname=devicename, unit = ['ppm','ppm'])
                if self._bCCS_Error:
                    self._bCCS_Error = False
                    self.event('CCS811 B: Sensorfehler wurde behoben', sname="bCO2", dname="Futtertrocknung", priority=0)
                    print("CCS811 B Error fixed")
            except:
                if not self._bCCS_Error:
                    self._bCCS_Error = True
                    self.event('CCS811 B: Sensorfehler!', sname="bCO2", dname="Futtertrocknung", priority=1)
                print("Error reading CCS811 B")
            diff = (time.time() - start_time)

    def _getDHT22(self, pin, tName, hName, error):
        diff = 0
        while self.run:
            if diff < 1/self.samplerate:
                time.sleep(1/self.samplerate-diff)
            start_time = time.time()
            humidity, temperature = Adafruit_DHT.read_retry(dht22, pin)
            if humidity != None and temperature != None:
                self.stream([temperature,humidity],  [tName, hName], dname=devicename, unit = ['°C','%'])
                if error:
                    error = False
                    self.event('DHT22 '+tName+': Sensorfehler wurde behoben', sname=tName, dname="Futtertrocknung", priority=0)
            else:
                if not error:
                    error = True
                    self.event('DHT22 '+tName+': Sensorfehler!', sname=tName, dname="Futtertrocknung", priority=1)
                print('Cannot read DHT22, Pin '+str(pin))
            diff = (time.time() - start_time)

    def _getControllerData(self):
        self.reglerModus = "Druck"
        self.reglerActiv = False
        self.potiEnabled = False
        self.fehler = []
        self.pressure_P = 0
        self.pressure_I = 0
        self.pressure_D = 0
        self.flow_P = 0
        self.flow_I = 0
        self.flow_D = 0
        self.pressureRange = [0,10]
        self.flowRange = [0,10]



        eFrequency = 0
        ePressure = 0
        eFlow = 0
        pressureDesired = 0
        flowDesired = 0
        frequencyDesired = 0

        rpiTemp = self._get_cpu_temperature()
        # Stream all measurements
        self.stream([eFrequency,ePressure,eFlow, pressureDesired, flowDesired, frequencyDesired, rpiTemp],  ['eFrequency','ePressure','eFlow', 'pressureDesired', 'flowDesired', 'frequencyDesired', 'CPU'], dname=devicename, unit = ['U/min','bar','m³/min','bar','m³/min','U/min','°C'])

    def _get_cpu_temperature(self):
        """get cpu temperature using vcgencmd"""
        process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
        output, _error = process.communicate()
        return float(output[output.index('=') + 1:output.rindex("'")])

    def setActive(self, active = True):
        pass

    def setMode(self, mode = 0): # manuell, druck, durchfluss
        pass

    def setPID(self, mode, p,i,d):
        pass

    def setDesired(self, mode, value):
        pass
