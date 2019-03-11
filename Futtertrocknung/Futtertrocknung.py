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

devicename = "Futtertrocknung"

dht22 = Adafruit_DHT.DHT22
# css811: sudo nano /boot/config.txt for i2c baudrate
i2c = busio.I2C(board.SCL, board.SDA)
ccs1 = adafruit_ccs811.CCS811(i2c)
ccs2 = adafruit_ccs811.CCS811(i2c, 0x5B)
DHT_pins = {"A":24,"B":23,"C":27,"D":17}

class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)

        self.run = True
        self.samplerate = 1

        ccsat = Thread(target=self.getCCSAData)
        ccsat.start()
        ccsbt = Thread(target=self.getCCSBData)
        ccsbt.start()

        dht22_a = Thread(target=self.getDHT22,args=(DHT_pins["A"],'aTemp', 'aHumid'))
        dht22_a.start()
        dht22_b = Thread(target=self.getDHT22,args=(DHT_pins["B"],'bTemp', 'bHumid'))
        dht22_b.start()
        dht22_c = Thread(target=self.getDHT22,args=(DHT_pins["C"],'cTemp', 'cHumid'))
        dht22_c.start()
        dht22_d = Thread(target=self.getDHT22,args=(DHT_pins["D"],'dTemp', 'dHumid'))
        dht22_d.start()

    def getCCSAData(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs1.data_ready:
            pass
        temp = ccs1.temperature
        ccs1.temp_offset = temp - 25.0

        while self.run:
            time.sleep(1/self.samplerate)
            try:
                self.stream([ccs1.eco2,ccs1.tvoc],  ['aCO2', 'aTVOC'], ['ppm','ppm'])
                if self.data[0]>2000:
                    print('event')
                    self.event('CO2 Gehalt hoch', sname="CO2", dname="Futtertrocknung", priority=2)
            except:
                print("Error reading CCS811 A")

    def getCCSBData(self):
        # Wait for the sensor to be ready and calibrate the thermistor
        while not ccs2.data_ready:
            pass
        temp = ccs2.temperature
        ccs2.temp_offset = temp - 25.0

        while self.run:
            time.sleep(1/self.samplerate)
            try:
                self.stream([ccs2.eco2,ccs2.tvoc],  ['bCO2', 'bTVOC'], ['ppm','ppm'])
            except:
                print("Error reading CCS811 B")

    def getDHT22(self, pin, tName, hName):
        while self.run:
            time.sleep(1/self.samplerate)
            humidity, temperature = Adafruit_DHT.read_retry(dht22, pin)
            self.stream([temperature,humidity],  [tName, hName], ['°C','%'])

    def getControllerData(self):
        self.data['fanVelocity'] = '?'
        self.data['fanMode'] = "Druck"
        self.data['active'] = False
        self.data['fan2heuPressure'] = '?'
        self.data['fan2heuVelocity'] = '?'
        self.data['fan2heuPressureDes'] = 0
        self.data['fan2heuVelocityDes'] = 0
        self.data['fanManualDes'] = 0

    def setActive(self, active = True):
        pass

    def setMode(self, mode = 0): # manuell, druck, durchfluss
        pass

    def setDesired(self, mode, value):
        pass
