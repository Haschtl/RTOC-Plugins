try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
from PyQt5 import uic
from PyQt5 import QtWidgets
import json
import logging as log
from pyModbusTCP.client import ModbusClient
# from pymodbus3.client.sync import ModbusTcpClient

# Betriebsarten:
# 0= AUS
# 1= Automatik
# 2= Kühlen
# 3= Sommer
# 4= Dauerbetrieb
# 5= Absenkung
# 6=Urlaub
# 7= Party

# Energiequellen Eintritt Teqe - nicht gefunden
# Energiequellen Austritt Teqa - nicht gefunden
# Verdichterfluss Temperatur - nicht gefunden
# Unterkühlung Temperatur - nicht gefunden
# Energiequellen Pumpe - ist 0
# Warmwasser Vorrang - ist 0
# Carterheizung - ist 0
# Kuehlen UmV Passiv - ist 0
# Pumpe Warmwasser - ist 0
# Mod Status - ist 0
# BSZ Verdichter Schaltungen - nicht gefunden 672
# DIP_SW - nicht gefunden 29
# AO1 HKP - ist 0
# AO2 Energiequelle - ist 0
# Anforderung 2. Stufe - ist 0
# Frischwasserpumpe - ist 0
# Heissgassollwert - nicht gefunden 45.8
# Druckdifferenz HD_ND - nicht gefunden 4.8
# EQ_Temp.differenz - nicht gefunden 1.1
# VL_RL_Temp.diff. - nicht gefunden -3.2
# Volt L1-N - ist 0
# Volt L2-N - ist 0
# Volt L3-N - ist 0
# Strom L1 - ist 0
# Strom L2 - ist 0
# Strom L3 - ist 0
# Netzfrequenz - ist 0
# WMZ_Temp. Ein - nicht gefunden
# WMZ_Temp. Aus - nicht gefunden
# OpFrequenz - ist 0
# OpVerdichter - ist 0
# Letzter FU Fehler - ist 15
# OpStromabgabe - ist 0
# OpAusgangsspannung - ist 0
# FU Temp - ist 0
# FU Fehler t-1 - ist 15
# FU Fehler t-2 - ist 15
# FU Fehler t-3 - ist 15
# FU Fehler t-4 - ist 15
# FU Fehler t-5 - ist 15
# FU Fehler t-6 - ist 15
# FU Fehler t-7 - ist 15
# FU Fehler t-8 - ist 15
# FU Fehler t-9 - ist 15
# PV-Status - nicht gefunden -5
# PV Energie - ist 0
# WP Energie (calc) - ist 0
# Soll-Dz (calc)  - ist 8284
# DC Spannung - ist 0

# BSZ Verdichter Betriebsstungen WW
# BSZ Verdichter Betriebsstunden HKR
# BSZ Verdichter Betriebsstunden gesamt
# BSZ Abtau Betriebsstunden
# BSZ Abtau Schaltungen
# BSZ Verdichter Schaltungen WW

# 192.168.178.72, 192.168.2.104

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)


class Plugin(LoggerPlugin):
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.loadConfig()
        self.setDeviceName(self._name)
        self.smallGUI = True

        # Data-logger thread
        self._firstStart = True
        self._lastStoerung = False
        self._lastExtAnf = True
        self._lastMode = 0
        # self._error = False
        self._modes = {
            0: 'AUS',
            1: 'Automatik',
            2: 'Kühlen',
            3: 'Sommer',
            4: 'Dauerbetrieb',
            5: 'Absenkung',
            6: 'Urlaub',
            7: 'Party',
        }
        self._base_address = ""

        self.setPerpetualTimer(self._helio_alle)

        self._base_address = self.host
        self._c = ModbusClient(host=self._base_address, port=self.port, auto_open=True, auto_close=True)
        self._c.timeout(10)
        self.start()

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Heliotherm/heliotherm.ui", self.widget)
        # self.setCallbacks()
        self.widget.pushButton.clicked.connect(self._openConnectionCallback)
        self.widget.samplerateSpinBox.valueChanged.connect(self._changeSamplerate)
        self.widget.comboBox.setCurrentText(self.host)
        # self._openConnectionCallback()
        return self.widget

    def _openConnectionCallback(self):
        if self.run:
            self.cancel()
            self.widget.pushButton.setText("Verbinden")
            self._base_address = ""
        else:
            address = self.widget.comboBox.currentText()
            self._base_address = address
            self._c = ModbusClient(host=self._base_address, port=self.port, auto_open=True, auto_close=True)
            self._c.timeout(10)
            #self._helio_get()
            self.start()
            self.widget.pushButton.setText("Beenden")

    def _helio_set(self, reg_addr, reg_value):
        for element in self.mappingWrite:
            if element[0] == reg_addr and element[5] == True:
                ans = self._c.write_single_register(reg_addr,reg_value)
                if ans == True:
                    return True
                else:
                    return False
            else:
                raise PermissionError
        raise KeyError

    def Schreiben(self, reg_name, reg_value):
        for element in self.mappingWrite:
            if element[1] == reg_name and element[5] == True:
                ans = self._c.write_single_register(element[0],reg_value)
                if ans == True:
                    return "Wert wurde geändert"
                else:
                    return "Wert konnte nicht geändert werden."
            else:
                return "Element darf nicht beschrieben werden."
        return "Element nicht gefunden"

    def Anschalten(self, modus=1):
        # 0= AUS
        # 1= Automatik
        # 2= Kühlen
        # 3= Sommer
        # 4= Dauerbetrieb
        # 5= Absenkung
        # 6=Urlaub
        # 7= Party
        if int(modus) in self._modes.keys():
            return self.Schreiben(100, modus)
        else:
            return 'Wähle einen Modus zwischen 0 und 7\n'+str(self._modes)

    def Ausschalten(self):
        return self.Schreiben(100, 0)

    def _helio_get_all(self, all=True):
        for idx, value in enumerate(self.mappingWrite):
            if self.mappingWrite[idx][4]==True or all:
                register = self.mappingWrite[idx][0]
                sname = self.mappingWrite[idx][1]
                divisor = self.mappingWrite[idx][2]
                unit = self.mappingWrite[idx][3]

                y = self._helio_get(register, length=1,
                divisor=divisor, holding=True)

                if y is None:
                    print('Could not load {} from register {}'.format(sname, register))
                else:
                    plot = {sname: [y, unit]}
                    self.stream(sdict={self._name:plot})

        for idx, value in enumerate(self.mappingRead):
            if self.mappingRead[idx][4]==True or all:
                register = self.mappingRead[idx][0]
                sname = self.mappingRead[idx][1]
                divisor = self.mappingRead[idx][2]
                unit=self.mappingRead[idx][3]
                y = self._helio_get(register, length=1, divisor=divisor, holding=False)

                if y is None:
                    logging.warning('Could not load {} from register {}'.format(sname, register))
                else:
                    plot = {sname: [y, unit]}
                    self.stream(sdict={self._name:plot})

    def _helio_alle(self, all = False):
        readStart=10
        readEnd=75
        writeStart=100
        writeEnd=159

        resultWrite = self._c.read_holding_registers(writeStart, writeEnd-writeStart+1)
        resultRead = self._c.read_input_registers(readStart, readEnd-readStart+1)

        ans = {}
        if type(resultWrite) == list:
            for idx, value in enumerate(self.mappingWrite):
                if self.mappingWrite[idx][4]==True or all:
                    sname = self.mappingWrite[idx][1]
                    divisor = self.mappingWrite[idx][2]
                    unit = self.mappingWrite[idx][3]
                    y = resultWrite[idx]
                    if y>=2 **16/2:
                        y = 2 **16 - y
                    y = y/divisor
                    ans[sname]=[y, unit]

                    if self.mappingWrite[idx][0] == 100:
                        if not self._firstStart and y != self._lastMode:
                            mode = self._modes[y]
                            self.event('Betriebsart wurde verändert: {}'.format(mode),'Betriebsart',self._name, 0, 'ModusChanged')
                        self._lastMode = y
                    elif self.mappingWrite[idx][0] == 127:
                        if not self._firstStart and y != self._lastExtAnf:
                            if y == 1:
                                self.event('Externe Anforderung angeschaltet','Externe Anforderung',self._name, 0, 'ExtAnfAn')
                            else:
                                self.event('Externe Anforderung ausgeschaltet','Externe Anforderung',self._name, 0, 'ExtAnfAus')
                        self._lastExtAnf = y
        else:
            logging.warning('Could not read writeable-registers, {}'.format(resultWrite))
            if self.widget:
                self.widget.comboBox.setCurrentText('Fehler')

        if type(resultRead) == list:
            for idx, value in enumerate(self.mappingRead):
                if self.mappingRead[idx][4]==True or all:
                    sname = self.mappingRead[idx][1]
                    divisor = self.mappingRead[idx][2]
                    unit = self.mappingRead[idx][3]
                    y = resultRead[idx]
                    if y>=2 **16/2:
                        y = 2 **16 - y
                    y = y/divisor
                    ans[sname]=[y, unit]

                    if self.mappingRead[idx][0] == 26:
                        if not self._firstStart and y != self._lastStoerung:
                            if y == 1:
                                self.event('Störung aufgetreten!','Externe Anforderung',self._name, 2, 'StoerungAn')
                            else:
                                self.event('Störung wurde behoben!','Externe Anforderung',self._name, 2, 'StoerungAus')
                        self._lastStoerung = y

            self._firstStart = False
        else:
            logging.warning('Could not read read-registers, {}'.format(resultRead))
            if self.widget:
                self.widget.comboBox.setCurrentText('Fehler')

        self.stream(sdict={self._name:ans})

    def _helio_get(self, register, length=1, divisor=1, holding=True):
        if holding: #read writeable-variables
            result = self._c.read_holding_registers(register, length)
        else: #read sensor-data
            result = self._c.read_input_registers(register, length)
        if type(result) == list:
            if len(result) == 1:
                result = result[0]
                if result>=2 **16/2:
                    result = 2 **16 - result
                y = result/divisor
                return y
            else:
                logging.warning('You requested more than one value at once, {}'.format(result))
                return None
        else:
            logging.warning('Could not read registers, {}'.format(result))
            return None

    def _changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()

    def loadConfig(self):
        packagedir = self.getDir(__file__)
        with open(packagedir+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")

        self.mappingWrite = config['mappingWrite']
        self.mappingRead = config['mappingRead']
        self.host = config['hostname']
        self.port = config ['port']
        self._name = config['name']
        self.samplerate = config['samplerate']


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
