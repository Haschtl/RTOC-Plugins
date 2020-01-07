try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
import json
import logging as log
from pyModbusTCP.client import ModbusClient
from functools import partial

log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

class Plugin(LoggerPlugin):
    """
Zeichnet die Messdaten einer Heliotherm-Wärmepumpe (mit Remote Control Gateway X SERIES EL-005-0001 ab v1.0.3.2 - 10.12.2018) auf.
Modbus-TCP muss im Webinterface der Wärmepumpe aktiviert sein und im Anschluss die IP-Adresse der Wärmepumpe im Parameter "IP_Adresse" eingetragen werden.
    """
    def __init__(self, *args, **kwargs):
        # Plugin setup
        super(Plugin, self).__init__(*args, **kwargs)
        self.setDeviceName('Heliotherm')
        
        self._connected = False
        self.__doc_connected__ = "Zeigt an, ob eine Wärmepumpe verbunden ist"
        self.status = ""
        self.__doc_status__ = "Zeigt Verbindungs-Informationen an, falls vorhanden"
        self._firstStart = True
        self._lastStoerung = False
        self._lastExtAnf = True
        self._lastMode = 0
        self._c = None

        # Initialize persistant attributes
        self.IP_Adresse = self.initPersistentVariable('IP_Adresse', '')
        self.__doc_IP_Adresse__ = "IP-Adresse des RCG2 der Heliotherm-Wärmepumpe"
        self.samplerate = self.initPersistentVariable('samplerate', 1)
        self.__doc_samplerate__ = "Aufzeichnungsrate in Herz"
        self.Port = self.initPersistentVariable('Port', 502)
        self.__doc_Port__ = "ModbusTCP-Port (Standart: 502)"
        self._groups = self.initPersistentVariable('_groups', {'Global': True})
        # Load mapping.json file
        self._groupInfo = {}
        self._mappingWrite = []
        self._mappingRead = []
        self._loadMapping()

        # Update self._groups
        for group in self._groupInfo.keys():
            if group not in self._groups.keys():
                self._groups[group] = False

        self._createGroupAttributes(self._groups)

        # Create attributes for
        self._createAttributes(self._mappingWrite)
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

    def _loadMapping(self):
        packagedir = self.getDir(__file__)
        with open(packagedir+"/mapping.json", encoding="UTF-8") as jsonfile:
            mapping = json.load(jsonfile, encoding="UTF-8")

        self._groupInfo = mapping['groups']
        self._mappingWrite = mapping['mappingWrite']
        self._mappingRead = mapping['mappingRead']


    def _createAttributes(self, mappingWrite):
        groups = self._activeGroups()
        for parameter in mappingWrite:
            if parameter['group'] in groups:
                # Replace invalid chars for attribute names
                name = self._formatAttributeName(parameter['sname'])
                # Create 'private' parameter with _ in front: self._name
                setattr(self.__class__, '_'+name, None)

                # This intermediate function handles the strange double self arguments
                def setter(self, name, parameter, selfself, value):
                    self._setAttribute(name, value, parameter)

                # Make sure, that the parameters are "the values, which would be represented at this point with print(...)"
                setpart = partial(setter, self, name, parameter)
                getpart = partial(getattr, self, '_'+name)

                # Create an attribute with the actual name. The getter refers to it's self._name attribute. The setter function to self._setGroupAttribute(name, value, parameter)
                setattr(self.__class__, name, property(getpart, setpart))

                # If parameter contains docs, create a third attribute at self.__doc_PARNAME__
                if "doc" in parameter.keys():
                    setattr(self, '__doc_'+name+'__', parameter['doc'])

    def _activeGroups(self):
        groups = []
        for group in self._groups.keys():
            if self._groups[group] is True:
                groups.append(group)

        return groups

    def _createGroupAttributes(self, groups):
        for groupname in groups.keys():
                # Replace invalid chars for attribute names
                name = 'Gruppe_'+self._formatAttributeName(groupname)
                # Create 'private' parameter with _ in front: self._name
                setattr(self.__class__, '_'+name, groups[groupname])

                # This intermediate function handles the strange double self arguments
                def setter(self, name, parameter, selfself, value):
                    self._setGroupAttribute(name, value, parameter)

                # Make sure, that the parameters are "the values, which would be represented at this point with print(...)"
                setpart = partial(setter, self, name, groupname)
                getpart = partial(getattr, self, '_'+name)

                # Create an attribute with the actual name. The getter refers to it's self._name attribute. The setter function to self._setAttribute(name, value, parameter)
                setattr(self.__class__, name, property(getpart, setpart))

                setattr(self, '__doc_'+name+'__', self._groupInfo[groupname])

    def _setAttribute(self, name, value, parameter):
        if self._c is None:
            return

        if parameter['write'] is False:
            self.warning('This parameter cannot be changed')
            self.status = 'This parameter cannot be changed'
        else:
            ok = self._writeModbusRegister(parameter, value)
            if ok:
                self.info('Wrote register in WP')
                self.status = 'Wrote register in WP'
            else:
                self.error('Failed to write register in WP')
                self.status = 'Failed to write register in WP'

    def _setAttributeRef(self, name, value, parameter):
        name = self._formatAttributeName(name)
        setattr(self, '_'+name, value)

    def _formatAttributeName(self, name):
        return name.replace(' ','_').replace('/','_').replace('.','_').replace('-','_')

    def _setGroupAttribute(self, name, value, groupname):
        name = self._formatAttributeName(name)
        setattr(self, '_'+name, value)
        self._groups[groupname] = value
        self.savePersistentVariable('_groups', self._groups)

    def connect(self, ip=None):
        """
Verbinde dich mit einer Heliotherm Wärmepumpe (mit RCG2). Gib dazu die IP-Adresse/den Hostnamen an. Wenn die IP-Adresse schonmal konfiguriert wurde, lasse das Feld einfach leer.
        """
        if ip != None and ip != '' and type(ip) is str:
            self.IP_Adresse = ip
            self.savePersistentVariable('IP_Adresse', self.IP_Adresse)
        self.info('Connecting with {}'.format(self.IP_Adresse))
        if not self._connected:
            try:
                self.setPerpetualTimer(self._readModbusRegisters, samplerate=self.samplerate)
                self._c = ModbusClient(host=self.IP_Adresse, port=self.Port, auto_open=True, auto_close=True)
                if self._c is None:
                    self.error('Could not connect with {}'.format(self.IP_Adresse))
                    self.status = 'Could not connect with {}'.format(self.IP_Adresse)
                    return False
                self._c.timeout(10)
                self.status = 'Trying to connect...'
                self.start()
                self._connected = True
                return True
            except Exception as e:
                self.error('Could not connect with {}:\n{}'.format(self.IP_Adresse, e))
                self.status = 'Could not connect with {}:\n{}'.format(self.IP_Adresse, e)
                return False
        else:
            self.status = 'Already connected. Disconnect first'
            return False
    
    def disconnect(self):
        """
Trenne die Verbindung zu der Heliotherm Wärmepumpe
        """
        if self._connected:
            self.cancel()
            self._connected = False
            self._c = None
            self.status = 'Successfully disconnected'
            return True
        else:
            self.status = 'Cannot disconnect. Not connected.'
            return False
    
    def _mappingMinMaxRegister(self, mapping):
        min = 9999999999999
        max = 0
        for parameter in mapping:
            if parameter['register']> max:
                max = parameter['register']
            if parameter['register']< min:
                min = parameter['register']
        return min, max

    def _readModbusRegisters(self):
        if self._c == None:
            return
        active_groups = self._activeGroups()

        writeStart=100
        writeEnd=159
        resultWrite = self._c.read_holding_registers(writeStart, writeEnd-writeStart+1)
        if type(resultWrite) != list:
            writeStart=100
            writeEnd=134
            resultWrite = self._c.read_holding_registers(writeStart, writeEnd-writeStart+1)

        ans = {}
        if type(resultWrite) == list:
            for parameter in self._mappingWrite:
                if parameter['group'] in active_groups:
                    regIdx= parameter['register']-writeStart
                    if regIdx >= len(resultWrite):
                        continue

                    writeableValue = resultWrite[regIdx]
                    if writeableValue>=2 **16/2:
                        writeableValue = 2 **16 - writeableValue
                    writeableValue = writeableValue/parameter['scale']

                    if parameter['record']:
                        ans[parameter['sname']]=[writeableValue, parameter['unit']]

                    # if parameter['write'] is True:
                    self._setAttributeRef(self._formatAttributeName(parameter['sname']), writeableValue, parameter)

                    if parameter['sname'] == "Betriebsart":
                        if not self._firstStart and writeableValue != self._lastMode:
                            mode = self._modes[writeableValue]
                            self.event('Betriebsart wurde verändert: {}'.format(mode),parameter['sname'],self._devicename, 0, 'ModusChanged')
                        self._lastMode = writeableValue
                    elif parameter['sname'] == "Externe Anforderung":
                        if not self._firstStart and writeableValue != self._lastExtAnf:
                            if writeableValue == 1:
                                self.event('Externe Anforderung angeschaltet',parameter['sname'],self._devicename, 0, 'ExtAnfAn')
                            else:
                                self.event('Externe Anforderung ausgeschaltet',parameter['sname'],self._devicename, 0, 'ExtAnfAus')
                        self._lastExtAnf = writeableValue
        else:
            self.warning('Could not read writeable-registers, {}'.format(resultWrite))
            self.status = 'Could not read writeable-registers, {}'.format(resultWrite)

        readStart=10
        readEnd=75
        resultRead = self._c.read_input_registers(readStart, readEnd-readStart+1)
        
        if type(resultRead) == list:
            for parameter in self._mappingRead:
                if parameter['group'] in active_groups:
                    regIdx= parameter['register']-readStart
                    if regIdx >= len(resultRead):
                        continue

                    writeableValue = resultRead[regIdx]
                    if writeableValue>=2 **16/2:
                        writeableValue = 2 **16 - writeableValue
                    writeableValue = writeableValue/parameter['scale']

                    if parameter['record']:
                        ans[parameter['sname']]=[writeableValue, parameter['unit']]

                    if parameter['sname'] == 'Stoerung':
                        if not self._firstStart and writeableValue != self._lastStoerung:
                            if writeableValue != 0:
                                self.event('Störung aufgetreten: {}!'.format(writeableValue),parameter['sname'],self._devicename, 2, 'StoerungAn')
                            else:
                                self.event('Störung wurde behoben!',parameter['sname'],self._devicename, 0, 'StoerungAus')
                        self._lastStoerung = writeableValue

            self._firstStart = False
            self.status = 'Connected'
        else:
            self.warning('Could not read read-registers, {}'.format(resultRead))
            self.status = 'Could not read read-registers, {}'.format(resultRead)

        self.stream(sdict={self._devicename:ans})

    def _writeModbusRegister(self, parameter, reg_value):
        # if str(reg_addr) in self._mappingWrite.keys():
        ans = self._c.write_single_register(parameter['register'],reg_value*parameter['scale'])
        if ans == True:
            return True
        else:
            return False


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
