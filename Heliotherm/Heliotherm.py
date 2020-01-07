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
    """
Zeichnet die Messdaten einer Heliotherm-Wärmepumpe (mit RCG2) auf.
Modbus-TCP muss aktiviert sein und die korrekte IP-Adresse eingetragen sein, damit dieses Gerät funktioniert.
    """
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.loadConfig()
        self.setDeviceName(self._name)
        self.smallGUI = True

        self.activeGroups = self.loadPersistentVariable('activeGroups', [True])
        self.__doc_activeGroups__ = """
Enthält eine Liste mit Funktionen, die die Wärmepumpe besitzt. Gültige Werte sind:
True: Alle Standartmessdaten werden aufgezeichnet
'EVU': Alle EVU-Daten werden aufgezeichnet
'MKR1': Mischkreis 1 Daten werden aufgezeichnet
'MKR2': Mischkreis 2 Daten werden aufgezeichnet
'ext': Externe Daten werden aufgezeichnet
'2teStufe': Zweite Stufe Daten werden aufgezeichnet 
        """
        self._availableGroups = ['EVU', 'MKR1','MKR2', 'ext', '2teStufe']
        # Data-logger thread
        self._firstStart = True
        self._lastStoerung = False
        self._lastExtAnf = True
        self._lastMode = 0

        self._heizkreis1Solltemperatur = 0
        self._heizkreis2Solltemperatur = 0
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
            8: 'Ausheizen',
            9: 'EVU Sperre',
            10: 'Hauptschalter aus'
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
            self.start()
            self.widget.pushButton.setText("Beenden")

    def _helio_set(self, reg_addr, reg_value):
        for element in self._mappingWrite:
            if element[0] == reg_addr and element[5] == True:
                ans = self._c.write_single_register(reg_addr,reg_value)
                if ans == True:
                    return True
                else:
                    return False
            else:
                raise PermissionError
        raise KeyError

    def _Schreiben(self, reg_name, reg_value):
        """
Schreibe ein Register manuell.
        """
        for element in self._mappingWrite:
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
        """
Schalte den Modus der Wärmepumpe um:
0= AUS, 
1= Automatik, 
2= Kühlen, 
3= Sommer, 
4= Dauerbetrieb, 
5= Absenkung, 
6=Urlaub, 
7= Party, 
        """
        # 0= AUS
        # 1= Automatik
        # 2= Kühlen
        # 3= Sommer
        # 4= Dauerbetrieb
        # 5= Absenkung
        # 6=Urlaub
        # 7= Party
        if int(modus) in self._modes.keys() and int(modus)<=7:
            return self._c.write_single_register(100, int(modus))
        else:
            return 'Wähle einen Modus zwischen 0 und 7\n'+str(self._modes)

    def MKR1Schreiben(self, modus=1):
        """
Schalte den Modus des MKR1 um:
0= AUS, 
1= Automatik, 
2= Kühlen, 
3= Sommer, 
4= Dauerbetrieb, 
5= Absenkung, 
6=Urlaub, 
7= Party, 
        """
        # 0= AUS
        # 1= Automatik
        # 2= Kühlen
        # 3= Sommer
        # 4= Dauerbetrieb
        # 5= Absenkung
        # 6=Urlaub
        # 7= Party
        if int(modus) in self._modes.keys() and int(modus)<=7:
            return self._c.write_single_register(107, int(modus))
        else:
            return 'Wähle einen Modus zwischen 0 und 7\n'+str(self._modes)

    def MKR2Schreiben(self, modus=1):
        """
Schalte den Modus des MKR2 um:
0= AUS, 
1= Automatik, 
2= Kühlen, 
3= Sommer, 
4= Dauerbetrieb, 
5= Absenkung, 
6=Urlaub, 
7= Party, 
        """
        # 0= AUS
        # 1= Automatik
        # 2= Kühlen
        # 3= Sommer
        # 4= Dauerbetrieb
        # 5= Absenkung
        # 6=Urlaub
        # 7= Party
        if int(modus) in self._modes.keys() and int(modus)<=7:
            return self._c.write_single_register(112, int(modus))
        else:
            return 'Wähle einen Modus zwischen 0 und 7\n'+str(self._modes)

    def MKR1Automatik(self):
        """
Schalte MKR1 auf Automatik
        """
        return self.MKR1Schreiben(modus=1)

    def MKR2Automatik(self):
        """
Schalte MKR2 auf Automatik
        """
        return self.MKR2Schreiben(modus=1)

    def MKR1Aus(self):
        """
Schalte MKR1 aus
        """
        return self.MKR1Schreiben(modus=0)

    def MKR2Aus(self):
        """
Schalte MKR2 aus
        """
        return self.MKR1Schreiben(modus=0)

    def MKR1Kuehlen(self):
        """
Schalte MKR1 auf Kühlen
        """
        return self.MKR1Schreiben(modus=2)

    def MKR2Kuehlen(self):
        """
Schalte MKR2 auf Kühlen
        """
        return self.MKR1Schreiben(modus=2)

    def MKR1Absenkung(self):
        """
Schalte MKR1 auf Absenkung
        """
        return self.MKR1Schreiben(modus=5)

    def MKR2Absenkung(self):
        """
Schalte MKR2 auf Absenkung
        """
        return self.MKR1Schreiben(modus=5)

    def Ausschalten(self):
        """
Schalte die Wärmepumpe aus
        """
        return self._c.write_single_register(100, 0)


    @property
    def Heizkreis1Solltemperatur(self):
        return self._heizkreis1Solltemperatur

    @Heizkreis1Solltemperatur.setter
    def Heizkreis1Solltemperatur(self, value):
        reg_addr = 108
        try:
            value = float(value)
        except:
            pass
        if value > 0:
            self._helio_set(reg_addr,value)

        self._heizkreis1Solltemperatur = value

    @property
    def Heizkreis2Solltemperatur(self):
        return self._heizkreis2Solltemperatur

    @Heizkreis2Solltemperatur.setter
    def Heizkreis2Solltemperatur(self, value):
        reg_addr = 113
        try:
            value = float(value)
        except:
            pass
        if value > 0:
            self._helio_set(reg_addr,value)

        self._heizkreis2Solltemperatur = value

    def _helio_alle(self, all = False):
        readStart=10
        readEnd=75
        resultRead = self._c.read_input_registers(readStart, readEnd-readStart+1)

        writeStart=100
        writeEnd=159
        resultWrite = self._c.read_holding_registers(writeStart, writeEnd-writeStart+1)
        if type(resultWrite) != list:
            writeStart=100
            writeEnd=134
            resultWrite = self._c.read_holding_registers(writeStart, writeEnd-writeStart+1)

        ans = {}
        if type(resultWrite) == list:
            for idx, value in enumerate(self._mappingWrite):
                if idx >= len(resultWrite):
                    break
                if len(self._mappingWrite[idx]) == 6:
                    if self._mappingWrite[idx][4] in self.activeGroups or all:
                        sname = self._mappingWrite[idx][1]
                        divisor = self._mappingWrite[idx][2]
                        unit = self._mappingWrite[idx][3]
                        y = resultWrite[idx]
                        if y>=2 **16/2:
                            y = 2 **16 - y
                        y = y/divisor
                        ans[sname]=[y, unit]

                        if self._mappingWrite[idx][0] == 100:
                            if not self._firstStart and y != self._lastMode:
                                mode = self._modes[y]
                                self.event('Betriebsart wurde verändert: {}'.format(mode),'Betriebsart',self._name, 0, 'ModusChanged')
                            self._lastMode = y
                        elif self._mappingWrite[idx][0] == 108:
                            self._heizkreis1Solltemperatur = y
                        elif self._mappingWrite[idx][0] == 113:
                            self._heizkreis2Solltemperatur = y
                        elif self._mappingWrite[idx][0] == 127:
                            if not self._firstStart and y != self._lastExtAnf:
                                if y == 1:
                                    self.event('Externe Anforderung angeschaltet','Externe Anforderung',self._name, 0, 'ExtAnfAn')
                                else:
                                    self.event('Externe Anforderung ausgeschaltet','Externe Anforderung',self._name, 0, 'ExtAnfAus')
                            self._lastExtAnf = y
                else:
                    pass
                # handle parameters
        else:
            logging.warning('Could not read writeable-registers, {}'.format(resultWrite))
            if self.widget:
                self.widget.comboBox.setCurrentText('Fehler')

        if type(resultRead) == list:
            for idx, value in enumerate(self._mappingRead):
                if self._mappingRead[idx][4] in self.activeGroups or all:
                    if len(self._mappingRead[idx] == 5):
                        sname = self._mappingRead[idx][1]
                        divisor = self._mappingRead[idx][2]
                        unit = self._mappingRead[idx][3]
                        y = resultRead[idx]
                        if y>=2 **16/2:
                            y = 2 **16 - y
                        y = y/divisor
                        ans[sname]=[y, unit]

                        if self._mappingRead[idx][0] == 26:
                            if not self._firstStart and y != self._lastStoerung:
                                if y != 0:
                                    self.event('Störung aufgetreten: {}!'.format(y),'Stoerung',self._name, 2, 'StoerungAn')
                                else:
                                    self.event('Störung wurde behoben!','Stoerung',self._name, 0, 'StoerungAus')
                            self._lastStoerung = y
                    else:
                        pass
                        # handle parameters

            self._firstStart = False
        else:
            logging.warning('Could not read read-registers, {}'.format(resultRead))
            if self.widget:
                self.widget.comboBox.setCurrentText('Fehler')

        self.stream(sdict={self._name:ans})

    def _changeSamplerate(self):
        self.samplerate = self.widget.samplerateSpinBox.value()

    def loadConfig(self):
        packagedir = self.getDir(__file__)
        with open(packagedir+"/config.json", encoding="UTF-8") as jsonfile:
            config = json.load(jsonfile, encoding="UTF-8")

        self._mappingWrite = config['mappingWrite']
        self._mappingRead = config['mappingRead']
        self.host = config['hostname']
        self.port = config ['port']
        self._name = config['name']
        self.samplerate = config['samplerate']


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
