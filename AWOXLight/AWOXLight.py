try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
import json
import logging as log
from pyModbusTCP.client import ModbusClient
from functools import partial
import awoxmeshlight
import webcolors

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

class Plugin(LoggerPlugin):
    """
Steuert eine AWOX Lampe via Bluetooth
    """
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName('AWOXLight')
        
        self.status = ""
        self._connected = False
        self.__doc_connected__ = "Zeigt an, ob eine Lampe verbunden ist"
        self.__doc_status__ = "Zeigt Verbindungs-Informationen an, falls vorhanden"
        self._mylight = None
        # Initialize persistant attributes
        self.MAC_Adresse = self.initPersistentVariable('MAC_Adresse', '')
        self.__doc_IP_Adresse__ = "MAC-Adresse der AWOX Lampe"
        
        self.Password = self.initPersistentVariable('Password', '')
        self.__doc_Password__ = "Passwort der AWOX Lampe"
        
        self.Name = self.initPersistentVariable('Name', '')
        self.__doc_Name__ = "Name der AWOX Lampe"

        if self.MAC_Adresse != '':
            self.connect()
        

    @property
    def connected(self):
        return self._connected

    @connected.setter
    def connected(self, value):
        if value is True:
            self.connect()
        elif value is False:
            self.disconnect()
        # self._connected = value

    def connect(self, mac=None):
        """
Stellt die Verbindung zu einer AWOX Lampe her
        """
        if mac != None and mac != '' and type(mac) is str:
            self.MAC_Adresse = mac
            self.savePersistentVariable('MAC_Adresse', self.MAC_Adresse)
        logging.info('Connecting with {}'.format(self.MAC_Adresse))
        if not self._connected:
            try:
                self._mylight = awoxmeshlight.AwoxMeshLight(self.MAC_Adresse, self.Name, self.Password)
                self._mylight.connect()
                self._connected = True
                return True
            except Exception as e:
                logging.error('Could not connect with {}:\n{}'.format(self.MAC_Adresse, e))
                self.status = 'Could not connect with {}:\n{}'.format(self.MAC_Adresse, e)
                return False
        else:
            self.status = 'Already connected. Disconnect first'
            return False
    
    def disconnect(self):
        """
Trenne die Verbindung zu der AWOX Lampe
        """
        if self._connected:
            self._mylight.disconnect()
            self._connected = False
            self._mylight = None
            self.status = 'Successfully disconnected'
            return True
        else:
            self.status = 'Cannot disconnect. Not connected.'
            return False

    def setPreset(self, id:int=0):
        """
Lädt ein Preset
        """
        if self._mylight !== None:
            self._mylight.setPreset(id) #colorchange

    def setSequenceFadeDuration(self, seconds=1):
        """
Set Sequence Fade duration
        """
        if self._mylight !== None:
            self._mylight.setSequenceFadeDuration(seconds*1000)

    def setSequenceColorDuration(self, seconds=1):
        """
Set Sequence Color duration
        """
        if self._mylight !== None:
            self._mylight.setSequenceColorDuration(seconds*1000)

    def setAlphaColor(self, red=0, green=255, blue=0, alpha=255):
        """
{"type": "RGBA_Color", "red": {"min": 0, "max":255}, "green": {"min": 0, "max":255}, "blue": {"min": 0, "max":255}, "alpha": {"min": 0, "max":255}}
Set Color, each from 0-255
        """
        if self._mylight !== None:
            self._mylight.setColor(red, green, blue) #green


    def setColor(self, red=0, green=255, blue=0):
        """
{"type": "RGB_Color", "red": {"min": 0, "max":255}, "green": {"min": 0, "max":255}, "blue": {"min": 0, "max":255}}
Set Color, each from 0-255
        """
        if self._mylight !== None:
            self._mylight.setColor(red, green, blue) #green

    def setColorBrightness(self, brightness=255):
        """
{"brightness": {"min": 0, "max":255}}
Set Color brightness: a value between 0 and 255
        """
        if self._mylight !== None:
            self._mylight.setColorBrightness(brightness) #dark

    def setWhite(self, temp=20, brightness=20):
        """
{"temp": {"min": 0, "max":255}, "brightness": {"min": 0, "max":255}}
Set white color: a value between 0 and 255
        """
        if self._mylight !== None:
            self._mylight.setWhite(temp, brightness) #warmwhite

    def readStatus(self):
        """
Read the light status
        """
        if self._mylight !== None:
            self._mylight.readStatus() #warmwhite

    def off(self):
        """
Switch the light off
        """
        if self._mylight !== None:
            self._mylight.off() #warmwhite

    def on(self):
        """
Switch the light on
        """
        if self._mylight !== None:
            self._mylight.on() #warmwhite
        

if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
