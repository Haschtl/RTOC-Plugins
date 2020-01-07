from RTOC.LoggerPlugin import LoggerPlugin

from PyQt5 import uic
from PyQt5 import QtWidgets


devicename = "OctoControl"
apikey = ""
SAMPLERATE = 1


class Plugin(LoggerPlugin):
    """ 
Remotesteuerung für 3D-Drucker mit Octoprint-Server
"""
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName(devicename)
        self.api = None

    def send_gcode(self, gcode:str):
        """
Sendet einen GCODE-Befehl an den Drucker
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.send_gcode(gcode)

    def fakeACK(self):
        """
Führt eine Fake-Acknowledge in Octoprint durch
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.fakeACK()

    def connectPrinter(self):
"""
Verbindet Octoprint mit einem Drucker (automatische Suche)
"""
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.connectPrinter()

    def disconnectPrinter(self):
        """
Trennt die Verbindung von Octoprint zum Drucker
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.disconnectPrinter()

    def getStatus(self):
        """
Gibt den aktuellen Druckerstatus zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getStatus()

    def getJob(self):
        """
Gibt Informationen zum aktuellen Druckjob zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getJob()

    def getPrintFiles(self):
        """
Gibt eine Liste mit allen verfügbaren Dateien zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getPrintFiles()

    def getVersion(self):
        """
Gibt die Octoprint-Version zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getVersion()

    def getConnection(self):
        """
Gibt die aktuellen Verbindungseinstellungen zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getConnection()

    def setHotendFan(self, value:float):
        """
Stellt die Bauteil-Lüfterdrehzahl (0-125) ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setFan(value, 0)

    def setChamberFan(self, value:float):
        """
Stellt die Druckraum-Lüfterdrehzahl (0-125) ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setFan(value, 1)

    def setLight(self, value:float):
        """
Stellt die Beleuchtungshelligkeit (0-125) ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setLight(value)

    def setHotend0Temp(self, value:float):
        """
Stellt die Solltemperatur am Hotend0 ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setNozzleTemp(value,0)

    def setHotend1Temp(self, value:float):
        """
Stellt die Solltemperatur am Hotend1 ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setNozzleTemp(value,1)

    def setBedTemp(self, value:float):
        """
Stellt die Solltemperatur des Druckbettes ein.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setBedTemp(value)

    def home(self):
        """
Führt ein Homing durch
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.home()

    def setPower(self, value:bool):
        """
Schaltet das Netzteil des Druckers an/aus
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.setPower(value)

    def enginesOff(self):
        """
Schaltet die Motoren des Drucker aus.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.enginesOff()

    def resetEEPROM(self):
        """
Setzt die aktuelle Konfiguration des Druckers zurück.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.resetEEPROM()

    def loadEEPROM(self):
        """
Ersetzt die aktuelle Konfiguration des Druckers mit der im EEPROM.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.loadEEPROM()

    def saveEEPROM(self):
        """
Speichert die aktuelle Konfiguration im EEPROM.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.saveEEPROM()

    def restart(self):
        """
Startet den Drucker neu.
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        self.api.restart()

    def getSelectedSpools(self):
        """
Gibt die aktuell ausgewählte Filament-Spule zurück
        """
        if self.api == None:
            print('No Printer-API (LaserWeb or Octoprint) connected.')
            return
        return self.api.getSelectedSpools()




if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
