try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
import requests
from PyQt5 import uic
from PyQt5 import QtWidgets

devicename = "Heliotherm"

#HOST = "192.168.178.72"
HOST = "192.168.2.104"

#from pymodbus3.client.sync import ModbusTcpClient
from pyModbusTCP.client import ModbusClient
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

############################# DO NOT EDIT FROM HERE ################################################

mappingWrite = [
[100, 'Betriebsart', 1, '', False],
[101, 'HKR Soll_Raum', 10, '°C', False],
[102, 'HKR Soll', 10, '°C', False],
[103, 'HKR Soll aktiv', 1, '', False],
[104, 'RLT min Kuehlen', 10, '°C', False],
[105, 'WW Normaltemperatur', 10, '°C', False],
[106, 'WW Minimaltemperatur', 10, '°C', False],
[107, 'MKR1 Betriebsart', 1, '', False],
[108, 'MKR1 Soll_Raum', 10, '°C', False],
[109, 'MKR1 Soll', 10, '°C', False],
[110, 'MKR1 Soll aktiv', 1, '', False],
[111, 'MKR1 Kuehlen RLT min.', 10, '°C', False],
[112, 'MKR2 Betriebsart', 1, '', False],
[113, 'MKR2 Soll_Raum', 10, '°C', False],
[114, 'MKR2 Soll', 10, '°C', False],
[115, 'MKR2 Soll aktiv', 1, '', False],
[116, 'MKR2 Kuehlen RLT min.', 10, '°C', False],
[117, 'PV Anf', 1, '', False],
[118, 'Unbekannt', 1, '', False],
[119, 'Unbekannt', 1, '', False],
[120, 'Unbekannt', 1, '', False],
[121, 'Unbekannt', 1, '', False],
[122, 'Unbekannt', 1, '', False],
[123, 'Unbekannt', 1, '', False],
[124, 'Unbekannt', 1, '', False],
[125, 'Leistungsaufnahmevorgabe', 1, 'W', False],
[126, 'Verdichterdrehzahlvorgabe', 1, '%°', False],
[127, 'Ext Anf', 1, '', False],
[128, 'Entstoeren', 1, '', False],
[129, 'Aussentemperatur Wert', 10, '°C', False],
[130, 'Aussentemperatur aktiv', 1, '', False],
[131, 'Puffertemperatur Wert', 10, '°C', False],
[132, 'Puffertemperatur aktiv', 1, '', False],
[133, 'Brauchwassertemperatur Wert', 10, '°C', False],
[134, 'Brauchwassertemperatur aktiv', 1, '', False],
[135, 'Unbekannt', 10, '°C', False],
[136, 'Unbekannt', 10, '°C', False],
[137, 'Unbekannt', 10, '°C', False],
[138, 'Unbekannt', 10, '°C', False],
[139, 'Unbekannt', 10, '°C', False],
[140, 'Unbekannt', 10, '°C', False],
[141, 'Unbekannt', 10, '°C', False],
[142, 'Unbekannt', 10, '°C', False],
[143, 'Unbekannt', 10, '°C', False],
[144, 'Unbekannt', 10, '°C', False],
[145, 'Unbekannt', 10, '°C', False],
[146, 'Unbekannt', 10, '°C', False],
]

mappingRead = [
[10, 'Temperatur Aussen', 10, '°C', False],
[11, 'Temperatur Brauchwasser', 10, '°C', False],
[12, 'Temperatur Vorlauf', 10, '°C', False],
[13, 'Temperatur Ruecklauf', 10, '°C', False],
[14, 'Temperatur Pufferspeicher', 10, '°C', False],
[15, 'Temperatur EQ_Eintritt', 10, '°C', True],
[16, 'Temperatur EQ_Austritt', 10, '°C', True],
[17, 'Temperatur Sauggas', 10, '°C', False],
[18, 'Temperatur Verdampfung', 10, '°C', True],
[19, 'Temperatur Kondensation', 10, '°C', False],
[20, 'Temperatur Heissgas', 10, '°C', False],
[21, 'Niederdruck', 10, 'Bar', False],
[22, 'Hochdruck', 10, 'Bar', False],
[23, 'Heizkreispumpe', 1, '', False],
[24, 'Pufferladepumpe', 1, '', False],
[25, 'Verdichter', 1, '', False],
[26, 'Stoerung', 1, '', False],
[27, 'Vierwegeventil Luft', 1, '', False],
[28, 'WMZ_Durchfluss', 10, 'l/min', False],
[29, 'n-Soll Verdichter', 1, '%°', False],
[30, 'COP', 10, '', False],
[31, 'Temperatur Frischwasser', 10, '°C', False],
[32, 'EVU Sperre', 1, '', False],
[33, 'Aussentemperatur verzoegert', 10, '°C', False],
[34, 'HKR verzoegert', 10, '°C', False],
[35, 'MKR1_Solltemperatur', 10, '°C', False],
[36, 'MKR2_Solltemperatur', 10, '°C', False],
[37, 'EQ-Ventilator', 1, '', False],
[38, 'WW-Vorrat', 1, '', False],
[39, 'Kühlen UMV passiv', 1, '', False],
[40, 'Expansionsventil', 1, '%°', False],
[41, 'Verdichteranforderung', 1, '', False],
[42, 'Betriebsstunden im WW-Betrieb', 1, 'h', False],
[43, 'Unbekannt', 1, '', False],
[44, 'Betriebsstunden im HZG-Betrieb', 1, 'h', False],
[45, 'Unbekannt', 1, '', False],
[46, 'Unbekannt', 1, '', False],
[47, 'Unbekannt', 1, '', False],
[48, 'Unbekannt', 1, '', False],
[49, 'Unbekannt', 1, '', False],
[50, 'Unbekannt', 1, '', False],
[51, 'Unbekannt', 1, '', False],
[52, 'Unbekannt', 1, '', False],
[53, 'Unbekannt', 1, '', False],
[54, 'Unbekannt', 1, '', False],
[55, 'Unbekannt', 1, '', False],
[56, 'Unbekannt', 1, '', False],
[57, 'Unbekannt', 1, '', False],
[58, 'Unbekannt', 1, '', False],
[59, 'Unbekannt', 1, '', False],
[60, 'WMZ_Heizung', 1, 'kW/h', False],
[61, 'Unbekannt', 1, '', False],
[62, 'Stromz_Heizung', 1, 'kW/h', False],
[63, 'Unbekannt', 1, '', False],
[64, 'WMZ_Brauchwasser', 1, 'kW/h', False],
[65, 'Unbekannt', 1, '', False],
[66, 'Stromz_Brauchwasser', 1, 'kW/h', False],
[67, 'Unbekannt', 1, '', False],
[68, 'Stromz_Gesamt', 1, 'kW/h', False],
[69, 'Unbekannt', 1, '', False],
[70, 'Stromz_Leistung', 1, 'W', False],
[71, 'Unbekannt', 1, '', False],
[72, 'WMZ_Gesamt', 1, 'kW/h', False],
[73, 'Unbekannt', 1, '', False],
[74, 'WMZ_Leistung', 1, 'kW', False],
[75, 'Unbekannt', 1, '', False],

]

class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot= None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(devicename)
        self.smallGUI = True

        # Data-logger thread

        self.setPerpetualTimer(self._updateT, samplerate=0.2)
        # self.updater.start()

        self.__base_address = ""
        self.__s = requests.Session()

        self._error = False
        self._start(HOST)

    # THIS IS YOUR THREAD
    def _updateT(self):
        y, name, units = self._helio_get()
        if y is not None:

            self.stream(y=y, snames=name, unit=units)
            if self._error == True:
                self.event('Wärmepumpe: Werte werden wieder empfangen', sname="Status", dname=devicename, priority=0)
                self._error = False
        elif self._error == False:
            self._error = True
            self.event('Wärmepumpe: Messwerte können nicht empfangen werden', sname="Status", dname=devicename, priority=1)

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Heliotherm/heliotherm.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateSpinBox.valueChanged.connect(self.__changeSamplerate)
        self.widget.comboBox.setCurrentText(HOST)
        self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        if self.run:
            self.cancel()
            self.widget.pushButton.setText("Verbinden")
            self.__base_address = ""
        else:
            address = self.widget.comboBox.currentText()
            self.__base_address = address
            self.c = ModbusClient(host=self.__base_address, port=502, auto_open=True, auto_close=True)
            self.c.timeout(10)
            #self._helio_get()
            self.start()
            self.widget.pushButton.setText("Beenden")

    def _start(self, address):
        if self.run:
            self.cancel()
            self.__base_address = ""
        else:
            self.__base_address = address
            self.c = ModbusClient(host=self.__base_address, port=502, auto_open=True, auto_close=True)
            self.c.timeout(10)
            #self._helio_get()
            self.start()

    def _helio_set(self, reg, value):
        pass
        #self.c.write_single_register(reg_addr,reg_value)
        #self.c.write_multiple_registers
    def _helio_get(self):
        #client = ModbusTcpClient(self.__base_address)
        #client.write_coil(1, True)
        #result = client.read_coils(0,1)
        resultWrite = self.c.read_holding_registers(100, 47)
        resultRead = self.c.read_input_registers(10,65)
        if resultRead is not None:
            for idx, d in enumerate(resultRead):
                if d>=2 **16/2:
                    resultRead[idx] = 2 **16 - d
            for idx, d in enumerate(resultWrite):
                if d>=2 **16/2:
                    resultWrite[idx] = 2 **16 - d
            if resultWrite is not None and resultRead is not None:
                y = []
                units = []
                snames = []
                for idx, value in enumerate(resultWrite):
                    if mappingWrite[idx][1]=='Unbekannt' or mappingWrite[idx][4]==False:
                        #mappingWrite[idx][1] = str(mappingWrite[idx][0])
                        pass
                    else:
                        snames.append(mappingWrite[idx][1])
                        y.append(resultWrite[idx]/mappingWrite[idx][2])
                        units.append(mappingWrite[idx][3])
                for idx, value in enumerate(resultRead):
                    if mappingRead[idx][1]=='Unbekannt' or mappingRead[idx][4]==False:
                        #mappingRead[idx][1] = str(mappingRead[idx][0])
                        pass
                    else:
                        snames.append(mappingRead[idx][1])
                        y.append(resultRead[idx]/mappingRead[idx][2])
                        units.append(mappingRead[idx][3])
                return y, snames, units
            else:
                self.widget.pushButton.setText("Fehler")
                return None, None, None
        else:
            logging.error('Could not read registers.')
            return None, None, None

    def __changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
