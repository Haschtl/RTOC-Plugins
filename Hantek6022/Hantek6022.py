# Hantek API from https://github.com/rpcope1/Hantek6022API/blob/master/PyHT6022/LibUsbScope.py

try:
    from LoggerPlugin import LoggerPlugin
except ImportError:
    from RTOC.LoggerPlugin import LoggerPlugin
import time
from threading import Thread
from PyQt5 import uic
from PyQt5 import QtWidgets

from collections import deque

from PyHT6022.LibUsbScope import Oscilloscope
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

DEVICENAME = 'Hantek6022'
SAMPLERATE = 10


class Plugin(LoggerPlugin):
    def __init__(self, stream=None, plot=None, event=None):
        # Plugin setup
        super(Plugin, self).__init__(stream, plot, event)
        self.setDeviceName(DEVICENAME)
        self.smallGUI = False

        self._scope = None

        self.setPerpetualTimer(self._updateT, samplerate=SAMPLERATE)
        self._blocksize = 6*1024      # should be divisible by 6*1024
        self._alternative = 1         # choose ISO 3072 bytes per 125 us

        self._recordLength = 5000
        self._blocksize = self._recordLength
        self._yData1 = deque(maxlen=self._recordLength)
        self._yData2 = deque(maxlen=self._recordLength)

        self._yData1Triggered = deque(maxlen=self._recordLength)
        self._yData2Triggered = deque(maxlen=self._recordLength)
        self._singleTriggerFound = False

        self.__capturer = Thread(target=self.__captureT)
        self.__capturer.start()

    # THIS IS YOUR THREAD
    def _updateT(self):

        if not self.widget.pauseButton.isChecked():
            if self.widget.enableTriggerButton.isChecked():
                yData1, yData2, stop = self.__trigger(list(self._yData1), list(self._yData2))
            else:
                yData1 = self._yData1
                yData2 = self._yData2
                stop = False
            samplerate = self._str2Samplerate(self.widget.samplerateComboBox.currentText())
            xData = [(i-len(yData1))/samplerate for i in range(len(yData1))]
            if len(self._yData1) > 1:
                self.plot(xData, yData1, dname='Hantek', sname='CH1', unit='V')
            if self.widget.channel2CheckBox.isChecked():
                self.plot(xData, yData2, dname='Hantek', sname='CH2', unit='V')
            if stop:
                self.widget.pauseButton.setChecked(True)

    def __captureT(self):
        #self.last_time = time.time()
        shutdown_event = self._scope.read_async(
            self._extend_callback, self._blocksize, outstanding_transfers=10, raw=True)
        self._scope.start_capture()
        while self.run:
            self._scope.poll()
        # logging.info("Stopping new transfers.")
        # scope.stop_capture()
        self._scope.stop_capture()
        shutdown_event.set()
        time.sleep(0.1)
        self._scope.close_handle()

    def loadGUI(self):
        self.widget = QtWidgets.QWidget()
        packagedir = self.getDir(__file__)
        uic.loadUi(packagedir+"/Hantek6022/hantek.ui", self.widget)
        # self.setCallbacks()
        self.widget.reconnectButton.clicked.connect(self.__openConnectionCallback)
        self.widget.samplerateComboBox.currentTextChanged.connect(self._updateScopeSettings)
        self.widget.recordLengthSpinBox.valueChanged.connect(self.changeLength)
        # self.widget.channel1CheckBox.valueChanged.connect(self.enableChannel1)
        self.widget.channel1CheckBox.setEnabled(False)
        self.widget.channel1ACDCComboBox.hide()  # valueChanged.connect(self.)
        self.widget.channel1VoltPDivComboBox.currentTextChanged.connect(self._updateScopeSettings)
        self.widget.channel2VoltPDivComboBox.currentTextChanged.connect(self._updateScopeSettings)
        self.widget.channel2CheckBox.stateChanged.connect(self._updateScopeSettings)
        self.widget.channel2ACDCComboBox.hide()  # valueChanged.connect(self.)
        # self.widget.pauseButton.clicked.connect(self.)

        # self.widget.triggerChannelComboBox.textChanged.connect(self.)
        # self.widget.triggerLevelSpinBox.valueChanged.connect(self.)
        # self.widget.enableTriggerButton.clicked.connect(self.)
        self._recordLength = self.widget.recordLengthSpinBox.value()
        self.xData = deque(maxlen=self._recordLength)
        self._yData1 = deque(maxlen=self._recordLength)
        self._yData2 = deque(maxlen=self._recordLength)
        self.__openConnectionCallback()
        return self.widget

    def __openConnectionCallback(self):
        self.widget.reconnectButton.setEnabled(False)
        if self.run:
            self.cancel()
            self.widget.reconnectButton.setText("Reconnect")
            self.__base_address = ""
            self.widget.reconnectButton.setEnabled(True)
        else:
            self._updateScopeSettings()
            self.widget.reconnectButton.setText("Stop")
            self.widget.reconnectButton.setEnabled(True)

    def __trigger(self, data1, data2):
        if not self._singleTriggerFound:
            if self.widget.channel2CheckBox.isChecked() and self.widget.triggerChannelComboBox.currentText() == 'CH2':
                triggerSignal = list(data2)
            else:
                triggerSignal = list(data1)

            flanke = self.widget.comboBox.currentText()
            triggerLevel = self.widget.triggerLevelSpinBox.value()
            cutoff = 0
            mean = self.widget.smoothSpinBox.value()
            triggerPrepared = False

            if flanke == 'Rising':
                if max(triggerSignal) > triggerLevel:
                    for idx in range(len(triggerSignal)):
                        if triggerSignal[idx] >= triggerLevel-mean and triggerSignal[idx] <= triggerLevel:
                            triggerPrepared = True
                        elif triggerSignal[idx] < triggerLevel-mean and triggerPrepared:
                            triggerPrepared = False
                        elif triggerSignal[idx] > triggerLevel and triggerPrepared == True:
                            cutoff = idx
                            break
            else:
                if min(triggerSignal) < triggerLevel:
                    for idx in range(len(triggerSignal)):
                        if triggerSignal[idx] <= triggerLevel+mean and triggerSignal[idx] >= triggerLevel:
                            triggerPrepared = True
                        elif triggerSignal[idx] > triggerLevel+mean and triggerPrepared:
                            triggerPrepared = False
                        elif triggerSignal[idx] < triggerLevel and triggerPrepared == True:
                            cutoff = idx
                            break
            stop = False

            if len(data2) > cutoff:
                data2 = list(data2)[cutoff:]
            if len(data1) > cutoff:
                data1 = list(data1)[cutoff:]

            if cutoff != 0 and self.widget.checkBox.isChecked() and not self._singleTriggerFound:
                self._singleTriggerFound = True
            else:
                self._singleTriggerFound = False
            if self.widget.checkBox.isChecked():
                self._yData1Triggered = deque(list(data1), maxlen=self._recordLength)
                self._yData2Triggered = deque(list(data2), maxlen=self._recordLength)
        else:
            if len(self._yData1Triggered) < self._recordLength:
                stop = False
            else:
                self._singleTriggerFound = False
                stop = True
                data1 = self._yData1Triggered
                data2 = self._yData2Triggered

        return data1, data2, stop

    def _updateScopeSettings(self):
        if self._scope:
            self.cancel()

        self._scope = Oscilloscope()
        self._scope.setup()
        self._scope.open_handle()
        if (not self._scope.is_device_firmware_present):
            self._scope.flash_firmware()
        else:
            self._scope.supports_single_channel = True

        logging.info("Setting up scope!")
        self._scope.set_interface(self._alternative)
        logging.info("ISO" if self._scope.is_iso else "BULK",
                     "packet size:", self._scope.packetsize)
        if self.widget.channel2CheckBox.isChecked():
            self._scope.set_num_channels(2)
        else:
            self._scope.set_num_channels(1)
        # set voltage range
        voltagerange1 = self._strVoltageToID(self.widget.channel1VoltPDivComboBox.currentText())
        voltagerange2 = self._strVoltageToID(self.widget.channel2VoltPDivComboBox.currentText())
        self._scope.set_ch1_voltage_range(voltagerange1)
        self._scope.set_ch2_voltage_range(voltagerange2)

        self._scope.set_sample_rate(self._str2SamplerateID(
            self.widget.samplerateComboBox.currentText()))

        self._blocksize = self._recordLength

        self.start()
        # self.widget.reconnectButton.setText("Stop")
        # self.widget.reconnectButton.setEnabled(True)

    def calibrate(self):
        if self._scope:
            self._scope.setup_dso_cal_level()
            cal_level = self._scope.get_calibration_data()
            self._scope.set_dso_calibration(cal_level)

    def _str2SamplerateID(self, strung):
        if 'MHz' in strung:
            strung = strung.replace(' MHz', '')
            return int(strung)
        else:
            strung = strung.replace(' kHz', '')
            return int(int(strung)/10)

    def _str2Samplerate(self, strung):
        if 'MHz' in strung:
            strung = strung.replace(' MHz', '')
            return int(strung)*1000000
        else:
            strung = strung.replace(' kHz', '')
            return int(strung)*1000

    # def __changeChannel1VoltPDiv(self, strung):
    #     if self._scope:
    #         voltagerange = self._strVoltageToID(strung)
    #         self._scope.set_ch1_voltage_range(voltagerange)
    #
    # def __changeChannel2VoltPDiv(self, strung):
    #     if self._scope:
    #         voltagerange = self._strVoltageToID(strung)
    #         self._scope.set_ch2_voltage_range(voltagerange)

    def _enableChannel2(self, value):
        if value:
            self._scope.set_num_channels(2)
        else:
            self._scope.set_num_channels(1)

    def _strVoltageToID(self, strung):
        voltagerange = 1
        if strung == '2.6 V':
            voltagerange = 2
        elif strung == '5 V':
            voltagerange = 5
        elif strung == '10 V':
            voltagerange = 10
        return voltagerange

    def _extend_callback(self, ch1_data, ch2_data):
        voltage_data = self._scope.scale_read_data(ch1_data, self._strVoltageToID(
            self.widget.channel1VoltPDivComboBox.currentText()))
        if len(voltage_data) > 1:
            self._yData1.extend(voltage_data)
            if len(self._yData1Triggered) < self._recordLength:
                if len(self._yData1Triggered)+len(voltage_data) < self._recordLength:
                    self._yData1Triggered.extend(voltage_data)
                else:
                    self._yData1Triggered.extend(
                        voltage_data[0:self._recordLength-len(self._yData1Triggered)])

        if ch2_data != '':
            voltage_data = self._scope.scale_read_data(ch2_data, self._strVoltageToID(
                self.widget.channel1VoltPDivComboBox.currentText()))
            self._yData2.extend(voltage_data)
            if len(self._yData2Triggered) < self._recordLength:
                if len(self._yData2Triggered)+len(voltage_data) < self._recordLength:
                    self._yData2Triggered.extend(voltage_data)
                else:
                    self._yData2Triggered.extend(
                        voltage_data[0:self._recordLength-len(self._yData2Triggered)])

    def changeLength(self, newlen=10000):
        self._recordLength = newlen
        self._yData1 = deque(maxlen=self._recordLength)
        self._yData2 = deque(maxlen=self._recordLength)
        self._yData1Triggered = deque(maxlen=self._recordLength)
        self._yData2Triggered = deque(maxlen=self._recordLength)
        self._updateScopeSettings()


if __name__ == "__main__":
    standalone = Plugin()
    standalone.setup()
